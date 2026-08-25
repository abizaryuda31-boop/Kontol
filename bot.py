# bot.py
import telebot
from telebot import types
from config import *
from database import Database
from utils import *
import time
from datetime import datetime
import io
import random
import string

bot = telebot.TeleBot(BOT_TOKEN)
db = Database()
BOT_USERNAME = bot.get_me().username

# ========== FUNGSI GENERATE PREFIX ==========
def generate_random_prefix(length=10):
    """Buat prefix email acak (huruf + angka)"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

# ========== START ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Tidak ada"
    full_name = message.from_user.full_name or "Tidak ada"

    user = db.get_user(user_id)
    if not user:
        ref_code = None
        referrer_id = 0
        if len(message.text.split()) > 1:
            ref_code = message.text.split()[1]
            db.c.execute("SELECT user_id FROM users WHERE referral_code = ?", (ref_code,))
            row = db.c.fetchone()
            if row:
                referrer_id = row[0]
        db.add_user(user_id, username, full_name, 0, generate_referral_code(), referrer_id)
        if referrer_id:
            db.update_balance(referrer_id, REFERRAL_BONUS)
            db.c.execute(
                "INSERT INTO referrals (referrer_id, referred_id, bonus, date) VALUES (?,?,?,?)",
                (referrer_id, user_id, REFERRAL_BONUS, datetime.now().isoformat())
            )
            db.conn.commit()
        user = db.get_user(user_id)

    if user[10] == 1:  # is_verified
        send_main_menu(message.chat.id, user)
    else:
        text = f"""
📢 *WELCOME TO JOB GMAIL PRO*

Sebelum menggunakan bot ini, kamu **wajib join channel** kami terlebih dahulu.

📌 *Channel:* {CHANNEL_USERNAME}

Klik tombol di bawah untuk join, lalu klik **Verifikasi**.
        """
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_join = types.InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")
        btn_verify = types.InlineKeyboardButton("✅ VERIFIKASI", callback_data="verify")
        markup.add(btn_join, btn_verify)
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

# ========== VERIFIKASI ==========
@bot.callback_query_handler(func=lambda call: call.data == 'verify')
def verify(call):
    user_id = call.from_user.id
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            db.set_verified(user_id)
            user = db.get_user(user_id)
            send_main_menu(call.message.chat.id, user)
            bot.answer_callback_query(call.id, "✅ Verifikasi Berhasil! Selamat bergabung.")
        else:
            bot.answer_callback_query(call.id, "❌ Kamu belum join channel! Join dulu ya.", show_alert=True)
    except:
        bot.answer_callback_query(call.id, "❌ Gagal verifikasi. Coba lagi.", show_alert=True)

# ========== MENU UTAMA (DENGAN FOTO) ==========
def send_main_menu(chat_id, user):
    caption = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━
    JOB GMAIL PRO
━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 *User:* {user[2] if user[2] else user[1]}
🆔 *ID:* {user[0]}
💰 *Balance:* {format_rupiah(user[6])}
📦 *Total Setor:* {user[7]} akun
💸 *Total WD:* {format_rupiah(user[8])}
🔗 *Kode Referral:* `{user[9]}`
━━━━━━━━━━━━━━━━━━━━━━━━━━━
*Pilih menu di bawah:*
    """
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("📤 SETOR GMAIL", callback_data="setor")
    btn2 = types.InlineKeyboardButton("💰 BALANCE", callback_data="balance")
    btn3 = types.InlineKeyboardButton("📜 RULES", callback_data="rules")
    btn4 = types.InlineKeyboardButton("🔗 REFERRAL", callback_data="referral")
    btn5 = types.InlineKeyboardButton("🏆 PERINGKAT", callback_data="ranking")
    btn6 = types.InlineKeyboardButton("💸 WITHDRAW", callback_data="withdraw")
    btn7 = types.InlineKeyboardButton("🎲 GENERATE NAMA", callback_data="generate")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7)
    bot.send_photo(chat_id, photo=PHOTO_URL, caption=caption, reply_markup=markup, parse_mode='Markdown')

# ========== MENU TEKS (NAVIGASI) ==========
def show_text_menu(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("📤 SETOR GMAIL", callback_data="setor")
    btn2 = types.InlineKeyboardButton("💰 BALANCE", callback_data="balance")
    btn3 = types.InlineKeyboardButton("📜 RULES", callback_data="rules")
    btn4 = types.InlineKeyboardButton("🔗 REFERRAL", callback_data="referral")
    btn5 = types.InlineKeyboardButton("🏆 PERINGKAT", callback_data="ranking")
    btn6 = types.InlineKeyboardButton("💸 WITHDRAW", callback_data="withdraw")
    btn7 = types.InlineKeyboardButton("🎲 GENERATE NAMA", callback_data="generate")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7)
    bot.send_message(chat_id, "📌 *Menu Utama:*", reply_markup=markup, parse_mode='Markdown')

# ========== GENERATE NAMA ==========
@bot.callback_query_handler(func=lambda call: call.data == 'generate')
def generate_name(call):
    user_id = call.from_user.id
    prefix = generate_random_prefix(10)  # panjang 10 karakter
    db.set_generated_prefix(user_id, prefix)
    bot.answer_callback_query(call.id, f"✅ Nama berhasil di-generate: {prefix}")
    bot.send_message(
        call.message.chat.id,
        f"🎲 *NAMA GMAIL HASIL GENERATE:*\n`{prefix}`\n\n"
        "📌 *Langkah selanjutnya:*\n"
        "1. Buat Gmail baru dengan nama **persis** seperti di atas (contoh: `{prefix}@gmail.com`).\n"
        "2. Gunakan password wajib: `{REQUIRED_PASSWORD}`\n"
        "3. Setelah selesai, kirim Gmail melalui menu **SETOR GMAIL**.\n\n"
        "⚠️ Nama ini hanya berlaku untuk 1 kali setor. Setelah setor, kamu perlu generate ulang untuk akun berikutnya.",
        parse_mode='Markdown'
    )

# ========== SETOR GMAIL ==========
@bot.callback_query_handler(func=lambda call: call.data == 'setor')
def setor_gmail(call):
    user_id = call.from_user.id
    generated = db.get_generated_prefix(user_id)
    if not generated:
        bot.send_message(
            call.message.chat.id,
            "❌ Kamu belum generate nama! Klik **🎲 GENERATE NAMA** dulu.",
            parse_mode='Markdown'
        )
        return
    msg = bot.send_message(
        call.message.chat.id,
        f"📧 *FORMAT SETOR GMAIL*\n\n"
        f"Kirim email dan password dengan format:\n`email|password`\n\n"
        f"Contoh: `{generated}@gmail.com|sgsg1122`\n\n"
        f"⚠️ Nama email WAJIB sesuai dengan yang digenerate: `{generated}`\n"
        f"Password WAJIB: `{REQUIRED_PASSWORD}`",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, proses_setor)

def proses_setor(message):
    user_id = message.from_user.id
    try:
        email, password = message.text.split('|')
        
        # 1. Validasi format email
        if not validate_email(email):
            bot.reply_to(message, "❌ Format email tidak valid. Coba lagi.")
            return

        # 2. Ambil prefix dari email (bagian sebelum @)
        email_prefix = email.split('@')[0]
        generated_prefix = db.get_generated_prefix(user_id)
        
        # 3. Validasi prefix harus sama dengan yang digenerate
        if not generated_prefix:
            bot.reply_to(
                message,
                "❌ Kamu belum generate nama! Klik **🎲 GENERATE NAMA** di menu.",
                parse_mode='Markdown'
            )
            return
        if email_prefix != generated_prefix:
            bot.reply_to(
                message,
                f"❌ Nama email tidak sesuai dengan hasil generate!\n"
                f"Nama yang di-generate: `{generated_prefix}`\n"
                f"Kamu kirim: `{email_prefix}`\n\n"
                "Silakan generate ulang atau perbaiki nama email.",
                parse_mode='Markdown'
            )
            return

        # 4. Validasi password harus sgsg1122
        if password != REQUIRED_PASSWORD:
            bot.reply_to(
                message,
                f"❌ Password wajib `{REQUIRED_PASSWORD}` (huruf kecil semua).\n"
                "Gmail ditolak. Pastikan password sesuai aturan.",
                parse_mode='Markdown'
            )
            return

        # 5. Cek keaktifan Gmail via IMAP
        if not check_gmail_valid(email, password):
            bot.reply_to(
                message,
                "❌ Gmail tidak aktif / login gagal.\n"
                "Pastikan Gmail masih Live dan password benar.\n"
                "Cek di https://en.gmailcheck.com/",
                parse_mode='Markdown'
            )
            return

        # 6. Simpan ke database (status pending_admin)
        gmail_id = db.add_gmail(email, password, user_id)
        
        # 7. Hapus generated prefix agar harus generate ulang untuk setoran berikutnya
        db.clear_generated_prefix(user_id)

        # Notifikasi admin
        admin_text = f"""
📥 *GMAIL BARU - PENDING*
👤 @{message.from_user.username or message.from_user.id}
📧 {email}
🔑 {password}
🆔 User ID: {user_id}
📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}
✅ Status Gmail: LIVE (terverifikasi IMAP)
✅ Nama sesuai generate
        """
        markup = types.InlineKeyboardMarkup()
        btn_approve = types.InlineKeyboardButton("✅ TERIMA", callback_data=f"approve_gmail_{gmail_id}")
        btn_reject = types.InlineKeyboardButton("❌ TOLAK", callback_data=f"reject_gmail_{gmail_id}")
        markup.add(btn_approve, btn_reject)

        for admin in ADMIN_ID:
            try:
                bot.send_message(admin, admin_text, reply_markup=markup, parse_mode='Markdown')
            except:
                pass

        bot.reply_to(
            message,
            f"✅ *GMAIL TERKIRIM!*\n📧 {email}\n⏳ Menunggu verifikasi admin. Kamu akan mendapat notifikasi setelah disetujui.",
            parse_mode='Markdown'
        )
        show_text_menu(message.chat.id)
    except:
        bot.reply_to(message, "❌ Format salah! Gunakan `email|password`", parse_mode='Markdown')

# ========== ADMIN APPROVE / REJECT ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_gmail_') or call.data.startswith('reject_gmail_'))
def admin_approve_gmail(call):
    if call.from_user.id not in ADMIN_ID:
        bot.answer_callback_query(call.id, "Akses ditolak.", show_alert=True)
        return

    parts = call.data.split('_')
    action = parts[0]
    gmail_id = int(parts[2])

    gmail = db.approve_gmail(gmail_id, call.from_user.id, 'verified' if action == 'approve' else 'rejected')
    if not gmail:
        bot.answer_callback_query(call.id, "Gmail tidak ditemukan.", show_alert=True)
        return

    user_id = gmail[3]
    if action == 'approve':
        user = db.get_user(user_id)
        msg = f"✅ *GMAIL DITERIMA!*\n📧 {gmail[1]}\n💰 +{format_rupiah(PRICE_PER_EMAIL)}\n📦 Sisa balance: {format_rupiah(user[6])}"
        bot.answer_callback_query(call.id, f"✅ Gmail diterima!", show_alert=True)
    else:
        msg = f"❌ *GMAIL DITOLAK*\n📧 {gmail[1]}\nAlasan: tidak valid / tidak sesuai ketentuan."
        bot.answer_callback_query(call.id, f"❌ Gmail ditolak.", show_alert=True)

    try:
        bot.send_message(user_id, msg, parse_mode='Markdown')
    except:
        pass

    bot.delete_message(call.message.chat.id, call.message.message_id)

# ========== BALANCE ==========
@bot.callback_query_handler(func=lambda call: call.data == 'balance')
def balance(call):
    user_id = call.from_user.id
    user = db.get_user(user_id)
    if user:
        text = f"""
💰 *BALANCE KAMU*
━━━━━━━━━━━━━━━━━━
💵 Saldo: {format_rupiah(user[6])}
📦 Total Setor: {user[7]} akun
💸 Total WD: {format_rupiah(user[8])}
━━━━━━━━━━━━━━━━━━
*Minimal WD: {format_rupiah(MIN_WITHDRAW)}*
        """
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
    else:
        bot.send_message(call.message.chat.id, "❌ Data tidak ditemukan. /start dulu.")

# ========== RULES ==========
@bot.callback_query_handler(func=lambda call: call.data == 'rules')
def rules(call):
    text = f"""
📜 *RULES STORAN GMAIL - JOB GMAIL PRO*
━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ *Gmail harus Fresh (baru dibuat)*

2️⃣ *Nama Gmail WAJIB sesuai dengan hasil GENERATE dari bot.*
   - Klik tombol **🎲 GENERATE NAMA** di menu.
   - Buat Gmail dengan nama persis seperti yang diberikan.
   - Tidak boleh mengubah, menambah, atau mengurangi karakter.

3️⃣ *Tanggal lahir akun Gmail wajib 18 tahun ke atas.*

4️⃣ *Password Gmail wajib:* `{REQUIRED_PASSWORD}` (huruf kecil semua).

5️⃣ *Akun tidak boleh ditautkan dengan nomor/email pemulihan.*

6️⃣ *Cek status Gmail di https://en.gmailcheck.com/* sebelum setor.

7️⃣ *Hanya kirim Gmail dengan status Live/Aktif.*

━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 *Catatan:*
• Setiap kali setor, kamu WAJIB generate nama baru.
• Gmail yang tidak sesuai dengan hasil generate akan ditolak.
• Admin berhak menolak jika ada indikasi pelanggaran.
━━━━━━━━━━━━━━━━━━━━━━━━━━━
*© 2026 JOB GMAIL PRO*
    """
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

# ========== REFERRAL ==========
@bot.callback_query_handler(func=lambda call: call.data == 'referral')
def referral(call):
    user_id = call.from_user.id
    user = db.get_user(user_id)
    if user:
        link = f"https://t.me/{BOT_USERNAME}?start={user[9]}"
        total_ref = db.count_referrals(user_id)
        text = f"""
🔗 *REFERRAL KAMU*
━━━━━━━━━━━━━━━━━━
📌 Kode: `{user[9]}`
👥 Total Referral: {total_ref} orang
💰 Bonus/Referral: {format_rupiah(REFERRAL_BONUS)}

📤 *Bagikan Link Ini:*
{link}
━━━━━━━━━━━━━━━━━━
*Setiap orang daftar pakai link ini, kamu dapat bonus!*
        """
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
    else:
        bot.send_message(call.message.chat.id, "❌ Data tidak ditemukan. /start dulu.")

# ========== RANKING ==========
@bot.callback_query_handler(func=lambda call: call.data == 'ranking')
def ranking(call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🏆 SETOR TERBANYAK", callback_data="rank_setor")
    btn2 = types.InlineKeyboardButton("💰 WD TERBANYAK", callback_data="rank_wd")
    markup.add(btn1, btn2)
    bot.send_message(call.message.chat.id, "📊 *Pilih Kategori Peringkat:*", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('rank_'))
def show_ranking(call):
    tipe = call.data.split('_')[1]
    data = db.get_ranking(tipe)
    text = f"🏆 *PERINGKAT {'SETOR' if tipe == 'setor' else 'WD'}* \n━━━━━━━━━━━━━━━━━━\n"
    if data:
        for i, row in enumerate(data, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            value = row[1] if tipe == 'setor' else format_rupiah(row[1])
            text += f"{medal} @{row[0] or 'User'} — {value}\n"
    else:
        text += "Belum ada data, boss!"
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

# ========== WITHDRAW ==========
@bot.callback_query_handler(func=lambda call: call.data == 'withdraw')
def withdraw(call):
    user_id = call.from_user.id
    user = db.get_user(user_id)
    if not user:
        bot.send_message(call.message.chat.id, "❌ Data tidak ditemukan. /start dulu.")
        return
    if user[6] < MIN_WITHDRAW:
        bot.send_message(
            call.message.chat.id,
            f"❌ Saldo kamu {format_rupiah(user[6])}, minimal WD {format_rupiah(MIN_WITHDRAW)}.",
            parse_mode='Markdown'
        )
        return
    msg = bot.send_message(
        call.message.chat.id,
        f"💸 *FORMAT WITHDRAW*\n\nKirim nomor DANA dan jumlah:\n`nomor|jumlah`\n\nContoh: `08123456789|10000`\nSaldo: {format_rupiah(user[6])}",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, proses_withdraw)

def proses_withdraw(message):
    user_id = message.from_user.id
    try:
        dana_number, amount_str = message.text.split('|')
        amount = int(amount_str)
        user = db.get_user(user_id)

        if not is_valid_dana(dana_number):
            bot.reply_to(message, "❌ Nomor DANA tidak valid (harus 08xxx).")
            return
        if amount < MIN_WITHDRAW:
            bot.reply_to(message, f"❌ Minimal WD {format_rupiah(MIN_WITHDRAW)}.")
            return
        if amount > user[6]:
            bot.reply_to(message, f"❌ Saldo tidak cukup. Saldo: {format_rupiah(user[6])}.")
            return

        db.add_withdraw(user_id, amount, dana_number)
        user = db.get_user(user_id)

        admin_text = f"""
💸 *WD REQUEST!*
👤 @{message.from_user.username or message.from_user.id}
🆔 {user_id}
📱 {dana_number}
💰 {format_rupiah(amount)}
📦 Sisa Saldo: {format_rupiah(user[6])}
⏳ Status: PENDING
        """
        for admin in ADMIN_ID:
            try:
                bot.send_message(admin, admin_text, parse_mode='Markdown')
            except:
                pass

        bot.reply_to(
            message,
            f"✅ *WD BERHASIL DIREQUEST!*\n💸 {format_rupiah(amount)}\n📱 {dana_number}\n⏳ Tunggu admin transfer 1x24 jam.",
            parse_mode='Markdown'
        )
        show_text_menu(message.chat.id)
    except:
        bot.reply_to(message, "❌ Format salah! Gunakan `nomor|jumlah`", parse_mode='Markdown')

# ========== ADMIN PANEL ==========
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_ID:
        bot.reply_to(message, "❌ Anda tidak memiliki akses.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("📥 GMAIL PENDING", callback_data="admin_gmail")
    btn2 = types.InlineKeyboardButton("💸 WD PENDING", callback_data="admin_wd")
    btn3 = types.InlineKeyboardButton("📊 STATISTIK", callback_data="admin_stats")
    btn4 = types.InlineKeyboardButton("📥 DOWNLOAD AKUN", callback_data="admin_download")
    markup.add(btn1, btn2, btn3, btn4)
    bot.send_message(message.chat.id, "🔧 *ADMIN PANEL*", reply_markup=markup, parse_mode='Markdown')

# ========== ADMIN DOWNLOAD ==========
@bot.callback_query_handler(func=lambda call: call.data == 'admin_download')
def admin_download(call):
    if call.from_user.id not in ADMIN_ID:
        bot.answer_callback_query(call.id, "Akses ditolak.", show_alert=True)
        return
    accounts = db.get_and_clear_verified_gmails()
    if not accounts:
        bot.answer_callback_query(call.id, "Tidak ada akun yang tersedia untuk diunduh.", show_alert=True)
        return
    content = "\n".join([f"{email}:{pwd}" for email, pwd in accounts])
    file_obj = io.BytesIO(content.encode('utf-8'))
    file_obj.name = "akun_gmail.txt"
    try:
        bot.send_document(
            call.message.chat.id,
            file_obj,
            caption=f"✅ {len(accounts)} akun berhasil diunduh.\nAkun-akun ini sudah dihapus dari database."
        )
        bot.answer_callback_query(call.id, f"✅ {len(accounts)} akun diunduh!")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Gagal mengunduh: {str(e)}", show_alert=True)

# ========== ADMIN LAINNYA ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_actions(call):
    if call.from_user.id not in ADMIN_ID:
        bot.answer_callback_query(call.id, "Akses ditolak.", show_alert=True)
        return

    action = call.data.split('_')[1]

    if action == 'gmail':
        gmails = db.get_pending_gmails()
        if gmails:
            for g in gmails:
                text = f"📧 {g[1]}\n🔑 {g[2]}\n👤 User ID: {g[3]}\n📅 {g[5]}"
                bot.send_message(call.message.chat.id, text)
        else:
            bot.send_message(call.message.chat.id, "✅ Tidak ada Gmail pending.")

    elif action == 'wd':
        wds = db.get_pending_withdraws()
        if wds:
            for w in wds:
                markup = types.InlineKeyboardMarkup()
                btn_process = types.InlineKeyboardButton("✅ PROSES", callback_data=f"process_wd_{w[0]}")
                btn_cancel = types.InlineKeyboardButton("❌ BATAL", callback_data=f"cancel_wd_{w[0]}")
                markup.add(btn_process, btn_cancel)
                bot.send_message(
                    call.message.chat.id,
                    f"💸 WD ID: {w[0]}\n👤 User: {w[1]}\n💰 {format_rupiah(w[2])}\n📱 {w[3]}\n📅 {w[5]}",
                    reply_markup=markup
                )
        else:
            bot.send_message(call.message.chat.id, "✅ Tidak ada WD pending.")

    elif action == 'stats':
        total_user, total_setor, total_balance = db.get_stats()
        text = f"""
📊 *STATISTIK BOT*
━━━━━━━━━━━━━━━━━━
👥 Total User: {total_user}
📦 Total Gmail Setor: {total_setor}
💰 Total Balance: {format_rupiah(total_balance)}
━━━━━━━━━━━━━━━━━━
        """
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

# ========== ADMIN PROSES WD ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('process_wd_'))
def process_wd(call):
    if call.from_user.id not in ADMIN_ID:
        bot.answer_callback_query(call.id, "Akses ditolak.", show_alert=True)
        return
    wd_id = int(call.data.split('_')[2])
    db.process_withdraw(wd_id, call.from_user.id)
    bot.answer_callback_query(call.id, "✅ WD diproses!", show_alert=True)
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_wd_'))
def cancel_wd(call):
    if call.from_user.id not in ADMIN_ID:
        bot.answer_callback_query(call.id, "Akses ditolak.", show_alert=True)
        return
    wd_id = int(call.data.split('_')[2])
    db.c.execute("UPDATE withdrawals SET status = 'cancelled' WHERE id = ?", (wd_id,))
    db.conn.commit()
    db.c.execute("SELECT user_id, amount FROM withdrawals WHERE id = ?", (wd_id,))
    row = db.c.fetchone()
    if row:
        db.update_balance(row[0], row[1])
    bot.answer_callback_query(call.id, "❌ WD dibatalkan, saldo dikembalikan.", show_alert=True)
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ========== FALLBACK ==========
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "Gunakan tombol menu atau /start untuk memulai.")

# ========== MAIN ==========
if __name__ == '__main__':
    print("🚀 JOB GMAIL PRO BOT (DENGAN GENERATE) STARTED...")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)