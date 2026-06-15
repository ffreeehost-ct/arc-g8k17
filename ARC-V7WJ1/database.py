import sqlite3
from config import DB_PATH


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.cur = self.conn.cursor()
        self._create_tables()
        self._migrate_add_image()

    def _create_tables(self):
        self.cur.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 0.0,
                stars_balance INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_spent REAL DEFAULT 0.0
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                flag TEXT DEFAULT '',
                base_price REAL NOT NULL DEFAULT 1.0,
                stock INTEGER DEFAULT 0,
                delivery_type TEXT DEFAULT 'auto',
                sort_order INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_code TEXT NOT NULL,
                data TEXT NOT NULL,
                sold INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category_code TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                total_price REAL NOT NULL,
                payment_method TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS promo_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                amount REAL NOT NULL,
                max_uses INTEGER DEFAULT 1,
                used_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS manual_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                user_id INTEGER NOT NULL,
                category_code TEXT NOT NULL,
                phone_number TEXT,
                status TEXT DEFAULT 'pending_number',
                admin_msg TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            );

            INSERT OR IGNORE INTO settings (key, value) VALUES ('discount', '0');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('markup', '0');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('stars_rate', '1.0');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('cryptobot_enabled', '1');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('stars_enabled', '1');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('yoomoney_enabled', '1');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('manual_payment_enabled', '0');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('wholesale_limit', '30');
        ''')
        self.conn.commit()

    def get_user(self, user_id):
        self.cur.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cur.fetchone()

    def register_user(self, user_id, username, first_name):
        self.cur.execute('INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)',
                         (user_id, username, first_name))
        self.conn.commit()

    def update_balance(self, user_id, amount):
        self.cur.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        self.conn.commit()

    def update_stars_balance(self, user_id, amount):
        self.cur.execute('UPDATE users SET stars_balance = stars_balance + ? WHERE user_id = ?', (amount, user_id))
        self.conn.commit()

    def add_to_total_spent(self, user_id, amount):
        self.cur.execute('UPDATE users SET total_spent = total_spent + ? WHERE user_id = ?', (amount, user_id))
        self.conn.commit()

    def get_all_categories(self):
        self.cur.execute('SELECT * FROM categories ORDER BY sort_order ASC')
        return self.cur.fetchall()

    def get_category(self, code):
        self.cur.execute('SELECT * FROM categories WHERE code = ?', (code,))
        return self.cur.fetchone()

    def add_category(self, code, name, flag, base_price):
        try:
            self.cur.execute('INSERT INTO categories (code, name, flag, base_price) VALUES (?, ?, ?, ?)',
                             (code, name, flag, base_price))
            self.conn.commit()
            return True
        except:
            return False

    def update_category_price(self, code, price):
        self.cur.execute('UPDATE categories SET base_price = ? WHERE code = ?', (price, code))
        self.conn.commit()

    def update_category_stock(self, code, stock):
        self.cur.execute('UPDATE categories SET stock = ? WHERE code = ?', (stock, code))
        self.conn.commit()

    def get_category_stock(self, code):
        self.cur.execute('SELECT COUNT(*) FROM products WHERE category_code = ? AND sold = 0', (code,))
        return self.cur.fetchone()[0]

    def add_products_bulk(self, category_code, lines):
        for line in lines:
            line = line.strip()
            if line:
                self.cur.execute('INSERT INTO products (category_code, data) VALUES (?, ?)', (category_code, line))
        self.conn.commit()
        self.cur.execute('UPDATE categories SET stock = (SELECT COUNT(*) FROM products WHERE category_code = ? AND sold = 0) WHERE code = ?', (category_code, category_code))
        self.conn.commit()

    def get_product_for_sale(self, category_code):
        self.cur.execute('SELECT id, data FROM products WHERE category_code = ? AND sold = 0 LIMIT 1', (category_code,))
        return self.cur.fetchone()

    def mark_product_sold(self, product_id):
        self.cur.execute('UPDATE products SET sold = 1 WHERE id = ?', (product_id,))
        self.conn.commit()

    def get_setting(self, key):
        self.cur.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = self.cur.fetchone()
        return row[0] if row else None

    def set_setting(self, key, value):
        self.cur.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))
        self.conn.commit()

    def get_final_price(self, base_price):
        disc = float(self.get_setting('discount') or 0)
        mark = float(self.get_setting('markup') or 0)
        price = base_price
        if disc > 0:
            price = price * (1 - disc / 100)
        if mark > 0:
            price = price * (1 + mark / 100)
        return round(price, 2)

    def create_order(self, user_id, category_code, quantity, total_price, payment_method):
        self.cur.execute('INSERT INTO orders (user_id, category_code, quantity, total_price, payment_method, status) VALUES (?, ?, ?, ?, ?, ?)',
                         (user_id, category_code, quantity, total_price, payment_method, 'pending'))
        self.conn.commit()
        return self.cur.lastrowid

    def update_order_status(self, order_id, status):
        self.cur.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
        self.conn.commit()

    def get_order(self, order_id):
        self.cur.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        return self.cur.fetchone()

    def get_user_orders(self, user_id):
        self.cur.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 20', (user_id,))
        return self.cur.fetchall()

    def get_all_users_count(self):
        self.cur.execute('SELECT COUNT(*) FROM users')
        return self.cur.fetchone()[0]

    def get_all_orders_count(self):
        self.cur.execute('SELECT COUNT(*) FROM orders')
        return self.cur.fetchone()[0]

    def get_revenue_total(self):
        self.cur.execute('SELECT COALESCE(SUM(total_price), 0) FROM orders WHERE status = ?', ('completed',))
        return self.cur.fetchone()[0]

    def get_user_by_username(self, username):
        self.cur.execute('SELECT user_id FROM users WHERE username = ?', (username.lstrip('@'),))
        row = self.cur.fetchone()
        return row[0] if row else None

    # promo
    def create_promo(self, code, amount, max_uses):
        self.cur.execute('INSERT OR IGNORE INTO promo_codes (code, amount, max_uses) VALUES (?, ?, ?)',
                         (code, amount, max_uses))
        self.conn.commit()
        return self.cur.lastrowid

    def get_promo(self, code):
        self.cur.execute('SELECT * FROM promo_codes WHERE code = ?', (code.upper(),))
        return self.cur.fetchone()

    def use_promo(self, promo_id):
        self.cur.execute('UPDATE promo_codes SET used_count = used_count + 1 WHERE id = ?', (promo_id,))
        self.conn.commit()

    def get_all_promos(self):
        self.cur.execute('SELECT * FROM promo_codes ORDER BY created_at DESC')
        return self.cur.fetchall()

    # manual orders
    def create_manual_order(self, order_id, user_id, category_code):
        self.cur.execute('INSERT INTO manual_orders (order_id, user_id, category_code) VALUES (?, ?, ?)',
                         (order_id, user_id, category_code))
        self.conn.commit()
        return self.cur.lastrowid

    def get_manual_order(self, order_id):
        self.cur.execute('SELECT * FROM manual_orders WHERE order_id = ?', (order_id,))
        return self.cur.fetchone()

    def update_manual_order(self, order_id, field, value):
        self.cur.execute(f'UPDATE manual_orders SET {field} = ? WHERE order_id = ?', (value, order_id))
        self.conn.commit()

    def get_pending_manual_orders(self):
        self.cur.execute('''SELECT mo.*, o.total_price, c.name, c.flag
                           FROM manual_orders mo
                           JOIN orders o ON mo.order_id = o.id
                           JOIN categories c ON mo.category_code = c.code
                           WHERE mo.status IN ('pending_number', 'pending_code')
                           ORDER BY o.created_at DESC''')
        return self.cur.fetchall()

    def get_manual_order_by_id(self, mo_id):
        self.cur.execute('SELECT * FROM manual_orders WHERE id = ?', (mo_id,))
        return self.cur.fetchone()

    def update_manual_order_by_id(self, mo_id, field, value):
        self.cur.execute(f'UPDATE manual_orders SET {field} = ? WHERE id = ?', (value, mo_id))
        self.conn.commit()

    def set_category_delivery_type(self, code, d_type):
        self.cur.execute('UPDATE categories SET delivery_type = ? WHERE code = ?', (d_type, code))
        self.conn.commit()

    def get_all_users(self):
        self.cur.execute('SELECT user_id, username, first_name FROM users')
        return self.cur.fetchall()

    def bulk_add_categories(self, items):
        for code, name, flag, price in items:
            try:
                self.cur.execute('INSERT OR IGNORE INTO categories (code, name, flag, base_price, sort_order) VALUES (?, ?, ?, ?, ?)',
                                 (code, name, flag, price, 0))
            except:
                pass
        self.conn.commit()

    def search_categories(self, query):
        self.cur.execute('SELECT * FROM categories WHERE name LIKE ? OR code LIKE ? ORDER BY sort_order ASC', (f'%{query}%', f'%{query}%'))
        return self.cur.fetchall()

    def close(self):
        self.conn.close()

    def _migrate_add_image(self):
        try:
            self.cur.execute('ALTER TABLE categories ADD COLUMN image TEXT DEFAULT NULL')
            self.conn.commit()
        except:
            pass

    def update_category_image(self, code, file_id):
        self.cur.execute('UPDATE categories SET image = ? WHERE code = ?', (file_id, code))
        self.conn.commit()

    def get_category_image(self, code):
        self.cur.execute('SELECT image FROM categories WHERE code = ?', (code,))
        row = self.cur.fetchone()
        return row[0] if row else None
