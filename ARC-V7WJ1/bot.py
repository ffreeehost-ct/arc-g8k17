import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage

from config import BOT_TOKEN, ADMIN_IDS, DEFAULT_STARS_RATE
from database import Database
from keyboards import *
from utils import *

import handlers.catalog
import handlers.admin
import handlers.payments
import handlers.profile
import handlers.promo
import handlers.seed

bot = telebot.TeleBot(BOT_TOKEN, state_storage=StateMemoryStorage())
db = Database()

class UserStates(StatesGroup):
    waiting_balance_amount = State()
    waiting_promo_code = State()
    # admin states
    admin_waiting_discount = State()
    admin_waiting_markup = State()
    admin_waiting_stars_rate = State()
    admin_waiting_promo_amount = State()
    admin_waiting_promo_code = State()
    admin_waiting_promo_uses = State()
    admin_waiting_custom_promo = State()
    admin_waiting_wholesale_limit = State()
    # manual delivery states
    admin_waiting_phone_number = State()
    admin_waiting_verify_code = State()
    admin_waiting_message_to_user = State()
    # add products
    admin_waiting_add_text = State()
    admin_waiting_category_choice = State()

if __name__ == '__main__':
    handlers.seed.seed_countries()
    handlers.payments.start_crypto_poller()
    print('бот запущен')
    bot.infinity_polling()
