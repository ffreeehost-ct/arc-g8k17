from bot import bot, db, UserStates
from keyboards import *


@bot.message_handler(func=lambda m: m.text == 'Акции / Коды')
def promo_menu_user(message):
    msg = bot.send_message(
        message.chat.id,
        '🎟️ Введите промокод:',
        reply_markup=main_menu()
    )
    bot.set_state(message.from_user.id, UserStates.waiting_promo_code, message.chat.id)


@bot.message_handler(state=UserStates.waiting_promo_code)
def process_promo_code(message):
    code = message.text.strip().upper()
    promo = db.get_promo(code)

    if not promo:
        bot.send_message(
            message.chat.id,
            '❌ Промокод не найден или истек',
            reply_markup=main_menu()
        )
        bot.delete_state(message.from_user.id, message.chat.id)
        return

    if promo[4] >= promo[3]:
        bot.send_message(
            message.chat.id,
            '❌ Промокод уже использован максимальное количество раз',
            reply_markup=main_menu()
        )
        bot.delete_state(message.from_user.id, message.chat.id)
        return

    # apply promo
    amount = promo[2]
    db.update_balance(message.from_user.id, amount)
    db.use_promo(promo[0])

    bot.send_message(
        message.chat.id,
        f'✅ Промокод {code} активирован!\n💰 На ваш баланс начислено {amount}$',
        reply_markup=main_menu()
    )
    bot.delete_state(message.from_user.id, message.chat.id)


@bot.message_handler(func=lambda m: m.text == 'Служба поддержки')
def support(message):
    bot.send_message(
        message.chat.id,
        '🆘 Служба поддержки\n\nПо всем вопросам пишите администратору:',
        reply_markup=support_button()
    )


@bot.callback_query_handler(func=lambda c: c.data == 'back_main')
def back_to_main(call):
    bot.edit_message_text(
        'Главное меню',
        call.message.chat.id, call.message.message_id,
        reply_markup=main_menu()
    )
    bot.answer_callback_query(call.id)