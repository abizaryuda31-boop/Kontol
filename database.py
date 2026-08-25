# database.py
import sqlite3
from datetime import datetime
from config import DB_FILE, PRICE_PER_EMAIL

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.c = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Users
        self.c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            birth_year INTEGER,
            join_date TEXT,
            balance INTEGER DEFAULT 0,
            total_setor INTEGER DEFAULT 0,
            total_wd INTEGER DEFAULT 0,
            referral_code TEXT,
            referred_by INTEGER DEFAULT 0,
            is_verified INTEGER DEFAULT 0
        )''')
        # Gmails
        self.c.execute('''CREATE TABLE IF NOT EXISTS gmails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            password TEXT,
            user_id INTEGER,
            status TEXT DEFAULT 'pending_admin',
            setor_date TEXT,
            verified_by INTEGER DEFAULT 0
        )''')
        # Withdrawals
        self.c.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            dana_number TEXT,
            status TEXT DEFAULT 'pending',
            request_date TEXT,
            processed_date TEXT
        )''')
        # Referrals
        self.c.execute('''CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER,
            bonus INTEGER,
            date TEXT
        )''')
        # Admin logs
        self.c.execute('''CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            message TEXT,
            date TEXT
        )''')
        self.conn.commit()

    # ---------- USER ----------
    def add_user(self, user_id, username, full_name, birth_year, referral_code, referred_by=0):
        try:
            self.c.execute(
                "INSERT INTO users (user_id, username, full_name, birth_year, join_date, referral_code, referred_by) VALUES (?,?,?,?,?,?,?)",
                (user_id, username, full_name, birth_year, datetime.now().isoformat(), referral_code, referred_by)
            )
            self.conn.commit()
            return True
        except:
            return False

    def get_user(self, user_id):
        self.c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return self.c.fetchone()

    def update_balance(self, user_id, amount):
        self.c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()

    def set_verified(self, user_id):
        self.c.execute("UPDATE users SET is_verified = 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()

    # ---------- GMAIL ----------
    def add_gmail(self, email, password, user_id):
        self.c.execute(
            "INSERT INTO gmails (email, password, user_id, setor_date) VALUES (?,?,?,?)",
            (email, password, user_id, datetime.now().isoformat())
        )
        self.conn.commit()
        return self.c.lastrowid

    def get_gmail_by_id(self, gmail_id):
        self.c.execute("SELECT * FROM gmails WHERE id = ?", (gmail_id,))
        return self.c.fetchone()

    def approve_gmail(self, gmail_id, admin_id, status='verified'):
        self.c.execute("UPDATE gmails SET status = ?, verified_by = ? WHERE id = ?", (status, admin_id, gmail_id))
        self.conn.commit()
        gmail = self.get_gmail_by_id(gmail_id)
        if gmail and status == 'verified':
            self.c.execute("UPDATE users SET balance = balance + ?, total_setor = total_setor + 1 WHERE user_id = ?",
                           (PRICE_PER_EMAIL, gmail[3]))
            self.conn.commit()
        return gmail

    def get_pending_gmails(self):
        self.c.execute("SELECT * FROM gmails WHERE status = 'pending_admin'")
        return self.c.fetchall()

    # ---------- NEW: GET & CLEAR VERIFIED GMAILS ----------
    def get_and_clear_verified_gmails(self):
        """Ambil semua Gmail status verified, lalu hapus dari database. Return list of (email, password)"""
        self.c.execute("SELECT id, email, password FROM gmails WHERE status = 'verified'")
        rows = self.c.fetchall()
        if not rows:
            return []
        # Ambil id
        ids = [row[0] for row in rows]
        # Hapus semua
        placeholders = ','.join('?' * len(ids))
        self.c.execute(f"DELETE FROM gmails WHERE id IN ({placeholders})", ids)
        self.conn.commit()
        # Return email & password
        return [(row[1], row[2]) for row in rows]

    # ---------- WITHDRAW ----------
    def add_withdraw(self, user_id, amount, dana_number):
        self.c.execute(
            "INSERT INTO withdrawals (user_id, amount, dana_number, request_date) VALUES (?,?,?,?)",
            (user_id, amount, dana_number, datetime.now().isoformat())
        )
        self.conn.commit()
        self.c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        self.c.execute("UPDATE users SET total_wd = total_wd + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
        return True

    def get_pending_withdraws(self):
        self.c.execute("SELECT * FROM withdrawals WHERE status = 'pending'")
        return self.c.fetchall()

    def process_withdraw(self, wd_id, admin_id):
        self.c.execute(
            "UPDATE withdrawals SET status = 'done', processed_date = ? WHERE id = ?",
            (datetime.now().isoformat(), wd_id)
        )
        self.conn.commit()

    # ---------- RANKING ----------
    def get_ranking(self, type='setor'):
        if type == 'setor':
            self.c.execute("SELECT username, total_setor FROM users ORDER BY total_setor DESC LIMIT 10")
        else:
            self.c.execute("SELECT username, total_wd FROM users ORDER BY total_wd DESC LIMIT 10")
        return self.c.fetchall()

    # ---------- REFERRAL ----------
    def count_referrals(self, user_id):
        self.c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
        return self.c.fetchone()[0]

    # ---------- STATS ----------
    def get_stats(self):
        self.c.execute("SELECT COUNT(*) FROM users")
        total_user = self.c.fetchone()[0]
        self.c.execute("SELECT SUM(total_setor) FROM users")
        total_setor = self.c.fetchone()[0] or 0
        self.c.execute("SELECT SUM(balance) FROM users")
        total_balance = self.c.fetchone()[0] or 0
        return total_user, total_setor, total_balance