import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery

from bot import bot, db
from config import ADMIN_IDS, PAYMENTS_PROVIDER_TOKEN, BOT_USERNAME, CRYPTO_BOT_TOKEN, YOOMONEY_RECEIVER, YOOMONEY_SECRET
from keyboards import *
from utils import get_flag
import json
import requests
import time
import uuid
import threading
import logging
import re

# ---- AUTO-POLLING FOR CRYPTO BOT ----
_crypto_pending = {}  # invoice_id -> {...}
_crypto_pending_lock = threading.Lock()

def register_pending_invoice(invoice_id, user_id, code, qty, chat_id, message_id, cat, total):
    with _crypto_pending_lock:
        _crypto_pending[str(invoice_id)] = {
            'user_id': user_id,
            'code': code,
            'qty': qty,
            'chat_id': chat_id,
            'message_id': message_id,
            'cat': cat,
            'total': total,
            'tries': 0
        }

def deliver_crypto_payment(pending):
    """auto-deliver after successful crypto payment"""
    code = pending['code']
    qty = pending['qty']
    cat = pending['cat']
    user_id = pending['user_id']
    total = pending['total']
    chat_id = pending['chat_id']
    message_id = pending['message_id']

    order_id = db.create_order(user_id, code, qty, total, 'cryptobot')

    if cat[6] == 'manual':
        db.create_manual_order(order_id, user_id, code)
        db.update_order_status(order_id, 'pending_number')
        try:
            bot.edit_message_text(
                f'✅ Оплата получена!\n\nЗаказ #{order_id}\nОжидайте, администратор скоро предоставит данные',
                chat_id, message_id
            )
        except:
            pass
        for aid in ADMIN_IDS:
            try:
                bot.send_message(
                    aid,
                    f'⚠️ Новый заказ #{order_id}!\nТовар: {cat[3]} {cat[2]} (Ручная выдача / CryptoBot auto)',
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton('📥 Скинуть номер', callback_data=f'manual_phone_')
                    )
                )
            except:
                pass
    else:
        products = []
        for _ in range(qty):
            prod = db.get_product_for_sale(code)
            if prod:
                products.append(prod[1])
                db.mark_product_sold(prod[0])
            else:
                break

        if products:
            db.update_order_status(order_id, 'completed')
            db.add_to_total_spent(user_id, total)
            text = f'✅ Успешная покупка!\n\nВаши товары:\n\n'
            text += '\n---\n'.join(products)
            try:
                bot.edit_message_text(text, chat_id, message_id)
            except:
                bot.send_message(chat_id, text)
        else:
            db.update_order_status(order_id, 'failed')
            try:
                bot.edit_message_text('❌ Товары закончились, деньги будут возвращены', chat_id, message_id)
            except:
                bot.send_message(chat_id, '❌ Товары закончились, деньги будут возвращены')

def crypto_polling_worker():
    """background thread: check pending crypto invoices every 8 seconds"""
    while True:
        try:
            with _crypto_pending_lock:
                to_check = list(_crypto_pending.items())
            for inv_id, pending in to_check:
                try:
                    paid = check_crypto_payment(inv_id)
                    if paid:
                        deliver_crypto_payment(pending)
                        with _crypto_pending_lock:
                            _crypto_pending.pop(inv_id, None)
                    else:
                        with _crypto_pending_lock:
                            pending['tries'] += 1
                            # remove after 180 tries (~24 min)
                            if pending['tries'] > 180:
                                _crypto_pending.pop(inv_id, None)
                except Exception as e:
                    logging.error(f'crypto poll error {inv_id}: {e}')
        except Exception as e:
            logging.error(f'crypto poll worker error: {e}')
        time.sleep(8)

def start_crypto_poller():
    t = threading.Thread(target=crypto_polling_worker, daemon=True)
    t.start()



# ---- CRYPTO BOT ----
def create_crypto_invoice(amount_usd, description=''):
    """Create invoice via CryptoBot API"""
    if not CRYPTO_BOT_TOKEN:
        return None
    try:
        url = 'https://pay.crypt.bot/api/createInvoice'
        headers = {
            'Crypto-Pay-API-Token': CRYPTO_BOT_TOKEN,
            'Content-Type': 'application/json'
        }
        data = {
            'asset': 'USDT',
            'amount': str(amount_usd),
            'description': description[:64],
            'expires_in': 1800
        }
        resp = requests.post(url, headers=headers, json=data, timeout=10).json()
        if resp.get('ok'):
            return resp['result']
        return None
    except:
        return None


def check_crypto_payment(invoice_id):
    """Check payment status"""
    if not CRYPTO_BOT_TOKEN:
        return None
    try:
        url = 'https://pay.crypt.bot/api/getInvoices'
        headers = {'Crypto-Pay-API-Token': CRYPTO_BOT_TOKEN}
        resp = requests.get(url, headers=headers, params={'invoice_ids': invoice_id}, timeout=10).json()
        if resp.get('ok') and resp['result']:
            return resp['result']['items'][0].get('status') == 'paid'
        return False
    except:
        return False


@bot.callback_query_handler(func=lambda c: c.data.startswith('pay_crypto_'))
def pay_crypto(call):
    code = call.data.split('_')[2]
    cat = db.get_category(code)
    if not cat:
        bot.answer_callback_query(call.id, 'Ошибка')
        return

    if db.get_setting('cryptobot_enabled') != '1':
        bot.answer_callback_query(call.id, 'CryptoBot отключен')
        return

    # get quantity from message
    qty = 1
    try:
        text = call.message.text
        if '🔢' in text:
            for p in text.split():
                if 'шт' in p:
                    qty = int(p.replace('🔢', '').replace('шт.', '').strip())
                    break
    except:
        qty = 1

    total = db.get_final_price(cat[4]) * qty

    # check wholesale
    wholesale_limit = int(db.get_setting('wholesale_limit') or 30)
    if qty >= wholesale_limit:
        bot.edit_message_text(
            f'📦 Оптовая покупка ({qty} шт.) оформляется напрямую через администратора',
            call.message.chat.id, call.message.message_id,
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton('👤 Написать админу', url=f'https://t.me/kostyasafe'),
                InlineKeyboardButton('↩️ Назад', callback_data='back_to_catalog')
            )
        )
        bot.answer_callback_query(call.id)
        return

    invoice = create_crypto_invoice(total, f'{cat[2]} ({code}) x{qty}')
    if invoice:
        invoice_url = invoice.get('pay_url') or invoice.get('bot_invoice_url')
        invoice_id = invoice['invoice_id']

        # register for auto-polling
        register_pending_invoice(
            invoice_id, call.from_user.id, code, qty,
            call.message.chat.id, call.message.message_id,
            cat, total
        )

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('💳 Оплатить', url=invoice_url))
        markup.add(InlineKeyboardButton('🔄 Проверить статус', callback_data=f'check_crypto_{code}_{invoice_id}'))
        markup.add(InlineKeyboardButton('↩️ Отмена', callback_data=f'cat_{code}'))

        bot.edit_message_text(
            f'💎 Оплата через CryptoBot\n\nТовар: {cat[3]} {cat[2]}\nСумма: {total}$\nКоличество: {qty} шт.\n\n💡 После оплаты товар будет выдан автоматически.\nЕсли товар не пришёл в течение минуты — нажми «Проверить статус»:',
            call.message.chat.id, call.message.message_id,
            reply_markup=markup
        )
    else:
        bot.answer_callback_query(call.id, 'Ошибка создания счета, попробуйте позже')


@bot.callback_query_handler(func=lambda c: c.data.startswith('check_crypto_'))
def check_crypto_payment_callback(call):
    parts = call.data.split('_')
    code = parts[2]
    invoice_id = parts[3]
    cat = db.get_category(code)
    if not cat:
        bot.answer_callback_query(call.id, 'Ошибка')
        return

    paid = check_crypto_payment(invoice_id)
    if paid:
        # deliver products
        qty = 1
        try:
            text = call.message.text
            if 'Количество:' in text:
                for line in text.split('\n'):
                    if 'Количество:' in line:
                        qty = int(line.split(':')[1].strip().replace('шт.', '').strip())
                        break
        except:
            qty = 1

        total = db.get_final_price(cat[4]) * qty
        order_id = db.create_order(call.from_user.id, code, qty, total, 'cryptobot')

        if cat[6] == 'manual':
            # manual delivery
            db.create_manual_order(order_id, call.from_user.id, code)
            db.update_order_status(order_id, 'pending_number')
            bot.edit_message_text(
                f'✅ Оплата получена!\n\nЗаказ #{order_id}\nОжидайте, администратор скоро предоставит данные',
                call.message.chat.id, call.message.message_id
            )
            # notify admins
            for aid in ADMIN_IDS:
                try:
                    bot.send_message(
                        aid,
                        f'⚠️ Новый заказ #{order_id}!\nТовар: {cat[3]} {cat[2]} (Ручная выдача)\nОжидание номера...',
                        reply_markup=InlineKeyboardMarkup().add(
                            InlineKeyboardButton('📥 Скинуть номер', callback_data=f'manual_phone_')
                        )
                    )
                except:
                    pass
        else:
            # auto delivery
            products = []
            for _ in range(qty):
                prod = db.get_product_for_sale(code)
                if prod:
                    products.append(prod[1])
                    db.mark_product_sold(prod[0])
                else:
                    break

            if products:
                db.update_order_status(order_id, 'completed')
                db.add_to_total_spent(call.from_user.id, total)
                text = f'✅ Успешная покупка!\n\nВаши товары:\n\n'
                text += '\n---\n'.join(products)
                bot.edit_message_text(
                    text,
                    call.message.chat.id, call.message.message_id
                )
            else:
                db.update_order_status(order_id, 'failed')
                bot.edit_message_text(
                    '❌ Товары закончились, деньги будут возвращены',
                    call.message.chat.id, call.message.message_id
                )
    else:
        bot.answer_callback_query(call.id, '❌ Платеж не найден или не подтвержден. Попробуйте позже.')


# ---- TELEGRAM STARS ----
@bot.callback_query_handler(func=lambda c: c.data.startswith('pay_stars_'))
def pay_stars(call):
    code = call.data.split('_')[2]
    cat = db.get_category(code)
    if not cat:
        bot.answer_callback_query(call.id, 'Ошибка')
        return

    if db.get_setting('stars_enabled') != '1':
        bot.answer_callback_query(call.id, 'Оплата Звездами отключена')
        return

    qty = 1
    try:
        text = call.message.text
        if '🔢' in text:
            for p in text.split():
                if 'шт' in p:
                    qty = int(p.replace('🔢', '').replace('шт.', '').strip())
                    break
    except:
        qty = 1

    total_usd = db.get_final_price(cat[4]) * qty
    stars_rate = float(db.get_setting('stars_rate') or 1.0)
    total_stars = int(total_usd * stars_rate)
    if total_stars < 1:
        total_stars = 1

    prices = [LabeledPrice(label=f'{cat[3]} {cat[2]} x{qty}', amount=total_stars)]

    try:
        bot.send_invoice(
            call.message.chat.id,
            title=f'{cat[3]} {cat[2]}',
            description=f'{cat[2]} x{qty}',
            invoice_payload=f'stars_{code}_{qty}',
            provider_token=PAYMENTS_PROVIDER_TOKEN or '',
            currency='XTR',
            prices=prices,
            start_parameter='shop',
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton('↩️ Отмена', callback_data=f'cat_{code}')
            )
        )
    except Exception as e:
        bot.answer_callback_query(call.id, f'Ошибка отправки инвойса: {e}')


@bot.pre_checkout_query_handler(func=lambda q: True)
def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@bot.message_handler(content_types=['successful_payment'])
def successful_payment(message):
    payload = message.successful_payment.invoice_payload
    if payload.startswith('stars_'):
        parts = payload.split('_')
        code = parts[1]
        qty = int(parts[2])
        cat = db.get_category(code)
        if not cat:
            return

        total = db.get_final_price(cat[4]) * qty
        order_id = db.create_order(message.from_user.id, code, qty, total, 'stars')

        if cat[6] == 'manual':
            db.create_manual_order(order_id, message.from_user.id, code)
            db.update_order_status(order_id, 'pending_number')
            bot.send_message(
                message.chat.id,
                f'✅ Оплата Звездами получена!\n\nЗаказ #{order_id}\nОжидайте, администратор скоро предоставит данные'
            )
            for aid in ADMIN_IDS:
                try:
                    bot.send_message(aid, f'⚠️ Новый заказ #{order_id}!\nТовар: {cat[3]} {cat[2]} (Ручная выдача / Stars)')
                except:
                    pass
        else:
            products = []
            for _ in range(qty):
                prod = db.get_product_for_sale(code)
                if prod:
                    products.append(prod[1])
                    db.mark_product_sold(prod[0])
                else:
                    break

            if products:
                db.update_order_status(order_id, 'completed')
                db.add_to_total_spent(message.from_user.id, total)
                text = f'✅ Успешная покупка!\n\nВаши товары:\n\n'
                text += '\n---\n'.join(products)
                bot.send_message(message.chat.id, text)
            else:
                db.update_order_status(order_id, 'failed')
                bot.send_message(message.chat.id, '❌ Товары закончились')


# ---- YOOMONEY ----
@bot.callback_query_handler(func=lambda c: c.data.startswith('pay_yoo_'))
def pay_yoomoney(call):
    code = call.data.split('_')[2]
    cat = db.get_category(code)
    if not cat:
        bot.answer_callback_query(call.id, 'Ошибка')
        return

    if db.get_setting('yoomoney_enabled') != '1':
        bot.answer_callback_query(call.id, 'ЮMoney отключен')
        return

    qty = 1
    try:
        text = call.message.text
        if '🔢' in text:
            for p in text.split():
                if 'шт' in p:
                    qty = int(p.replace('🔢', '').replace('шт.', '').strip())
                    break
    except:
        qty = 1

    total = db.get_final_price(cat[4]) * qty
    total_rub = int(total * 88)

    # generate payment link using YooMoney
    # simplified: just show recipient for p2p
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton('💳 Оплатить', url=f'https://yoomoney.ru/to/{YOOMONEY_RECEIVER}'),
        InlineKeyboardButton('✅ Я оплатил', callback_data=f'check_yoo_{code}_{qty}'),
        InlineKeyboardButton('↩️ Отмена', callback_data=f'cat_{code}')
    )

    bot.edit_message_text(
        f'💳 Оплата через ЮMoney\n\nТовар: {cat[3]} {cat[2]}\nСумма: {total_rub} руб (~{total}$)\nКоличество: {qty} шт.\n\nПереведите нужную сумму на кошелек, затем нажмите «Я оплатил»:',
        call.message.chat.id, call.message.message_id,
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith('check_yoo_'))
def check_yoo_payment(call):
    # manual check of yoomoney payment
    # in real implementation would check via API
    parts = call.data.split('_')
    code = parts[2]
    qty = int(parts[3]) if len(parts) > 3 else 1
    cat = db.get_category(code)
    if not cat:
        bot.answer_callback_query(call.id, 'Ошибка')
        return

    bot.answer_callback_query(call.id, '⏳ Ожидание подтверждения...')
    # manual confirmation flow
    for aid in ADMIN_IDS:
        try:
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton('✅ Подтвердить', callback_data=f'confirm_yoo_{call.from_user.id}_{code}_{qty}'),
                InlineKeyboardButton('❌ Отклонить', callback_data=f'reject_yoo_{call.from_user.id}')
            )
            bot.send_message(
                aid,
                f'💳 Запрос на подтверждение ЮMoney\nПользователь: @{call.from_user.username or call.from_user.id}\nТовар: {cat[3]} {cat[2]}\nСумма: {db.get_final_price(cat[4]) * qty}$\nКоличество: {qty}',
                reply_markup=markup
            )
        except:
            pass

    bot.send_message(
        call.message.chat.id,
        '⏳ Ожидайте подтверждения оплаты администратором'
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith('confirm_yoo_'))
def confirm_yoo(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    parts = call.data.split('_')
    user_id = int(parts[2])
    code = parts[3]
    qty = int(parts[4])
    cat = db.get_category(code)
    if not cat:
        bot.answer_callback_query(call.id, 'Ошибка')
        return

    total = db.get_final_price(cat[4]) * qty
    order_id = db.create_order(user_id, code, qty, total, 'yoomoney')

    if cat[6] == 'manual':
        db.create_manual_order(order_id, user_id, code)
        db.update_order_status(order_id, 'pending_number')
        try:
            bot.send_message(user_id, f'✅ Оплата подтверждена!\n\nЗаказ #{order_id}\nОжидайте данные от администратора')
        except:
            pass
    else:
        products = []
        for _ in range(qty):
            prod = db.get_product_for_sale(code)
            if prod:
                products.append(prod[1])
                db.mark_product_sold(prod[0])
            else:
                break
        if products:
            db.update_order_status(order_id, 'completed')
            db.add_to_total_spent(user_id, total)
            try:
                text = f'✅ Оплата подтверждена!\n\nВаши товары:\n\n'
                text += '\n---\n'.join(products)
                bot.send_message(user_id, text)
            except:
                pass

    bot.answer_callback_query(call.id, '✅ Подтверждено')
    bot.edit_message_text('✅ Платеж подтвержден', call.message.chat.id, call.message.message_id)


@bot.callback_query_handler(func=lambda c: c.data.startswith('reject_yoo_'))
def reject_yoo(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    user_id = int(call.data.split('_')[2])
    try:
        bot.send_message(user_id, '❌ Платеж не подтвержден. Попробуйте другой способ оплаты.')
    except:
        pass
    bot.answer_callback_query(call.id, '❌ Отклонено')


# ---- MANUAL PAYMENT ----
@bot.callback_query_handler(func=lambda c: c.data == 'deposit')
def deposit(call):
    bot.edit_message_text(
        '💳 Пополнение баланса\nВыберите способ:',
        call.message.chat.id, call.message.message_id,
        reply_markup=deposit_methods()
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith('deposit_'))
def deposit_method(call):
    method = call.data.split('_')[1]
    if method == 'crypto':
        invoice = create_crypto_invoice(10, 'Пополнение баланса')
        if invoice:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton('💳 Оплатить', url=invoice.get('pay_url', '')))
            markup.add(InlineKeyboardButton('✅ Я оплатил', callback_data=f'deposit_check_crypto_{invoice["invoice_id"]}'))
            markup.add(InlineKeyboardButton('↩️ Назад', callback_data='back_main'))
            bot.edit_message_text(
                '💎 Пополнение через CryptoBot\n\nМинимальная сумма: 10$\nОтправьте любую сумму через кнопку ниже:',
                call.message.chat.id, call.message.message_id,
                reply_markup=markup
            )
        else:
            bot.answer_callback_query(call.id, 'Ошибка, попробуйте позже')
    elif method == 'yoo':
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton('💳 Отправить', url=f'https://yoomoney.ru/to/{YOOMONEY_RECEIVER}'),
            InlineKeyboardButton('✅ Я оплатил', callback_data='deposit_check_yoo'),
            InlineKeyboardButton('↩️ Назад', callback_data='back_main')
        )
        bot.edit_message_text(
            '💳 Пополнение через ЮMoney\n\nПереведите любую сумму на кошелек админа и нажмите «Я оплатил»',
            call.message.chat.id, call.message.message_id,
            reply_markup=markup
        )
    elif method == 'stars':
        prices = [LabeledPrice(label='Пополнение баланса (10 звезд)', amount=10)]
        try:
            bot.send_invoice(
                call.message.chat.id,
                title='Пополнение баланса',
                description='Пополнение баланса через Telegram Stars',
                invoice_payload='deposit_stars',
                provider_token=PAYMENTS_PROVIDER_TOKEN or '',
                currency='XTR',
                prices=prices,
                start_parameter='deposit'
            )
        except Exception as e:
            bot.answer_callback_query(call.id, f'Ошибка: {e}')
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith('deposit_check_crypto_'))
def check_deposit_crypto(call):
    invoice_id = call.data.split('_')[3]
    paid = check_crypto_payment(invoice_id)
    if paid:
        db.update_balance(call.from_user.id, 10)
        bot.edit_message_text(
            '✅ Баланс пополнен на 10$!',
            call.message.chat.id, call.message.message_id,
            reply_markup=main_menu()
        )
    else:
        bot.answer_callback_query(call.id, '❌ Платеж не найден')


@bot.callback_query_handler(func=lambda c: c.data == 'deposit_check_yoo')
def check_deposit_yoo(call):
    for aid in ADMIN_IDS:
        try:
            bot.send_message(
                aid,
                f'💳 Пользователь @{call.from_user.username or call.from_user.id} пополнил через ЮMoney\nПроверьте и начислите баланс',
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton('✅ Начислить 10$', callback_data=f'add_balance_{call.from_user.id}_10'),
                    InlineKeyboardButton('↩️ Другая сумма', callback_data=f'add_balance_{call.from_user.id}_custom')
                )
            )
        except:
            pass
    bot.answer_callback_query(call.id, '⏳ Ожидайте подтверждения')


@bot.callback_query_handler(func=lambda c: c.data.startswith('add_balance_'))
def add_balance_admin(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    parts = call.data.split('_')
    user_id = int(parts[2])
    amount = parts[3]

    if amount == 'custom':
        msg = bot.send_message(call.message.chat.id, f'Введите сумму для начисления пользователю {user_id}:')
        bot.register_next_step_handler(msg, lambda m: process_custom_balance(m, user_id))
    else:
        amount = float(amount)
        db.update_balance(user_id, amount)
        try:
            bot.send_message(user_id, f'💰 Вам начислено {amount}$ на баланс!')
        except:
            pass
        bot.answer_callback_query(call.id, f'✅ Начислено {amount}$')
        bot.edit_message_text(f'✅ Начислено {amount}$ пользователю {user_id}', call.message.chat.id, call.message.message_id)


def process_custom_balance(message, user_id):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            raise ValueError
        db.update_balance(user_id, amount)
        try:
            bot.send_message(user_id, f'💰 Вам начислено {amount}$ на баланс!')
        except:
            pass
        bot.send_message(message.chat.id, f'✅ Начислено {amount}$ пользователю {user_id}', reply_markup=admin_back())
    except:
        bot.send_message(message.chat.id, 'Неверное значение')
