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

    # BYPASS UNTUK ADMIN ATAU USER YANG SUDAH TERVERIFIKASI
    if user_id in ADMIN_ID or user[10] == 1:  
        if user_id in ADMIN_ID and user[10] == 0:
            db.set_verified(user_id)
        send_main_menu(message.chat.id, user)
    else:
        text = f"""
<blockquote><b>✦ ═══ 📢 VERIFIKASI CHANNEL ═══ ✦</b>

<i>Selamat Datang di <b>JOB GMAIL PRO</b>!</i>
Sebelum mengakses fitur bot, kamu <b>WAJIB</b> bergabung ke channel resmi kami terlebih dahulu.

📢 <b>Official Channel:</b> {CHANNEL_USERNAME}

Silakan klik tombol <b>JOIN CHANNEL</b> di bawah, lalu pilih <b>VERIFIKASI</b>.</blockquote>
        """
        markup = types.InlineKeyboardMarkup(row_width=1)
        clean_channel = CHANNEL_USERNAME.replace('@','').strip()
        btn_join = types.InlineKeyboardButton("📢 ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ", url=f"https://t.me/{clean_channel}")
        btn_verify = types.InlineKeyboardButton("✅ ᴠᴇʀɪꜰɪᴋᴀꜱɪ", callback_data="verify")
        markup.add(btn_join, btn_verify)
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='HTML')

# ========== VERIFIKASI JOIN ==========
@bot.callback_query_handler(func=lambda call: call.data == 'verify')
def verify(call):
    user_id = call.from_user.id
    
    # BYPASS KHUSUS ADMIN (TIDAK PERLU JOIN)
    if user_id in ADMIN_ID:
        db.set_verified(user_id)
        user = db.get_user(user_id)
        send_main_menu(call.message.chat.id, user)
        bot.answer_callback_query(call.id, "👑 Akses Admin Diterima!")
        return

    try:
        chat_target = CHANNEL_USERNAME if CHANNEL_USERNAME.startswith('@') else f"@{CHANNEL_USERNAME}"
        member = bot.get_chat_member(chat_target, user_id)
        
        if member.status in ['member', 'administrator', 'creator']:
            db.set_verified(user_id)
            user = db.get_user(user_id)
            send_main_menu(call.message.chat.id, user)
            bot.answer_callback_query(call.id, "⚡ Verifikasi Berhasil! Selamat datang.")
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
        else:
            bot.answer_callback_query(call.id, "❌ Kamu belum join channel! Silakan join terlebih dahulu.", show_alert=True)
            
    except Exception as e:
        error_msg = str(e).replace('<', '&lt;').replace('>', '&gt;')
        bot.answer_callback_query(
            call.id, 
            "⚠️ Gagal mengecek status channel!\nPastikan Bot sudah diangkat menjadi ADMIN di Channel.", 
            show_alert=True
        )
        for admin in ADMIN_ID:
            try:
                bot.send_message(admin, f"<b>⚠️ SYSTEM ERROR VERIFIKASI:</b>\n<code>{error_msg}</code>", parse_mode='HTML')
            except:
                pass

# ========== MENU UTAMA ==========
def send_main_menu(chat_id, user):
    caption = f"""
<blockquote><b>✨ ═══ ᴊᴏʙ ɢᴍᴀɪʟ ᴘʀᴏ ═══ ✨</b>

👤 <b>ᴜꜱᴇʀ :</b> <code>{user[2] if user[2] else user[1]}</code>
🆔 <b>ɪᴅ :</b> <code>{user[0]}</code>
💰 <b>ꜱᴀʟᴅᴏ :</b> <code>{format_rupiah(user[6])}</code>
📦 <b>ᴛᴏᴛᴀʟ ꜱᴇᴛᴏʀ :</b> <code>{user[7]} Akun</code>
💸 <b>ᴛᴏᴛᴀʟ ᴡᴅ :</b> <code>{format_rupiah(user[8])}</code>
🔗 <b>ʀᴇꜰᴇʀʀᴀʟ :</b> <code>{user[9]}</code>

<b><i>Silakan pilih menu di bawah ini untuk memulai:</i></b></blockquote>
    """
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("📤 ꜱᴇᴛᴏʀ ɢᴍᴀɪʟ", callback_data="setor")
    btn2 = types.InlineKeyboardButton("💰 ꜱᴀʟᴅᴏ & ʙᴀʟᴀɴᴄᴇ", callback_data="balance")
    btn3 = types.InlineKeyboardButton("📜 ʀᴜʟᴇꜱ & ᴀᴛᴜʀᴀɴ", callback_data="rules")
    btn4 = types.InlineKeyboardButton("🔗 ʀᴇꜰᴇʀʀᴀʟ", callback_data="referral")
    btn5 = types.InlineKeyboardButton("🏆 ᴘᴇʀɪɴɢᴋᴀᴛ", callback_data="ranking")
    btn6 = types.InlineKeyboardButton("💸 ᴡɪᴛʜᴅʀᴀᴡ", callback_data="withdraw")
    btn7 = types.InlineKeyboardButton("🎲 ɢᴇɴᴇʀᴀᴛᴇ ɴᴀᴍᴀ", callback_data="generate")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7)

    bot.send_photo(chat_id, photo=PHOTO_URL, caption=caption, reply_markup=markup, parse_mode='HTML')

# ========== MENU TEKS (NAVIGASI) ==========
def show_text_menu(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("📤 ꜱᴇᴛᴏʀ ɢᴍᴀɪʟ", callback_data="setor")
    btn2 = types.InlineKeyboardButton("💰 ꜱᴀʟᴅᴏ & ʙᴀʟᴀɴᴄᴇ", callback_data="balance")
    btn3 = types.InlineKeyboardButton("📜 ʀᴜʟᴇꜱ & ᴀᴛᴜʀᴀɴ", callback_data="rules")
    btn4 = types.InlineKeyboardButton("🔗 ʀᴇꜰᴇʀʀᴀʟ", callback_data="referral")
    btn5 = types.InlineKeyboardButton("🏆 ᴘᴇʀɪɴɢᴋᴀᴛ", callback_data="ranking")
    btn6 = types.InlineKeyboardButton("💸 ᴡɪᴛʜᴅʀᴀᴡ", callback_data="withdraw")
    btn7 = types.InlineKeyboardButton("🎲 ɢᴇɴᴇʀᴀᴛᴇ ɴᴀᴍᴀ", callback_data="generate")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7)
    
    bot.send_message(chat_id, "<blockquote><b>📌 ᴍᴇɴᴜ ᴜᴛᴀᴍᴀ Navigasi Bot:</b></blockquote>", reply_markup=markup, parse_mode='HTML')

# ========== GENERATE NAMA ==========
@bot.callback_query_handler(func=lambda call: call.data == 'generate')
def generate_name(call):
    user_id = call.from_user.id
    prefix = generate_random_prefix(10)
    db.set_generated_prefix(user_id, prefix)
    bot.answer_callback_query(call.id, f"✅ Nama berhasil di-generate!")
    bot.send_message(
        call.message.chat.id,
        f"""
<blockquote><b>🎲 ɢᴇɴᴇʀᴀᴛᴇ ɴᴀᴍᴀ ɢᴍᴀɪʟ</b>

PREFIX NAMA AKUN:
<code>{prefix}</code>

<b>📌 Step Pembuatan:</b>
1. Buat Gmail baru sesuai prefix: <code>{prefix}@gmail.com</code>
2. Gunakan Password Wajib: <code>{REQUIRED_PASSWORD}</code>
3. Kirim ke bot via menu <b>SETOR GMAIL</b>.

⚠️ <i>Prefix ini berlaku untuk 1x setoran.</i></blockquote>
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
            "<blockquote>❌ <b>AKSES DITOLAK:</b> Kamu belum melakukan generate nama! Klik menu <b>🎲 GENERATE NAMA</b> terlebih dahulu.</blockquote>",
            parse_mode='HTML'
        )
        return
    msg = bot.send_message(
        call.message.chat.id,
        f"""
<blockquote><b>📧 ꜰᴏʀᴍᴀᴛ ꜱᴇᴛᴏʀ ɢᴍᴀɪʟ</b>

Kirimkan email & password dengan format baku:
<code>email|password</code>

<b>Contoh:</b>
<code>{generated}@gmail.com|{REQUIRED_PASSWORD}</code>

⚠️ <i>Wajib sesuai nama generate:</i> <code>{generated}</code>
⚠️ <i>Password Wajib:</i> <code>{REQUIRED_PASSWORD}</code></blockquote>
        """,
        parse_mode='HTML'
    )
    bot.register_next_step_handler(msg, proses_setor)

def proses_setor(message):
    user_id = message.from_user.id
    try:
        email, password = message.text.split('|')

        if not validate_email(email):
            bot.reply_to(message, "<blockquote>❌ <b>FORMAT SALAH:</b> Format email tidak valid. Silakan coba lagi.</blockquote>", parse_mode='HTML')
            return

        email_prefix = email.split('@')[0]
        generated_prefix = db.get_generated_prefix(user_id)

        if not generated_prefix:
            bot.reply_to(message, "<blockquote>❌ Kamu belum generate nama! Klik tombol generate di menu.</blockquote>", parse_mode='HTML')
            return

        if email_prefix != generated_prefix:
            bot.reply_to(
                message,
                f"""
<blockquote>❌ <b>NAMA TIDAK SESUAI!</b>
• Hasil Generate: <code>{generated_prefix}</code>
• Yang Dikirim: <code>{email_prefix}</code>

Silakan perbaiki atau generate ulang!</blockquote>
                """,
                parse_mode='HTML'
            )
            return

        if password != REQUIRED_PASSWORD:
            bot.reply_to(
                message,
                f"<blockquote>❌ <b>PASSWORD SALAH!</b> Password wajib menggunakan <code>{REQUIRED_PASSWORD}</code>.</blockquote>",
                parse_mode='HTML'
            )
            return

        if not check_gmail_valid(email, password):
            bot.reply_to(
                message,
                "<blockquote>❌ <b>LOGIN GAGAL!</b> Gmail tidak aktif atau tidak bisa diakses IMAP.\nCek status akun kamu di https://en.gmailcheck.com/</blockquote>",
                parse_mode='HTML'
            )
            return

        gmail_id = db.add_gmail(email, password, user_id)
        db.clear_generated_prefix(user_id)

        admin_text = f"""
<blockquote><b>📥 ꜱᴇᴛᴏʀᴀɴ ɢᴍᴀɪʟ ʙᴀʀᴜ (PENDING)</b>

👤 <b>User:</b> @{message.from_user.username or message.from_user.id}
🆔 <b>ID User:</b> <code>{user_id}</code>
📧 <b>Email:</b> <code>{email}</code>
🔑 <b>Password:</b> <code>{password}</code>
📅 <b>Waktu:</b> <code>{datetime.now().strftime('%Y-%m-%d %H:%M')}</code>

✅ <i>Status IMAP LIVE & Nama Sesuai Generate!</i></blockquote>
        """
        markup = types.InlineKeyboardMarkup()
        btn_approve = types.InlineKeyboardButton("✅ ᴛᴇʀɪᴍᴀ", callback_data=f"approve_gmail_{gmail_id}")
        btn_reject = types.InlineKeyboardButton("❌ ᴛᴏʟᴀᴋ", callback_data=f"reject_gmail_{gmail_id}")
        markup.add(btn_approve, btn_reject)

        for admin in ADMIN_ID:
            try:
                bot.send_message(admin, admin_text, reply_markup=markup, parse_mode='HTML')
            except:
                pass

        bot.reply_to(
            message,
            f"<blockquote>✅ <b>GMAIL BERHASIL DIKIRIM!</b>\n📧 Email: <code>{email}</code>\n\n⏳ <i>Sedang diverifikasi oleh Admin. Notifikasi akan dikirim setelah disetujui.</i></blockquote>",
            parse_mode='HTML'
        )
        show_text_menu(message.chat.id)
    except:
        bot.reply_to(message, "<blockquote>❌ <b>FORMAT SALAH!</b> Gunakan format pemisah garis lurus: <code>email|password</code></blockquote>", parse_mode='HTML')

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
        msg = f"<blockquote>✅ <b>ɢᴍᴀɪʟ ᴅɪᴛᴇʀɪᴍᴀ!</b>\n📧 Email: <code>{gmail[1]}</code>\n💰 Bonus: <b>+{format_rupiah(PRICE_PER_EMAIL)}</b>\n💳 Saldo Sekarang: <code>{format_rupiah(user[6])}</code></blockquote>"
        bot.answer_callback_query(call.id, "✅ Gmail diterima!", show_alert=True)
    else:
        msg = f"<blockquote>❌ <b>ɢᴍᴀɪʟ ᴅɪᴛᴏʟᴀᴋ</b>\n📧 Email: <code>{gmail[1]}</code>\n⚠️ <i>Alasan: Akun mati/tidak sesuai ketentuan.</i></blockquote>"
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
<blockquote><b>💰 ɪɴꜰᴏ ꜱᴀʟᴅᴏ & ʙᴀʟᴀɴᴄᴇ</b>

💵 <b>Saldo Aktif:</b> <code>{format_rupiah(user[6])}</code>
📦 <b>Total Setor:</b> <code>{user[7]} Akun</code>
💸 <b>Total WD:</b> <code>{format_rupiah(user[8])}</code>

📌 <i>Minimal Penarikan (WD): {format_rupiah(MIN_WITHDRAW)}</i></blockquote>
        """
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')
    else:
        bot.send_message(call.message.chat.id, "<blockquote>❌ Data akun tidak ditemukan. Ketik /start ulang.</blockquote>", parse_mode='HTML')

# ========== RULES ==========
@bot.callback_query_handler(func=lambda call: call.data == 'rules')
def rules(call):
    text = f"""
<blockquote><b>📜 ʀᴜʟᴇꜱ & ꜱʏᴀʀᴀᴛ ꜱᴇᴛᴏʀ ɢᴍᴀɪʟ</b>

1️⃣ <b>Akun Fresh (Baru dibuat).</b>
2️⃣ <b>Wajib menggunakan NAMA HASIL GENERATE dari bot.</b>
   - Tidak boleh mengubah atau menambah karakter prefix.
3️⃣ <b>Umur akun minimal 18 tahun+ (Tahun Lahir &lt;= 2005).</b>
4️⃣ <b>Password Wajib:</b> <code>{REQUIRED_PASSWORD}</code>
5️⃣ <b>Dilarang menautkan Nomor HP / Email Pemulihan.</b>
6️⃣ <b>Cek kualitas akun di:</b> https://en.gmailcheck.com/

⚠️ <i>Pelanggaran aturan berpotensi menyebabkan akun ditolak dan garansi hangus.</i></blockquote>
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
<blockquote><b>🔗 ᴘʀᴏɢʀᴀᴍ ʀᴇꜰᴇʀʀᴀʟ</b>

🔑 <b>Kode Reff:</b> <code>{user[9]}</code>
👥 <b>Total Reff:</b> <code>{total_ref} Orang</code>
💰 <b>Komisi:</b> <code>{format_rupiah(REFERRAL_BONUS)} / User</code>

<b>📤 Link Undangan Kamu:</b>
<code>{link}</code>

<i>Bagikan link di atas dan dapatkan bonus saldo otomatis!</i></blockquote>
        """
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')
    else:
        bot.send_message(call.message.chat.id, "<blockquote>❌ Data tidak ditemukan. Ketik /start.</blockquote>", parse_mode='HTML')

# ========== RANKING ==========
@bot.callback_query_handler(func=lambda call: call.data == 'ranking')
def ranking(call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🏆 ꜱᴇᴛᴏʀ ᴛᴇʀʙᴀɴʏᴀᴋ", callback_data="rank_setor")
    btn2 = types.InlineKeyboardButton("💰 ᴡᴅ ᴛᴇʀʙᴀɴʏᴀᴋ", callback_data="rank_wd")
    markup.add(btn1, btn2)
    bot.send_message(call.message.chat.id, "<blockquote><b>📊 ᴘɪʟɪʜ ᴋᴀᴛᴇɢᴏʀɪ ᴘᴇʀɪɴɢᴋᴀᴛ:</b></blockquote>", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('rank_'))
def show_ranking(call):
    tipe = call.data.split('_')[1]
    data = db.get_ranking(tipe)
    text = f"<blockquote><b>🏆 ᴘᴇʀɪɴɢᴋᴀᴛ TOP 10 ({'SETOR' if tipe == 'setor' else 'WITHDRAW'})</b>\n\n"
    if data:
        for i, row in enumerate(data, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"<b>{i}.</b>"
            value = f"{row[1]} Akun" if tipe == 'setor' else format_rupiah(row[1])
            text += f"{medal} @{row[0] or 'User'} — <code>{value}</code>\n"
    else:
        text += "<i>Belum ada data terkumpul.</i>"
    text += "</blockquote>"
    bot.send_message(call.message.chat.id, text, parse_mode='HTML')

# ========== WITHDRAW ==========
@bot.callback_query_handler(func=lambda call: call.data == 'withdraw')
def withdraw(call):
    user_id = call.from_user.id
    user = db.get_user(user_id)
    if not user:
        bot.send_message(call.message.chat.id, "<blockquote>❌ Data akun tidak ditemukan. Ketik /start.</blockquote>", parse_mode='HTML')
        return
    if user[6] < MIN_WITHDRAW:
        bot.send_message(
            call.message.chat.id,
            f"<blockquote>❌ <b>SALDO TIDAK CUKUP!</b>\nSaldo kamu: <code>{format_rupiah(user[6])}</code>\nMinimal WD: <code>{format_rupiah(MIN_WITHDRAW)}</code></blockquote>",
            parse_mode='HTML'
        )
        return
    msg = bot.send_message(
        call.message.chat.id,
        f"""
<blockquote><b>💸 ꜰᴏʀᴍᴀᴛ ᴡɪᴛʜᴅʀᴀᴡ (ᴅᴀɴᴀ)</b>

Kirim nomor DANA & jumlah penarikan:
<code>nomor|jumlah</code>

<b>Contoh:</b> <code>081234567890|10000</code>
💰 <b>Saldo Saat Ini:</b> <code>{format_rupiah(user[6])}</code></blockquote>
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
            bot.reply_to(message, "<blockquote>❌ Nomor DANA tidak valid (harus diawali 08xxx).</blockquote>", parse_mode='HTML')
            return
        if amount < MIN_WITHDRAW:
            bot.reply_to(message, f"<blockquote>❌ Minimal WD adalah {format_rupiah(MIN_WITHDRAW)}.</blockquote>", parse_mode='HTML')
            return
        if amount > user[6]:
            bot.reply_to(message, f"<blockquote>❌ Saldo tidak cukup. Saldo kamu: {format_rupiah(user[6])}.</blockquote>", parse_mode='HTML')
            return

        db.add_withdraw(user_id, amount, dana_number)
        user = db.get_user(user_id)

        admin_text = f"""
<blockquote><b>💸 ᴘᴇɴᴀʀɪᴋᴀɴ ᴅᴀɴᴀ (PENDING)</b>

👤 <b>User:</b> @{message.from_user.username or message.from_user.id}
🆔 <b>ID:</b> <code>{user_id}</code>
📱 <b>No DANA:</b> <code>{dana_number}</code>
💰 <b>Nominal:</b> <code>{format_rupiah(amount)}</code>
💳 <b>Sisa Saldo:</b> <code>{format_rupiah(user[6])}</code></blockquote>
        """
        for admin in ADMIN_ID:
            try:
                bot.send_message(admin, admin_text, parse_mode='HTML')
            except:
                pass

        bot.reply_to(
            message,
            f"<blockquote>✅ <b>REQUEST WD SUCCESS!</b>\n💸 Nominal: <code>{format_rupiah(amount)}</code>\n📱 No DANA: <code>{dana_number}</code>\n\n⏳ <i>Diproses admin maksimal 1x24 jam.</i></blockquote>",
            parse_mode='HTML'
        )
        show_text_menu(message.chat.id)
    except:
        bot.reply_to(message, "<blockquote>❌ <b>FORMAT SALAH!</b> Gunakan format: <code>nomor|jumlah</code></blockquote>", parse_mode='HTML')

# ========== ADMIN PANEL ==========
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_ID:
        bot.reply_to(message, "<blockquote>❌ Anda tidak memiliki akses admin.</blockquote>", parse_mode='HTML')
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("📥 ɢᴍᴀɪʟ ᴘᴇɴᴅɪɴɢ", callback_data="admin_gmail")
    btn2 = types.InlineKeyboardButton("💸 ᴡᴅ ᴘᴇɴᴅɪɴɢ", callback_data="admin_wd")
    btn3 = types.InlineKeyboardButton("📊 ꜱᴛᴀᴛɪꜱᴛɪᴋ", callback_data="admin_stats")
    btn4 = types.InlineKeyboardButton("📥 ᴅᴏᴡɴʟᴏᴀᴅ ᴀᴋᴜɴ", callback_data="admin_download")
    markup.add(btn1, btn2, btn3, btn4)
    bot.send_message(message.chat.id, "<blockquote><b>🛡️ ᴀᴅᴍɪɴ ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ</b></blockquote>", reply_markup=markup, parse_mode='HTML')

# ========== ADMIN DOWNLOAD ==========
@bot.callback_query_handler(func=lambda call: call.data == 'admin_download')
def admin_download(call):
    if call.from_user.id not in ADMIN_ID:
        bot.answer_callback_query(call.id, "Akses ditolak.", show_alert=True)
        return
    accounts = db.get_and_clear_verified_gmails()
    if not accounts:
        bot.answer_callback_query(call.id, "Tidak ada akun verified yang tersedia.", show_alert=True)
        return
    content = "\n".join([f"{email}:{pwd}" for email, pwd in accounts])
    file_obj = io.BytesIO(content.encode('utf-8'))
    file_obj.name = "akun_gmail_verified.txt"
    try:
        bot.send_document(
            call.message.chat.id,
            file_obj,
            caption=f"<blockquote>✅ <b>DOWNLOAD SUCCESS</b>\n📦 Total: <b>{len(accounts)} Akun</b>\n⚠️ <i>Akun yang diunduh otomatis dibersihkan dari DB.</i></blockquote>",
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id, f"✅ {len(accounts)} akun diunduh!")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Gagal: {str(e)}", show_alert=True)

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
                text = f"<blockquote>📧 <code>{g[1]}</code>\n🔑 <code>{g[2]}</code>\n👤 User ID: <code>{g[3]}</code>\n📅 {g[5]}</blockquote>"
                bot.send_message(call.message.chat.id, text, parse_mode='HTML')
        else:
            bot.send_message(call.message.chat.id, "<blockquote>✅ Tidak ada Gmail pending.</blockquote>", parse_mode='HTML')

    elif action == 'wd':
        wds = db.get_pending_withdraws()
        if wds:
            for w in wds:
                markup = types.InlineKeyboardMarkup()
                btn_process = types.InlineKeyboardButton("✅ ᴘʀᴏꜱᴇꜱ", callback_data=f"process_wd_{w[0]}")
                btn_cancel = types.InlineKeyboardButton("❌ ʙᴀᴛᴀʟ", callback_data=f"cancel_wd_{w[0]}")
                markup.add(btn_process, btn_cancel)
                bot.send_message(
                    call.message.chat.id,
                    f"<blockquote>💸 <b>WD ID:</b> <code>{w[0]}</code>\n👤 <b>User:</b> <code>{w[1]}</code>\n💰 <b>Nominal:</b> <code>{format_rupiah(w[2])}</code>\n📱 <b>DANA:</b> <code>{w[3]}</code></blockquote>",
                    reply_markup=markup,
                    parse_mode='HTML'
                )
        else:
            bot.send_message(call.message.chat.id, "<blockquote>✅ Tidak ada WD pending.</blockquote>", parse_mode='HTML')

    elif action == 'stats':
        total_user, total_setor, total_balance = db.get_stats()
        text = f"""
<blockquote><b>📊 ꜱᴛᴀᴛɪꜱᴛɪᴋ ʙᴏᴛ</b>

👥 <b>Total User:</b> <code>{total_user}</code>
📦 <b>Total Setor:</b> <code>{total_setor} Akun</code>
💰 <b>Total Balance:</b> <code>{format_rupiah(total_balance)}</code></blockquote>
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
    bot.reply_to(message, "<blockquote>Gunakan tombol menu atau ketik /start untuk memulai navigasi.</blockquote>", parse_mode='HTML')

# ========== MAIN ==========
if __name__ == '__main__':
    print("🚀 JOB GMAIL PRO BOT STARTED...")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
