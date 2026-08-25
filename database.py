# database.py
import sqlite3

class Database:
    def __init__(self, db_file="bot_database.db"):
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.c = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Tabel Users
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                generated_prefix TEXT,
                referral_code TEXT UNIQUE,
                referrer_id INTEGER DEFAULT 0,
                balance INTEGER DEFAULT 0,
                total_setor INTEGER DEFAULT 0,
                total_wd INTEGER DEFAULT 0,
                is_verified INTEGER DEFAULT 0
            )
        ''')
        # Tabel Gmails
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS gmails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                password TEXT,
                user_id INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            )
        ''')
        # Tabel Withdrawals
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                dana_number TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            )
        ''')
        # Tabel Referrals
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                bonus INTEGER,
                date TEXT
            )
        ''')
        self.conn.commit()

    def get_user(self, user_id):
        self.c.execute("SELECT user_id, username, full_name, generated_prefix, referral_code, referrer_id, balance, total_setor, total_wd, referral_code, is_verified FROM users WHERE user_id = ?", (user_id,))
        return self.c.fetchone()

    def add_user(self, user_id, username, full_name, generated_prefix, referral_code, referrer_id=0):
        self.c.execute('''
            INSERT OR IGNORE INTO users (user_id, username, full_name, generated_prefix, referral_code, referrer_id, balance, total_setor, total_wd, is_verified)
            VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, 0)
        ''', (user_id, username, full_name, generated_prefix, referral_code, referrer_id))
        self.conn.commit()

    def set_verified(self, user_id):
        self.c.execute("UPDATE users SET is_verified = 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def set_generated_prefix(self, user_id, prefix):
        self.c.execute("UPDATE users SET generated_prefix = ? WHERE user_id = ?", (prefix, user_id))
        self.conn.commit()

    def get_generated_prefix(self, user_id):
        self.c.execute("SELECT generated_prefix FROM users WHERE user_id = ?", (user_id,))
        row = self.c.fetchone()
        return row[0] if row else None

    def clear_generated_prefix(self, user_id):
        self.c.execute("UPDATE users SET generated_prefix = NULL WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def update_balance(self, user_id, amount):
        self.c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()

    def add_gmail(self, email, password, user_id):
        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.c.execute("INSERT INTO gmails (email, password, user_id, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
                       (email, password, user_id, now))
        self.conn.commit()
        return self.c.lastrowid

    def approve_gmail(self, gmail_id, admin_id, status):
        self.c.execute("SELECT id, email, password, user_id FROM gmails WHERE id = ?", (gmail_id,))
        gmail = self.c.fetchone()
        if gmail:
            self.c.execute("UPDATE gmails SET status = ? WHERE id = ?", (status, gmail_id))
            if status == 'verified':
                from config import PRICE_PER_EMAIL
                user_id = gmail[3]
                self.c.execute("UPDATE users SET balance = balance + ?, total_setor = total_setor + 1 WHERE user_id = ?", (PRICE_PER_EMAIL, user_id))
            self.conn.commit()
        return gmail

    def add_withdraw(self, user_id, amount, dana_number):
        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.c.execute("INSERT INTO withdrawals (user_id, amount, dana_number, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
                       (user_id, amount, dana_number, now))
        self.c.execute("UPDATE users SET balance = balance - ?, total_wd = total_wd + ? WHERE user_id = ?", (amount, amount, user_id))
        self.conn.commit()

    def process_withdraw(self, wd_id, admin_id):
        self.c.execute("UPDATE withdrawals SET status = 'success' WHERE id = ?", (wd_id,))
        self.conn.commit()

    def count_referrals(self, user_id):
        self.c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
        row = self.c.fetchone()
        return row[0] if row else 0

    def get_ranking(self, tipe):
        if tipe == 'setor':
            self.c.execute("SELECT username, total_setor FROM users ORDER BY total_setor DESC LIMIT 10")
        else:
            self.c.execute("SELECT username, total_wd FROM users ORDER BY total_wd DESC LIMIT 10")
        return self.c.fetchall()

    def get_pending_gmails(self):
        self.c.execute("SELECT id, email, password, user_id, status, created_at FROM gmails WHERE status = 'pending'")
        return self.c.fetchall()

    def get_pending_withdraws(self):
        self.c.execute("SELECT id, user_id, amount, dana_number FROM withdrawals WHERE status = 'pending'")
        return self.c.fetchall()

    def get_stats(self):
        self.c.execute("SELECT COUNT(*), SUM(total_setor), SUM(balance) FROM users")
        row = self.c.fetchone()
        return row[0] or 0, row[1] or 0, row[2] or 0

    def get_and_clear_verified_gmails(self):
        self.c.execute("SELECT email, password FROM gmails WHERE status = 'verified'")
        rows = self.c.fetchall()
        if rows:
            self.c.execute("UPDATE gmails SET status = 'downloaded' WHERE status = 'verified'")
            self.conn.commit()
        return rows
