from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        KeyboardButton('Каталог товаров'),
        KeyboardButton('Мой профиль')
    )
    markup.row(
        KeyboardButton('Пополнить баланс'),
        KeyboardButton('Акции / Коды')
    )
    markup.row(KeyboardButton('Служба поддержки'))
    return markup


def catalog_sort_buttons(current_sort='cheap'):
    markup = InlineKeyboardMarkup(row_width=2)
    if current_sort == 'cheap':
        markup.add(
            InlineKeyboardButton(' Сначала дешевые', callback_data='sort_cheap'),
            InlineKeyboardButton(' Сначала дорогие', callback_data='sort_expensive')
        )
    else:
        markup.add(
            InlineKeyboardButton(' Сначала дешевые', callback_data='sort_cheap'),
            InlineKeyboardButton(' Сначала дорогие', callback_data='sort_expensive')
        )
    return markup


def catalog_grid(categories, page=0, sort='cheap', per_page=12):
    markup = InlineKeyboardMarkup(row_width=4)
    if sort == 'cheap':
        sorted_cats = sorted(categories, key=lambda c: c[4])
    else:
        sorted_cats = sorted(categories, key=lambda c: c[4], reverse=True)

    total_pages = (len(sorted_cats) + per_page - 1) // per_page
    page_cats = sorted_cats[page * per_page: (page + 1) * per_page]

    for i in range(0, len(page_cats), 4):
        row = page_cats[i:i+4]
        buttons = []
        for cat in row:
            code, name, flag, base_price = cat[1], cat[2], cat[3], cat[4]
            btn_text = f'{flag} {base_price}$'
            buttons.append(InlineKeyboardButton(btn_text, callback_data=f'cat_{code}'))
        markup.row(*buttons)

    # nav row
    nav_btns = []
    if page > 0:
        nav_btns.append(InlineKeyboardButton('◀️ Назад', callback_data=f'catalog_page_{page-1}'))
    nav_btns.append(InlineKeyboardButton(f'📄 {page+1}/{total_pages}', callback_data='noop'))
    if page < total_pages - 1:
        nav_btns.append(InlineKeyboardButton('Вперед ▶️', callback_data=f'catalog_page_{page+1}'))
    markup.row(*nav_btns)

    # sort + search
    markup.row(
        InlineKeyboardButton('🟢 Дешевле', callback_data='sort_cheap'),
        InlineKeyboardButton('⚪ Дороже', callback_data='sort_expensive'),
        InlineKeyboardButton('🔍 Поиск по ГЕО', callback_data='search_geo')
    )
    return markup


def product_card(category, quantity=1, in_cart=False):
    markup = InlineKeyboardMarkup(row_width=3)
    markup.row(
        InlineKeyboardButton('➖ Убавить', callback_data=f'qty_dec_{category[1]}'),
        InlineKeyboardButton(f'🔢 {quantity} шт.', callback_data='noop'),
        InlineKeyboardButton('Прибавить ➕', callback_data=f'qty_inc_{category[1]}')
    )

    # payment methods - 2 columns
    markup.row(
        InlineKeyboardButton('💎 CryptoBot', callback_data=f'pay_crypto_{category[1]}'),
        InlineKeyboardButton('⭐️ Stars', callback_data=f'pay_stars_{category[1]}'),
    )
    markup.row(
        InlineKeyboardButton('💳 ЮMoney', callback_data=f'pay_yoo_{category[1]}'),
        InlineKeyboardButton('↩️ Назад', callback_data='back_to_catalog'),
    )
    return markup


def profile_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton('📊 Мои заказы', callback_data='my_orders'),
        InlineKeyboardButton('💰 Пополнить баланс', callback_data='deposit'),
        InlineKeyboardButton('↩️ На главную', callback_data='back_main')
    )
    return markup


def deposit_methods():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton('💎 CryptoBot (USDT/TON)', callback_data='deposit_crypto'),
        InlineKeyboardButton('💳 ЮMoney (Рубли)', callback_data='deposit_yoo'),
        InlineKeyboardButton('⭐️ Пополнить Звездами', callback_data='deposit_stars'),
        InlineKeyboardButton('↩️ Назад', callback_data='back_main')
    )
    return markup


def support_button():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('✍️ Написать админу', url='https://t.me/kostyasafe'))
    return markup


def admin_main_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton('📈 Скидка', callback_data='admin_discount'),
        InlineKeyboardButton('📊 Наценка', callback_data='admin_markup'),
        InlineKeyboardButton('💰 Курс Звезд', callback_data='admin_stars_rate'),
        InlineKeyboardButton('🗄️ Управление БД', callback_data='admin_manage_db'),
        InlineKeyboardButton('💳 Платежные шлюзы', callback_data='admin_payments'),
        InlineKeyboardButton('🎟️ Промокоды', callback_data='admin_promo'),
        InlineKeyboardButton('🤝 Оптовый лимит', callback_data='admin_wholesale'),
        InlineKeyboardButton('📦 Ручные заказы', callback_data='admin_manual_orders'),
        InlineKeyboardButton('📊 Статистика', callback_data='admin_stats'),
        InlineKeyboardButton('📨 Рассылка', callback_data='admin_broadcast'),
        InlineKeyboardButton('↩️ Главное меню', callback_data='back_main')
    )
    return markup


def admin_back():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('↩️ Назад в админку', callback_data='admin_menu'))
    return markup


def admin_db_management(categories):
    markup = InlineKeyboardMarkup(row_width=1)
    for cat in categories[:10]:
        has_photo = '📸' if cat[7] else '🖼'
        markup.add(InlineKeyboardButton(
            f'{has_photo} {cat[3]} {cat[2]} ({cat[4]}$)',
            callback_data=f'admin_add_to_{cat[1]}'
        ))
    markup.row(
        InlineKeyboardButton('🖼 Загрузить фото', callback_data='admin_upload_photo'),
    )
    markup.row(
        InlineKeyboardButton('➕ Добавить категорию', callback_data='admin_add_category'),
        InlineKeyboardButton('🔄 Тип выдачи', callback_data='admin_toggle_delivery'),
    )
    markup.row(InlineKeyboardButton('↩️ Назад', callback_data='admin_menu'))
    return markup


def admin_toggle_delivery_cats(categories):
    markup = InlineKeyboardMarkup(row_width=2)
    for cat in categories[:10]:
        label = '🟢 Авто' if cat[6] == 'auto' else '🔴 Ручная'
        markup.add(InlineKeyboardButton(f'{cat[3]} {cat[2]} [{label}]', callback_data=f'admin_toggle_{cat[1]}'))
    markup.add(InlineKeyboardButton('↩️ Назад', callback_data='admin_manage_db'))
    return markup


def admin_manual_order_actions(mo_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton('📥 Скинуть номер', callback_data=f'manual_phone_{mo_id}'),
        InlineKeyboardButton('✍️ Написать клиенту', callback_data=f'manual_write_{mo_id}'),
        InlineKeyboardButton('✅ Завершить', callback_data=f'manual_done_{mo_id}')
    )
    return markup


def admin_payment_toggles():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton('🔄 CryptoBot', callback_data='toggle_cryptobot'),
        InlineKeyboardButton('🔄 Telegram Stars', callback_data='toggle_stars'),
        InlineKeyboardButton('🔄 ЮMoney', callback_data='toggle_yoomoney'),
        InlineKeyboardButton('🔄 Ручная оплата', callback_data='toggle_manual'),
        InlineKeyboardButton('↩️ Назад', callback_data='admin_menu')
    )
    return markup


def promo_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton('🎲 Автогенерация', callback_data='promo_auto'),
        InlineKeyboardButton('✍️ Ручной ввод', callback_data='promo_manual'),
        InlineKeyboardButton('📋 Список промокодов', callback_data='promo_list'),
        InlineKeyboardButton('↩️ Назад', callback_data='admin_menu')
    )
    return markup


def order_actions(order_id):
    markup = InlineKeyboardMarkup(row_width=1)
    if order_id:
        markup.add(InlineKeyboardButton('🔑 Получить код', callback_data=f'get_code_{order_id}'))
    return markup
