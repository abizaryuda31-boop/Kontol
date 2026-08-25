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
<b>📢 WELCOME TO JOB GMAIL PRO</b>

Sebelum menggunakan bot ini, kamu <b>wajib join channel</b> kami terlebih dahulu.

📌 <b>Channel:</b> {CHANNEL_USERNAME}

Klik tombol di bawah untuk join, lalu klik <b>Verifikasi</b>.
        """
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_join = types.InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")
        btn_verify = types.InlineKeyboardButton("✅ VERIFIKASI", callback_data="verify")
        markup.add(btn_join, btn_verify)
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='HTML')

# ========== VERIFIKASI JOIN (PAKAI USERNAME) ==========
@bot.callback_query_handler(func=lambda call: call.data == 'verify')
def verify(call):
    user_id = call.from_user.id
    try:
        # Coba ambil member dengan username
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            db.set_verified(user_id)
            user = db.get_user(user_id)
            send_main_menu(call.message.chat.id, user)
            bot.answer_callback_query(call.id, "✅ Verifikasi Berhasil! Selamat bergabung.")
        else:
            bot.answer_callback_query(call.id, f"❌ Status: {member.status}. Kamu belum join channel!", show_alert=True)
    except Exception as e:
        error_msg = str(e)
        # Kirim error detail ke user
        bot.answer_callback_query(call.id, f"❌ Error: {error_msg[:100]}", show_alert=True)
        # Kirim juga ke admin
        for admin in ADMIN_ID:
            try:
                bot.send_message(admin, f"⚠️ Error verifikasi:\n{error_msg}")
            except:
                pass

# ========== MENU UTAMA (DENGAN FOTO) ==========
def send_main_menu(chat_id, user):
    caption = f"""
<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>
    <b>JOB GMAIL PRO</b>
<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>
👤 <b>User:</b> {user[2] if user[2] else user[1]}
🆔 <b>ID:</b> {user[0]}
💰 <b>Balance:</b> {format_rupiah(user[6])}
📦 <b>Total Setor:</b> {user[7]} akun
💸 <b>Total WD:</b> {format_rupiah(user[8])}
🔗 <b>Kode Referral:</b> <code>{user[9]}</code>
<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>
<i>Pilih menu di bawah:</i>
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

    bot.send_photo(chat_id, photo=PHOTO_URL, caption=caption, reply_markup=markup, parse_mode='HTML')

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
    bot.send_message(chat_id, "<b>📌 Menu Utama:</b>", reply_markup=markup, parse_mode='HTML')

# ========== GENERATE NAMA ==========
@bot.callback_query_handler(func=lambda call: call.data == 'generate')
def generate_name(call):
    user_id = call.from_user.id
    prefix = generate_random_prefix(10)
    db.set_generated_prefix(user_id, prefix)
    bot.answer_callback_query(call.id, f"✅ Nama berhasil di-generate: {prefix}")
    bot.send_message(
        call.message.chat.id,
        f"""
<b>🎲 NAMA GMAIL HASIL GENERATE:</b>
<code>{prefix}</code>

<b>📌 Langkah selanjutnya:</b>
1. Buat Gmail baru dengan nama <b>persis</b> seperti di atas (contoh: <code>{prefix}@gmail.com</code>).
2. Gunakan password wajib: <code>{REQUIRED_PASSWORD}</code>
3. Setelah selesai, kirim Gmail melalui menu <b>SETOR GMAIL</b>.

⚠️ Nama ini hanya berlaku untuk 1 kali setor. Setelah setor, kamu perlu generate ulang untuk akun berikutnya.
        """,
        parse_mode='HTML'
    )

# ========== SETOR GMAIL ==========
@bot.callback_query_handler(func=lambda call: call.data == 'setor')
def setor_gmail(call):
    user_id = call.from_user.id
    generated = db.get_generated_prefix(user_id)
    if not generated:
        bot.send_message(
            call.message.chat.id,
            "❌ Kamu belum generate nama! Klik <b>🎲 GENERATE NAMA</b> dulu.",
            parse_mode='HTML'
        )
        return
    msg = bot.send_message(
        call.message.chat.id,
        f"""
<b>📧 FORMAT SETOR GMAIL</b>

Kirim email dan password dengan format:
<code>email|password</code>

Contoh: <code>{generated}@gmail.com|sgsg1122</code>

⚠️ Nama email WAJIB sesuai dengan yang digenerate: <code>{generated}</code>
Password WAJIB: <code>{REQUIRED_PASSWORD}</code>
        """,
        parse_mode='HTML'
    )
    bot.register_next_step_handler(msg, proses_setor)

def proses_setor(message):
    user_id = message.from_user.id
    try:
        email, password = message.text.split('|')

        if not validate_email(email):
            bot.reply_to(message, "❌ Format email tidak valid. Coba lagi.", parse_mode='HTML')
            return

        email_prefix = email.split('@')[0]
        generated_prefix = db.get_generated_prefix(user_id)

        if not generated_prefix:
            bot.reply_to(
                message,
                "❌ Kamu belum generate nama! Klik <b>🎲 GENERATE NAMA</b> di menu.",
                parse_mode='HTML'
            )
            return
        if email_prefix != generated_prefix:
            bot.reply_to(
                message,
                f"""
❌ Nama email tidak sesuai dengan hasil generate!
Nama yang di-generate: <code>{generated_prefix}</code>
Kamu kirim: <code>{email_prefix}</code>

Silakan generate ulang atau perbaiki nama email.
                """,
                parse_mode='HTML'
            )
            return

        if password != REQUIRED_PASSWORD:
            bot.reply_to(
                message,
                f"❌ Password wajib <code>{REQUIRED_PASSWORD}</code> (huruf kecil semua).\nGmail ditolak.",
                parse_mode='HTML'
            )
            return

        if not check_gmail_valid(email, password):
            bot.reply_to(
                message,
                "❌ Gmail tidak aktif / login gagal.\nPastikan Gmail masih Live dan password benar.\nCek di https://en.gmailcheck.com/",
                parse_mode='HTML'
            )
            return

        gmail_id = db.add_gmail(email, password, user_id)
        db.clear_generated_prefix(user_id)

        admin_text = f"""
<b>📥 GMAIL BARU - PENDING</b>
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
                bot.send_message(admin, admin_text, reply_markup=markup, parse_mode='HTML')
            except:
                pass

        bot.reply_to(
            message,
            f"✅ <b>GMAIL TERKIRIM!</b>\n📧 {email}\n⏳ Menunggu verifikasi admin. Kamu akan mendapat notifikasi setelah disetujui.",
            parse_mode='HTML'
        )
        show_text_menu(message.chat.id)
    except:
        bot.reply_to(message, "❌ Format salah! Gunakan <code>email|password</code>", parse_mode='HTML')

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
        msg = f"✅ <b>GMAIL DITERIMA!</b>\n📧 {gmail[1]}\n💰 +{format_rupiah(PRICE_PER_EMAIL)}\n📦 Sisa balance: {format_rupiah(user[6])}"
        bot.answer_callback_query(call.id, "✅ Gmail diterima!", show_alert=True)
    else:
        msg = f"❌ <b>GMAIL DITOLAK</b>\n📧 {gmail[1]}\nAlasan: tidak valid / tidak sesuai ketentuan."
        bot.answer_callback_query(call.id, "❌ Gmail ditolak.", show_alert=True)

    try:
        bot.send_message(user_id, msg, parse_mode='HTML')
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
<b>💰 BALANCE KAMU</b>
<b>━━━━━━━━━━━━━━━━━━</b>
💵 Saldo: {format_rupiah(user[6])}
📦 Total Setor: {user[7]} akun
💸 Total WD: {format_rupiah(user[8])}
<b>━━━━━━━━━━━━━━━━━━</b>
<i>Minimal WD: {format_rupiah(MIN_WITHDRAW)}</i>
        """
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')
    else:
        bot.send_message(call.message.chat.id, "❌ Data tidak ditemukan. /start dulu.", parse_mode='HTML')

# ========== RULES ==========
@bot.callback_query_handler(func=lambda call: call.data == 'rules')
def rules(call):
    text = f"""
<b>📜 RULES STORAN GMAIL - JOB GMAIL PRO</b>
<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>

1️⃣ <b>Gmail harus Fresh (baru dibuat)</b>

2️⃣ <b>Nama Gmail WAJIB sesuai dengan hasil GENERATE dari bot.</b>
   - Klik tombol <b>🎲 GENERATE NAMA</b> di menu.
   - Buat Gmail dengan nama persis seperti yang diberikan.
   - Tidak boleh mengubah, menambah, atau mengurangi karakter.

3️⃣ <b>Tanggal lahir akun Gmail wajib 18 tahun ke atas.</b>

4️⃣ <b>Password Gmail wajib:</b> <code>{REQUIRED_PASSWORD}</code> (huruf kecil semua).

5️⃣ <b>Akun tidak boleh ditautkan dengan nomor/email pemulihan.</b>

6️⃣ <b>Cek status Gmail di https://en.gmailcheck.com/</b> sebelum setor.

7️⃣ <b>Hanya kirim Gmail dengan status Live/Aktif.</b>

<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>
📌 <i>Catatan:</i>
• Setiap kali setor, kamu WAJIB generate nama baru.
• Gmail yang tidak sesuai dengan hasil generate akan ditolak.
• Admin berhak menolak jika ada indikasi pelanggaran.
<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>
<i>© 2026 JOB GMAIL PRO</i>
    """
    bot.send_message(call.message.chat.id, text, parse_mode='HTML')

# ========== REFERRAL ==========
@bot.callback_query_handler(func=lambda call: call.data == 'referral')
def referral(call):
    user_id = call.from_user.id
    user = db.get_user(user_id)
    if user:
        link = f"https://t.me/{BOT_USERNAME}?start={user[9]}"
        total_ref = db.count_referrals(user_id)
        text = f"""
<b>🔗 REFERRAL KAMU</b>
<b>━━━━━━━━━━━━━━━━━━</b>
📌 Kode: <code>{user[9]}</code>
👥 Total Referral: {total_ref} orang
💰 Bonus/Referral: {format_rupiah(REFERRAL_BONUS)}

<b>📤 Bagikan Link Ini:</b>
{link}
<b>━━━━━━━━━━━━━━━━━━</b>
<i>Setiap orang daftar pakai link ini, kamu dapat bonus!</i>
        """
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')
    else:
        bot.send_message(call.message.chat.id, "❌ Data tidak ditemukan. /start dulu.", parse_mode='HTML')

# ========== RANKING ==========
@bot.callback_query_handler(func=lambda call: call.data == 'ranking')
def ranking(call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🏆 SETOR TERBANYAK", callback_data="rank_setor")
    btn2 = types.InlineKeyboardButton("💰 WD TERBANYAK", callback_data="rank_wd")
    markup.add(btn1, btn2)
    bot.send_message(call.message.chat.id, "<b>📊 Pilih Kategori Peringkat:</b>", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('rank_'))
def show_ranking(call):
    tipe = call.data.split('_')[1]
    data = db.get_ranking(tipe)
    text = f"<b>🏆 PERINGKAT {'SETOR' if tipe == 'setor' else 'WD'}</b> \n<b>━━━━━━━━━━━━━━━━━━</b>\n"
    if data:
        for i, row in enumerate(data, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            value = row[1] if tipe == 'setor' else format_rupiah(row[1])
            text += f"{medal} @{row[0] or 'User'} — {value}\n"
    else:
        text += "Belum ada data, boss!"
    bot.send_message(call.message.chat.id, text, parse_mode='HTML')

# ========== WITHDRAW ==========
@bot.callback_query_handler(func=lambda call: call.data == 'withdraw')
def withdraw(call):
    user_id = call.from_user.id
    user = db.get_user(user_id)
    if not user:
        bot.send_message(call.message.chat.id, "❌ Data tidak ditemukan. /start dulu.", parse_mode='HTML')
        return
    if user[6] < MIN_WITHDRAW:
        bot.send_message(
            call.message.chat.id,
            f"❌ Saldo kamu {format_rupiah(user[6])}, minimal WD {format_rupiah(MIN_WITHDRAW)}.",
            parse_mode='HTML'
        )
        return
    msg = bot.send_message(
        call.message.chat.id,
        f"""
<b>💸 FORMAT WITHDRAW</b>

Kirim nomor DANA dan jumlah:
<code>nomor|jumlah</code>

Contoh: <code>08123456789|10000</code>
Saldo: {format_rupiah(user[6])}
        """,
        parse_mode='HTML'
    )
    bot.register_next_step_handler(msg, proses_withdraw)

def proses_withdraw(message):
    user_id = message.from_user.id
    try:
        dana_number, amount_str = message.text.split('|')
        amount = int(amount_str)
        user = db.get_user(user_id)

        if not is_valid_dana(dana_number):
            bot.reply_to(message, "❌ Nomor DANA tidak valid (harus 08xxx).", parse_mode='HTML')
            return
        if amount < MIN_WITHDRAW:
            bot.reply_to(message, f"❌ Minimal WD {format_rupiah(MIN_WITHDRAW)}.", parse_mode='HTML')
            return
        if amount > user[6]:
            bot.reply_to(message, f"❌ Saldo tidak cukup. Saldo: {format_rupiah(user[6])}.", parse_mode='HTML')
            return

        db.add_withdraw(user_id, amount, dana_number)
        user = db.get_user(user_id)

        admin_text = f"""
<b>💸 WD REQUEST!</b>
👤 @{message.from_user.username or message.from_user.id}
🆔 {user_id}
📱 {dana_number}
💰 {format_rupiah(amount)}
📦 Sisa Saldo: {format_rupiah(user[6])}
⏳ Status: PENDING
        """
        for admin in ADMIN_ID:
            try:
                bot.send_message(admin, admin_text, parse_mode='HTML')
            except:
                pass

        bot.reply_to(
            message,
            f"✅ <b>WD BERHASIL DIREQUEST!</b>\n💸 {format_rupiah(amount)}\n📱 {dana_number}\n⏳ Tunggu admin transfer 1x24 jam.",
            parse_mode='HTML'
        )
        show_text_menu(message.chat.id)
    except:
        bot.reply_to(message, "❌ Format salah! Gunakan <code>nomor|jumlah</code>", parse_mode='HTML')

# ========== ADMIN PANEL ==========
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_ID:
        bot.reply_to(message, "❌ Anda tidak memiliki akses.", parse_mode='HTML')
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("📥 GMAIL PENDING", callback_data="admin_gmail")
    btn2 = types.InlineKeyboardButton("💸 WD PENDING", callback_data="admin_wd")
    btn3 = types.InlineKeyboardButton("📊 STATISTIK", callback_data="admin_stats")
    btn4 = types.InlineKeyboardButton("📥 DOWNLOAD AKUN", callback_data="admin_download")
    markup.add(btn1, btn2, btn3, btn4)
    bot.send_message(message.chat.id, "<b>🔧 ADMIN PANEL</b>", reply_markup=markup, parse_mode='HTML')

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
<b>📊 STATISTIK BOT</b>
<b>━━━━━━━━━━━━━━━━━━</b>
👥 Total User: {total_user}
📦 Total Gmail Setor: {total_setor}
💰 Total Balance: {format_rupiah(total_balance)}
<b>━━━━━━━━━━━━━━━━━━</b>
        """
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')

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
    bot.reply_to(message, "Gunakan tombol menu atau /start untuk memulai.", parse_mode='HTML')

# ========== MAIN ==========
if __name__ == '__main__':
    print("🚀 JOB GMAIL PRO BOT (DENGAN GENERATE) STARTED...")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)