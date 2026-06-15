import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import bot, db, UserStates
from config import ADMIN_IDS
from keyboards import *
from utils import get_flag


@bot.message_handler(func=lambda m: m.text in ['Каталог товаров', '/start', '/catalog'])
def catalog_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ''
    first_name = message.from_user.first_name or ''
    db.register_user(user_id, username, first_name)

    if message.text == '/start':
        bot.send_message(
            user_id,
            'Добро пожаловать в магазин аккаунтов\n\n'
            'Здесь вы можете купить аккаунты и номера по лучшим ценам',
            reply_markup=main_menu()
        )

    categories = db.get_all_categories()
    if not categories:
        bot.send_message(user_id, 'Каталог пуст, загляните позже', reply_markup=main_menu())
        return

    markup = catalog_grid(categories, page=0, sort='cheap')
    bot.send_message(
        user_id,
        'Каталог товаров\n'
        'Выберите страну из списка ниже:',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith('catalog_page_'))
def catalog_page(call):
    page = int(call.data.split('_')[2])
    categories = db.get_all_categories()
    if not categories:
        bot.answer_callback_query(call.id, 'Нет категорий')
        return
    markup = catalog_grid(categories, page=page, sort='cheap')
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith('sort_'))
def catalog_sort(call):
    sort = 'cheap' if 'cheap' in call.data else 'expensive'
    categories = db.get_all_categories()
    markup = catalog_grid(categories, page=0, sort=sort)
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
    except:
        pass
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith('cat_'))
def show_category(call):
    code = call.data.split('_')[1]
    cat = db.get_category(code)
    if not cat:
        bot.answer_callback_query(call.id, 'Категория не найдена')
        return

    stock = db.get_category_stock(code)
    final_price = db.get_final_price(cat[4])
    delivery_info = 'логин:пароль | TData сессия'

    text = (
        f'📱 КАТЕГОРИЯ: {cat[3]} {cat[2]} ({cat[1]})\n'
        f'💰 Цена за шт: {final_price}$\n'
        f'📦 В наличии: {stock} шт.\n'
        f'ℹ️ Формат: {delivery_info}'
    )

    markup = product_card(cat, quantity=1)
    image = db.get_category_image(code)
    
    try:
        if image:
            # delete old text message and send photo instead
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_photo(call.message.chat.id, image, caption=text, reply_markup=markup)
        else:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except:
        if image:
            bot.send_photo(call.message.chat.id, image, caption=text, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith('qty_'))
def change_quantity(call):
    parts = call.data.split('_')
    action = parts[1]
    code = parts[2]
    cat = db.get_category(code)
    if not cat:
        bot.answer_callback_query(call.id, 'Ошибка')
        return

    current_text = call.message.text or call.message.caption or ''
    quantity = 1
    if '🔢' in current_text:
        try:
            qty_part = [p for p in current_text.split() if 'шт' in p][0]
            quantity = int(qty_part.replace('🔢', '').replace('шт.', '').strip())
        except:
            quantity = 1

    if action == 'inc':
        quantity += 1
        if quantity > 100:
            quantity = 100
    elif action == 'dec':
        quantity -= 1
        if quantity < 1:
            quantity = 1

    final_price = db.get_final_price(cat[4]) * quantity
    stock = db.get_category_stock(code)
    delivery_info = 'логин:пароль | TData сессия'

    text = (
        f'📱 КАТЕГОРИЯ: {cat[3]} {cat[2]} ({cat[1]})\n'
        f'💰 Цена за шт: {final_price / quantity:.2f}$\n'
        f'📦 В наличии: {stock} шт.\n'
        f'ℹ️ Формат: {delivery_info}'
    )
    markup = product_card(cat, quantity=quantity)
    image = db.get_category_image(code)
    try:
        if image and call.message.photo:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_photo(call.message.chat.id, image, caption=text, reply_markup=markup)
        else:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except:
        if image:
            bot.send_photo(call.message.chat.id, image, caption=text, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)
    bot.answer_callback_query(call.id, f'Количество: {quantity}')


@bot.callback_query_handler(func=lambda c: c.data == 'back_to_catalog')
def back_to_catalog(call):
    categories = db.get_all_categories()
    markup = catalog_grid(categories, page=0, sort='cheap')
    text = '🛍 Каталог товаров\nВыберите страну из списка ниже:'
    try:
        if call.message.photo:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, text, reply_markup=markup)
        else:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except:
        bot.send_message(call.message.chat.id, text, reply_markup=markup)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == 'search_geo')
def search_geo(call):
    msg = bot.send_message(call.message.chat.id, 'Введите название страны или код для поиска:')
    bot.register_next_step_handler(msg, process_geo_search)
    bot.answer_callback_query(call.id)


def process_geo_search(message):
    query = message.text.strip()
    results = db.search_categories(query)
    if not results:
        bot.send_message(message.chat.id, 'Ничего не найдено, попробуйте иначе', reply_markup=main_menu())
        return

    markup = InlineKeyboardMarkup(row_width=2)
    for cat in results[:10]:
        markup.add(InlineKeyboardButton(f'{cat[3]} {cat[2]} ({cat[4]}$)', callback_data=f'cat_{cat[1]}'))
    markup.add(InlineKeyboardButton('↩️ В каталог', callback_data='back_to_catalog'))
    bot.send_message(message.chat.id, 'Результаты поиска:', reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data == 'noop')
def noop(call):
    bot.answer_callback_query(call.id)
