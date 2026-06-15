from bot import bot, db
from keyboards import *
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


@bot.message_handler(func=lambda m: m.text == 'Мой профиль')
def profile(message):
    user = db.get_user(message.from_user.id)
    if not user:
        db.register_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
        user = db.get_user(message.from_user.id)

    orders = db.get_user_orders(message.from_user.id)
    orders_text = '\n'.join([f'#{o[0]} | {o[2]} | {o[4]}$ | {o[6]}' for o in orders[:5]]) or 'Нет заказов'

    text = (
        f'👤 Мой профиль\n'
        f'ID: {message.from_user.id}\n'
        f'Баланс: {user[3]:.2f}$\n'
        f'Звёзды: {user[4]}\n'
        f'Всего потрачено: {user[6]:.2f}$\n'
        f'Последние заказы:\n{orders_text}'
    )
    bot.send_message(message.chat.id, text, reply_markup=profile_menu())


@bot.callback_query_handler(func=lambda c: c.data == 'my_orders')
def my_orders(call):
    orders = db.get_user_orders(call.from_user.id)
    if not orders:
        bot.answer_callback_query(call.id, 'У вас нет заказов')
        return

    text = '📋 Мои заказы:\n\n'
    for o in orders[:10]:
        status_emoji = '✅' if o[6] == 'completed' else '⏳' if o[6] == 'pending' else '❌'
        text += f'{status_emoji} #{o[0]} | {o[2]} | {o[4]}$ | {o[7][:16]}\n'

    bot.edit_message_text(
        text,
        call.message.chat.id, call.message.message_id,
        reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('↩️ Назад', callback_data='back_main_profile'))
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == 'back_main_profile')
def back_main_profile(call):
    user = db.get_user(call.from_user.id)
    orders = db.get_user_orders(call.from_user.id)
    orders_text = '\n'.join([f'#{o[0]} | {o[2]} | {o[4]}$ | {o[6]}' for o in orders[:5]]) or 'Нет заказов'
    text = (
        f'👤 Мой профиль\n'
        f'ID: {call.from_user.id}\n'
        f'Баланс: {user[3]:.2f}$\n'
        f'Звёзды: {user[4]}\n'
        f'Всего потрачено: {user[6]:.2f}$\n'
        f'Последние заказы:\n{orders_text}'
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=profile_menu())
    bot.answer_callback_query(call.id)