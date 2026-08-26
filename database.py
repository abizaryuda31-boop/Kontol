# database.py
import sqlite3

class Database:
    def __init__(self, db_name="bot_database.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.c = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Tabel Users
        self.c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            generated_prefix TEXT,
            referral_code TEXT UNIQUE,
            referred_by INTEGER DEFAULT 0,
            balance INTEGER DEFAULT 0,
            total_setor INTEGER DEFAULT 0,
            total_wd INTEGER DEFAULT 0,
            joined_date TEXT,
            is_verified INTEGER DEFAULT 0
        )''')

        # Tabel Gmails
        self.c.execute('''CREATE TABLE IF NOT EXISTS gmails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            password TEXT,
            user_id INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )''')

        # Tabel Withdraws
        self.c.execute('''CREATE TABLE IF NOT EXISTS withdraws (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            dana_number TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )''')

        # Tabel Referrals
        self.c.execute('''CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER,
            bonus INTEGER,
            date TEXT
        )''')

        # Tabel Settings (Untuk Maintenance Status)
        self.c.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        
        # Default status maintenance: '0' (BUKA)
        self.c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance', '0')")
        self.conn.commit()

    # --- SETTINGS FUNCTIONS ---
    def set_maintenance(self, status):
        # status: '1' untuk TUTUP, '0' untuk BUKA
        self.c.execute("UPDATE settings SET value = ? WHERE key = 'maintenance'", (str(status),))
        self.conn.commit()

    def is_maintenance(self):
        self.c.execute("SELECT value FROM settings WHERE key = 'maintenance'")
        row = self.c.fetchone()
        return row[0] == '1' if row else False

    # --- USER FUNCTIONS ---
    def get_user(self, user_id):
        self.c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return self.c.fetchone()

    def add_user(self, user_id, username, full_name, generated_prefix, referral_code, referred_by):
        from datetime import datetime
        joined_date = datetime.now().isoformat()
        self.c.execute('''INSERT OR IGNORE INTO users 
            (user_id, username, full_name, generated_prefix, referral_code, referred_by, joined_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)''', 
            (user_id, username, full_name, generated_prefix, referral_code, referred_by, joined_date))
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

    def count_referrals(self, user_id):
        self.c.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
        return self.c.fetchone()[0]

    # --- GMAIL FUNCTIONS ---
    def add_gmail(self, email, password, user_id):
        from datetime import datetime
        created_at = datetime.now().isoformat()
        self.c.execute("INSERT INTO gmails (email, password, user_id, created_at) VALUES (?, ?, ?, ?)",
                       (email, password, user_id, created_at))
        self.conn.commit()
        return self.c.lastrowid

    def approve_gmail(self, gmail_id, admin_id, status='verified'):
        self.c.execute("SELECT * FROM gmails WHERE id = ?", (gmail_id,))
        gmail = self.c.fetchone()
        if not gmail or gmail[4] != 'pending':
            return None
        
        self.c.execute("UPDATE gmails SET status = ? WHERE id = ?", (status, gmail_id))
        if status == 'verified':
            user_id = gmail[3]
            from config import PRICE_PER_EMAIL
            self.c.execute("UPDATE users SET balance = balance + ?, total_setor = total_setor + 1 WHERE user_id = ?", (PRICE_PER_EMAIL, user_id))
        self.conn.commit()
        return gmail

    def get_pending_gmails(self):
        self.c.execute("SELECT * FROM gmails WHERE status = 'pending'")
        return self.c.fetchall()

    def get_and_clear_verified_gmails(self):
        self.c.execute("SELECT email, password FROM gmails WHERE status = 'verified'")
        rows = self.c.fetchall()
        self.c.execute("DELETE FROM gmails WHERE status = 'verified'")
        self.conn.commit()
        return rows

    # --- WITHDRAW FUNCTIONS ---
    def add_withdraw(self, user_id, amount, dana_number):
        from datetime import datetime
        created_at = datetime.now().isoformat()
        self.c.execute("INSERT INTO withdraws (user_id, amount, dana_number, created_at) VALUES (?, ?, ?, ?)",
                       (user_id, amount, dana_number, created_at))
        self.c.execute("UPDATE users SET balance = balance - ?, total_wd = total_wd + ? WHERE user_id = ?", (amount, amount, user_id))
        self.conn.commit()

    def get_pending_withdraws(self):
        self.c.execute("SELECT * FROM withdraws WHERE status = 'pending'")
        return self.c.fetchall()

    # --- STATS & RANKING ---
    def get_stats(self):
        self.c.execute("SELECT COUNT(*) FROM users")
        tot_users = self.c.fetchone()[0]
        self.c.execute("SELECT COUNT(*) FROM gmails WHERE status = 'verified'")
        tot_setor = self.c.fetchone()[0]
        self.c.execute("SELECT SUM(balance) FROM users")
        tot_bal = self.c.fetchone()[0] or 0
        return tot_users, tot_setor, tot_bal

    def get_ranking(self, tipe='setor'):
        if tipe == 'setor':
            self.c.execute("SELECT username, total_setor FROM users ORDER BY total_setor DESC LIMIT 10")
        else:
            self.c.execute("SELECT username, total_wd FROM users ORDER BY total_wd DESC LIMIT 10")
        return self.c.fetchall()
