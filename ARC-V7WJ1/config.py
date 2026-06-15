import os

BOT_TOKEN = '8616890979:AAHRaN55414FvQgJDxL4zWU4s1U-UOMNdtE'
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '123456789').split(',')]

# crypto bot
CRYPTO_BOT_TOKEN = '595218:AAeF65BPlXrA20wuOAwJVQET7RaSxvv9iyL'

# yoomoney
YOOMONEY_RECEIVER = '4100119548499139'
YOOMONEY_RECEIVER_NAME = 'Антонина Николаевна .К'
YOOMONEY_SECRET = os.getenv('YOOMONEY_SECRET', '')  # если есть секрет — впиши сюда

# stars rate: 1 rub = X stars
DEFAULT_STARS_RATE = 1.0

# db path
DB_PATH = 'shop.db'

# bot username for stars
BOT_USERNAME = os.getenv('BOT_USERNAME', 'YourBot')

# provider token for stars (test or live)
PAYMENTS_PROVIDER_TOKEN = os.getenv('PAYMENTS_PROVIDER_TOKEN', '')
