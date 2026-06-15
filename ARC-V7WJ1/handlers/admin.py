import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import bot, db, UserStates
from config import ADMIN_IDS
from keyboards import *


@bot.message_handler(func=lambda m: m.text == '/admin' and m.from_user.id in ADMIN_IDS)
def admin_panel(message):
    bot.send_message(
        message.chat.id,
        '👑 Панель администратора\nВыберите раздел:',
        reply_markup=admin_main_menu()
    )


@bot.callback_query_handler(func=lambda c: c.data == 'admin_menu')
def admin_menu_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, 'Нет доступа')
        return
    bot.edit_message_text(
        '👑 Панель администратора\nВыберите раздел:',
        call.message.chat.id,
        call.message.message_id,
        reply_markup=admin_main_menu()
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == 'admin_stats')
def admin_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, 'Нет доступа')
        return
    users = db.get_all_users_count()
    orders = db.get_all_orders_count()
    revenue = db.get_revenue_total()
    cats = len(db.get_all_categories())
    text = (
        f'📊 Статистика\n\n'
        f'👤 Пользователей: {users}\n'
        f'📦 Категорий: {cats}\n'
        f'📋 Заказов: {orders}\n'
        f'💰 Выручка: {revenue:.2f}$'
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=admin_back())
    bot.answer_callback_query(call.id)


# ----- DISCOUNT -----
@bot.callback_query_handler(func=lambda c: c.data == 'admin_discount')
def admin_discount(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    cur = db.get_setting('discount')
    msg = bot.send_message(
        call.message.chat.id,
        f'Текущая скидка: {cur}%\nВведите новое значение от 0 до 50 (0 = выключить):'
    )
    bot.set_state(call.from_user.id, UserStates.admin_waiting_discount, call.message.chat.id)
    bot.answer_callback_query(call.id)


@bot.message_handler(state=UserStates.admin_waiting_discount)
def process_discount(message):
    try:
        val = int(message.text)
        if val < 0 or val > 50:
            raise ValueError
        db.set_setting('discount', str(val))
        bot.send_message(message.chat.id, f'✅ Скидка установлена: {val}%', reply_markup=admin_back())
        bot.delete_state(message.from_user.id, message.chat.id)

        # auto broadcast
        if val > 0:
            users = db.get_all_users()
            for uid, uname, fname in users:
                try:
                    bot.send_message(
                        uid,
                        f'🔥 Внимание! Администратор включил скидку {val}% на все аккаунты!\nУспей купить по дешевке!',
                        reply_markup=main_menu()
                    )
                except:
                    pass
    except:
        bot.send_message(message.chat.id, 'Неверное значение, введите число от 0 до 50')


# ----- MARKUP -----
@bot.callback_query_handler(func=lambda c: c.data == 'admin_markup')
def admin_markup(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    cur = db.get_setting('markup')
    msg = bot.send_message(
        call.message.chat.id,
        f'Текущая наценка: {cur}%\nВведите новое значение от 0 до 50 (0 = выключить):'
    )
    bot.set_state(call.from_user.id, UserStates.admin_waiting_markup, call.message.chat.id)
    bot.answer_callback_query(call.id)


@bot.message_handler(state=UserStates.admin_waiting_markup)
def process_markup(message):
    try:
        val = int(message.text)
        if val < 0 or val > 50:
            raise ValueError
        db.set_setting('markup', str(val))
        bot.send_message(message.chat.id, f'✅ Наценка установлена: {val}%', reply_markup=admin_back())
        bot.delete_state(message.from_user.id, message.chat.id)
    except:
        bot.send_message(message.chat.id, 'Неверное значение, введите число от 0 до 50')


# ----- STARS RATE -----
@bot.callback_query_handler(func=lambda c: c.data == 'admin_stars_rate')
def admin_stars_rate(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    cur = db.get_setting('stars_rate')
    msg = bot.send_message(
        call.message.chat.id,
        f'Текущий курс: 1 рубль = {cur} звезд\nВведите новый курс (например 1.5):'
    )
    bot.set_state(call.from_user.id, UserStates.admin_waiting_stars_rate, call.message.chat.id)
    bot.answer_callback_query(call.id)


@bot.message_handler(state=UserStates.admin_waiting_stars_rate)
def process_stars_rate(message):
    try:
        val = float(message.text.replace(',', '.'))
        if val <= 0:
            raise ValueError
        db.set_setting('stars_rate', str(val))
        bot.send_message(message.chat.id, f'✅ Курс установлен: 1 рубль = {val} звезд', reply_markup=admin_back())
        bot.delete_state(message.from_user.id, message.chat.id)
    except:
        bot.send_message(message.chat.id, 'Неверное значение, введите положительное число')


# ----- UPLOAD PHOTO FOR CATEGORY -----
@bot.callback_query_handler(func=lambda c: c.data == 'admin_upload_photo')
def admin_upload_photo_start(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    cats = db.get_all_categories()
    markup = InlineKeyboardMarkup(row_width=2)
    for cat in cats[:10]:
        markup.add(InlineKeyboardButton(
            f'{cat[3]} {cat[2]}',
            callback_data=f'admin_setphoto_{cat[1]}'
        ))
    markup.add(InlineKeyboardButton('↩️ Назад', callback_data='admin_manage_db'))
    bot.edit_message_text(
        '🖼 Выберите категорию для загрузки фото:',
        call.message.chat.id, call.message.message_id,
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith('admin_setphoto_'))
def admin_setphoto_cat(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    code = call.data.split('_')[2]
    cat = db.get_category(code)
    if not cat:
        bot.answer_callback_query(call.id, 'Категория не найдена')
        return

    cur_image = db.get_category_image(code)
    text = f'Отправьте фото для категории {cat[3]} {cat[2]} ({code})'
    if cur_image:
        text += '\n\nИли нажмите кнопку чтобы удалить текущее фото'
        markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton('🗑 Удалить фото', callback_data=f'admin_delphoto_{code}')
        )
        msg = bot.send_message(call.message.chat.id, text, reply_markup=markup)
    else:
        msg = bot.send_message(call.message.chat.id, text)
    bot.register_next_step_handler(msg, lambda m: process_upload_photo(m, code))
    bot.answer_callback_query(call.id)


def process_upload_photo(message, code):
    if message.photo:
        file_id = message.photo[-1].file_id
        db.update_category_image(code, file_id)
        bot.send_message(
            message.chat.id,
            f'✅ Фото обновлено для {code}',
            reply_markup=admin_back()
        )
    else:
        bot.send_message(
            message.chat.id,
            '❌ Отправьте именно фото',
            reply_markup=admin_back()
        )


@bot.callback_query_handler(func=lambda c: c.data.startswith('admin_delphoto_'))
def admin_delphoto(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    code = call.data.split('_')[2]
    db.update_category_image(code, None)
    bot.edit_message_text(
        f'✅ Фото удалено для {code}',
        call.message.chat.id, call.message.message_id,
        reply_markup=admin_back()
    )
    bot.answer_callback_query(call.id)


# ----- MANAGE DB -----
@bot.callback_query_handler(func=lambda c: c.data == 'admin_manage_db')
def admin_manage_db(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    categories = db.get_all_categories()
    bot.edit_message_text(
        '🗄️ Управление товарами\nВыберите категорию для добавления товаров:',
        call.message.chat.id,
        call.message.message_id,
        reply_markup=admin_db_management(categories)
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith('admin_add_to_'))
def admin_add_to_category(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    code = call.data.replace('admin_add_to_', '')
    cat = db.get_category(code)
    if not cat:
        bot.answer_callback_query(call.id, 'Категория не найдена')
        return
    msg = bot.send_message(
        call.message.chat.id,
        f'📥 Введите товары для {cat[3]} {cat[2]} ({code})\n\nФормат: каждый товар с новой строки\nМожно отправить .txt файл'
    )
    bot.set_state(call.from_user.id, UserStates.admin_waiting_add_text, call.message.chat.id)
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['add_category_code'] = code
    bot.answer_callback_query(call.id)


@bot.message_handler(state=UserStates.admin_waiting_add_text, content_types=['text', 'document'])
def process_add_products(message):
    code = None
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        code = data.get('add_category_code')

    if not code:
        bot.send_message(message.chat.id, 'Ошибка, попробуйте снова')
        bot.delete_state(message.from_user.id, message.chat.id)
        return

    if message.document:
        # download file
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded = bot.download_file(file_info.file_path)
            text = downloaded.decode('utf-8')
            lines = text.split('\n')
        except:
            bot.send_message(message.chat.id, 'Не удалось прочитать файл')
            return
    else:
        lines = message.text.split('\n')

    db.add_products_bulk(code, lines)
    count = len([l for l in lines if l.strip()])
    bot.send_message(
        message.chat.id,
        f'✅ Добавлено {count} товаров в категорию {code}',
        reply_markup=admin_back()
    )
    bot.delete_state(message.from_user.id, message.chat.id)


@bot.callback_query_handler(func=lambda c: c.data == 'admin_toggle_delivery')
def admin_toggle_delivery(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    categories = db.get_all_categories()
    bot.edit_message_text(
        '🔄 Переключение типа выдачи\nВыберите категорию:',
        call.message.chat.id,
        call.message.message_id,
        reply_markup=admin_toggle_delivery_cats(categories)
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith('admin_toggle_'))
def process_toggle_delivery(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    code = call.data.replace('admin_toggle_', '')
    cat = db.get_category(code)
    if not cat:
        bot.answer_callback_query(call.id, 'Не найдено')
        return
    new_type = 'manual' if cat[6] == 'auto' else 'auto'
    db.set_category_delivery_type(code, new_type)
    bot.answer_callback_query(call.id, f'✅ {cat[2]}: {"ручная" if new_type == "manual" else "авто"} выдача')
    # refresh
    categories = db.get_all_categories()
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                       reply_markup=admin_toggle_delivery_cats(categories))
    except:
        pass


@bot.callback_query_handler(func=lambda c: c.data == 'admin_add_category')
def admin_add_category(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(
        call.message.chat.id,
        'Введите новую категорию в формате:\nКод | Название | Цена\n\nПример: US | США | 0.42'
    )
    bot.register_next_step_handler(msg, process_add_category)
    bot.answer_callback_query(call.id)


def process_add_category(message):
    try:
        parts = message.text.split('|')
        code = parts[0].strip().upper()
        name = parts[1].strip()
        price = float(parts[2].strip().replace(',', '.'))
        flag = get_flag(code)
        if db.add_category(code, name, flag, price):
            bot.send_message(message.chat.id, f'✅ Категория {flag} {name} добавлена', reply_markup=admin_back())
        else:
            bot.send_message(message.chat.id, 'Ошибка: такой код уже существует')
    except Exception as e:
        bot.send_message(message.chat.id, f'Ошибка формата: {e}')


# ----- PAYMENTS -----
@bot.callback_query_handler(func=lambda c: c.data == 'admin_payments')
def admin_payments(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    cb = '🟢 Вкл' if db.get_setting('cryptobot_enabled') == '1' else '🔴 Выкл'
    st = '🟢 Вкл' if db.get_setting('stars_enabled') == '1' else '🔴 Выкл'
    ym = '🟢 Вкл' if db.get_setting('yoomoney_enabled') == '1' else '🔴 Выкл'
    mp = '🟢 Вкл' if db.get_setting('manual_payment_enabled') == '1' else '🔴 Выкл'
    text = (
        f'💳 Управление платежными шлюзами\n\n'
        f'CryptoBot: {cb}\n'
        f'Telegram Stars: {st}\n'
        f'ЮMoney: {ym}\n'
        f'Ручная оплата: {mp}\n\n'
        'Нажмите на шлюз чтобы переключить:'
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=admin_payment_toggles())
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith('toggle_'))
def toggle_payment(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    key_map = {
        'toggle_cryptobot': 'cryptobot_enabled',
        'toggle_stars': 'stars_enabled',
        'toggle_yoomoney': 'yoomoney_enabled',
        'toggle_manual': 'manual_payment_enabled',
    }
    key = key_map.get(call.data)
    if not key:
        bot.answer_callback_query(call.id, 'Ошибка')
        return
    cur = db.get_setting(key)
    new_val = '0' if cur == '1' else '1'
    db.set_setting(key, new_val)
    bot.answer_callback_query(call.id, '✅ Переключено')
    # refresh
    admin_payments(call)


# ----- MANUAL ORDERS -----
@bot.callback_query_handler(func=lambda c: c.data == 'admin_manual_orders')
def admin_manual_orders_list(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    orders = db.get_pending_manual_orders()
    if not orders:
        bot.edit_message_text(
            '📦 Нет активных ручных заказов',
            call.message.chat.id, call.message.message_id,
            reply_markup=admin_back()
        )
        bot.answer_callback_query(call.id)
        return

    text = '📦 Активные ручные заказы:\n\n'
    for o in orders:
        text += f'#{o[1]} | {o[7]} {o[8]} | {o[5]}$ | Статус: {o[3]}\n'
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=admin_back())
    bot.answer_callback_query(call.id)


# ----- WHOLESALE -----
@bot.callback_query_handler(func=lambda c: c.data == 'admin_wholesale')
def admin_wholesale(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    cur = db.get_setting('wholesale_limit')
    msg = bot.send_message(
        call.message.chat.id,
        f'Текущий оптовый лимит: {cur} шт.\nВведите новое значение (минимум 10):'
    )
    bot.set_state(call.from_user.id, UserStates.admin_waiting_wholesale_limit, call.message.chat.id)
    bot.answer_callback_query(call.id)


@bot.message_handler(state=UserStates.admin_waiting_wholesale_limit)
def process_wholesale(message):
    try:
        val = int(message.text)
        if val < 10:
            raise ValueError
        db.set_setting('wholesale_limit', str(val))
        bot.send_message(message.chat.id, f'✅ Лимит опта: {val} шт.', reply_markup=admin_back())
        bot.delete_state(message.from_user.id, message.chat.id)
    except:
        bot.send_message(message.chat.id, 'Неверное значение, введите число от 10')


# ----- PROMO -----
@bot.callback_query_handler(func=lambda c: c.data == 'admin_promo')
def admin_promo(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    bot.edit_message_text(
        '🎟️ Управление промокодами',
        call.message.chat.id, call.message.message_id,
        reply_markup=promo_menu()
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == 'promo_auto')
def promo_auto(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    code = generate_promo_code()
    msg = bot.send_message(call.message.chat.id, f'Сгенерирован код: {code}\nВведите сумму бонуса (в $):')
    bot.set_state(call.from_user.id, UserStates.admin_waiting_promo_amount, call.message.chat.id)
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['promo_code'] = code
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == 'promo_manual')
def promo_manual(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, 'Введите промокод (сам придумайте):')
    bot.set_state(call.from_user.id, UserStates.admin_waiting_custom_promo, call.message.chat.id)
    bot.answer_callback_query(call.id)


@bot.message_handler(state=UserStates.admin_waiting_custom_promo)
def process_custom_promo(message):
    code = message.text.strip().upper()
    bot.send_message(message.chat.id, f'Промокод: {code}\nВведите сумму бонуса (в $):')
    bot.set_state(message.from_user.id, UserStates.admin_waiting_promo_amount, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['promo_code'] = code


@bot.message_handler(state=UserStates.admin_waiting_promo_amount)
def process_promo_amount(message):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            raise ValueError
        bot.send_message(message.chat.id, f'Сумма: {amount}$\nВведите количество активаций:')
        bot.set_state(message.from_user.id, UserStates.admin_waiting_promo_uses, message.chat.id)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['promo_amount'] = amount
    except:
        bot.send_message(message.chat.id, 'Неверная сумма')


@bot.message_handler(state=UserStates.admin_waiting_promo_uses)
def process_promo_uses(message):
    try:
        uses = int(message.text)
        if uses <= 0:
            raise ValueError
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            code = data.get('promo_code')
            amount = data.get('promo_amount')
        db.create_promo(code, amount, uses)
        bot.send_message(
            message.chat.id,
            f'✅ Промокод {code} на {amount}$ ({uses} активаций) создан',
            reply_markup=admin_back()
        )
        bot.delete_state(message.from_user.id, message.chat.id)
    except:
        bot.send_message(message.chat.id, 'Неверное значение')


@bot.callback_query_handler(func=lambda c: c.data == 'promo_list')
def promo_list(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    promos = db.get_all_promos()
    if not promos:
        bot.send_message(call.message.chat.id, 'Нет промокодов', reply_markup=admin_back())
        bot.answer_callback_query(call.id)
        return
    text = '🎟️ Список промокодов:\n\n'
    for p in promos:
        text += f'{p[1]} | {p[2]}$ | Использовано: {p[4]}/{p[3]}\n'
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=admin_back())
    bot.answer_callback_query(call.id)


# ----- BROADCAST -----
@bot.callback_query_handler(func=lambda c: c.data == 'admin_broadcast')
def admin_broadcast(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, '📨 Введите текст для рассылки всем пользователям:')
    bot.register_next_step_handler(msg, process_broadcast)
    bot.answer_callback_query(call.id)


def process_broadcast(message):
    text = message.text
    users = db.get_all_users()
    sent = 0
    failed = 0
    for uid, uname, fname in users:
        try:
            bot.send_message(uid, text, reply_markup=main_menu())
            sent += 1
        except:
            failed += 1
    bot.send_message(
        message.chat.id,
        f'📊 Рассылка завершена\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}',
        reply_markup=admin_back()
    )


# ----- MANUAL DELIVERY CALLBACKS -----
@bot.callback_query_handler(func=lambda c: c.data.startswith('manual_phone_'))
def manual_enter_phone(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    mo_id = int(call.data.split('_')[2])
    msg = bot.send_message(call.message.chat.id, 'Введите номер телефона для отправки клиенту:')
    bot.set_state(call.from_user.id, UserStates.admin_waiting_phone_number, call.message.chat.id)
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['manual_order_id'] = mo_id
    bot.answer_callback_query(call.id)


@bot.message_handler(state=UserStates.admin_waiting_phone_number)
def process_manual_phone(message):
    phone = message.text.strip()
    mo_id = None
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        mo_id = data.get('manual_order_id')
    if not mo_id:
        bot.send_message(message.chat.id, 'Ошибка')
        bot.delete_state(message.from_user.id, message.chat.id)
        return

    mo = db.get_manual_order_by_id(mo_id)
    if not mo:
        bot.send_message(message.chat.id, 'Заказ не найден')
        bot.delete_state(message.from_user.id, message.chat.id)
        return

    db.update_manual_order_by_id(mo_id, 'phone_number', phone)
    db.update_manual_order_by_id(mo_id, 'status', 'pending_code')

    # send to user
    try:
        bot.send_message(
            mo[2],
            f'✅ Ваш номер готов!\n\n{phone}\n\nНажмите кнопку ниже чтобы запросить код подтверждения:',
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton('🔑 Получить код', callback_data=f'get_code_{mo[1]}')
            )
        )
    except:
        bot.send_message(message.chat.id, 'Не удалось отправить номер клиенту')

    bot.send_message(message.chat.id, f'✅ Номер {phone} отправлен клиенту', reply_markup=admin_back())
    bot.delete_state(message.from_user.id, message.chat.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith('get_code_'))
def request_code(call):
    order_id = int(call.data.split('_')[2])
    order = db.get_order(order_id)
    if not order:
        bot.answer_callback_query(call.id, 'Заказ не найден')
        return

    # notify admins
    for admin_id in ADMIN_IDS:
        try:
            mo = db.get_manual_order(order_id)
            if mo:
                bot.send_message(
                    admin_id,
                    f'🔔 Клиент запрашивает код для номера {mo[4]}\nЗаказ #{order_id}',
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton('💬 Отправить код', callback_data=f'manual_code_{mo[0]}'),
                        InlineKeyboardButton('✍️ Написать клиенту', callback_data=f'manual_write_{mo[0]}')
                    )
                )
        except:
            pass
    bot.answer_callback_query(call.id, '✅ Запрос отправлен администратору')


@bot.callback_query_handler(func=lambda c: c.data.startswith('manual_code_'))
def admin_enter_code(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    mo_id = int(call.data.split('_')[2])
    msg = bot.send_message(call.message.chat.id, 'Введите код подтверждения для отправки клиенту:')
    bot.set_state(call.from_user.id, UserStates.admin_waiting_verify_code, call.message.chat.id)
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['manual_order_id'] = mo_id
    bot.answer_callback_query(call.id)


@bot.message_handler(state=UserStates.admin_waiting_verify_code)
def process_verify_code(message):
    code_text = message.text.strip()
    mo_id = None
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        mo_id = data.get('manual_order_id')
    if not mo_id:
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    mo = db.get_manual_order_by_id(mo_id)
    if not mo:
        bot.send_message(message.chat.id, 'Заказ не найден')
        bot.delete_state(message.from_user.id, message.chat.id)
        return

    try:
        bot.send_message(
            mo[2],
            f'✅ Код подтверждения:\n\n{code_text}'
        )
        db.update_manual_order_by_id(mo_id, 'status', 'completed')
        db.update_order_status(mo[1], 'completed')
        bot.send_message(message.chat.id, '✅ Код отправлен клиенту', reply_markup=admin_back())
    except:
        bot.send_message(message.chat.id, 'Не удалось отправить код клиенту')

    bot.delete_state(message.from_user.id, message.chat.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith('manual_write_'))
def admin_write_user(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    mo_id = int(call.data.split('_')[2])
    msg = bot.send_message(call.message.chat.id, 'Введите сообщение для клиента:')
    bot.set_state(call.from_user.id, UserStates.admin_waiting_message_to_user, call.message.chat.id)
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['manual_order_id'] = mo_id
    bot.answer_callback_query(call.id)


@bot.message_handler(state=UserStates.admin_waiting_message_to_user)
def process_admin_message(message):
    msg_text = message.text.strip()
    mo_id = None
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        mo_id = data.get('manual_order_id')
    if not mo_id:
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    mo = db.get_manual_order_by_id(mo_id)
    if not mo:
        bot.send_message(message.chat.id, 'Заказ не найден')
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    try:
        bot.send_message(mo[2], f'📩 Сообщение от администратора:\n\n{msg_text}')
        bot.send_message(message.chat.id, '✅ Сообщение отправлено клиенту', reply_markup=admin_back())
    except:
        bot.send_message(message.chat.id, 'Не удалось отправить сообщение')
    bot.delete_state(message.from_user.id, message.chat.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith('manual_done_'))
def manual_done(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    mo_id = int(call.data.split('_')[2])
    db.update_manual_order_by_id(mo_id, 'status', 'completed')
    mo = db.get_manual_order_by_id(mo_id)
    if mo:
        db.update_order_status(mo[1], 'completed')
    bot.answer_callback_query(call.id, '✅ Заказ завершен')
