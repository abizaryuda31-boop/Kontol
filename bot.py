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

# ========== HELPER BUILDER KEYBOARD ==========
def generate_main_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("📤 ꜱᴇᴛᴏʀ ɢᴍᴀɪʟ", callback_data="setor")
    btn2 = types.InlineKeyboardButton("💰 ꜱᴀʟᴅᴏ & ʙᴀʟᴀɴᴄᴇ", callback_data="balance")
    btn3 = types.InlineKeyboardButton("📜 ʀᴜʟᴇꜱ & ᴀᴛᴜʀᴀɴ", callback_data="rules")
    btn4 = types.InlineKeyboardButton("🔗 ʀᴇꜰᴇʀʀᴀʟ", callback_data="referral")
    btn5 = types.InlineKeyboardButton("🏆 ᴘᴇʀɪɴɢᴋᴀᴛ", callback_data="ranking")
    btn6 = types.InlineKeyboardButton("💸 ᴡɪᴛʜᴅʀᴀᴡ", callback_data="withdraw")
    btn7 = types.InlineKeyboardButton("🎲 ɢᴇɴᴇʀᴀᴛᴇ ɴᴀᴍᴀ", callback_data="generate")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7)
    return markup

def generate_back_markup():
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("🔙 ᴋᴇᴍʙᴀʟɪ ᴋᴇ ᴍᴇɴᴜ", callback_data="back_to_main")
    markup.add(btn_back)
    return markup

def generate_random_prefix(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def get_caption_main_menu(user):
    return f"""
<blockquote><b>✨ ═══ ᴊᴏʙ ɢᴍᴀɪʟ ᴘʀᴏ ═══ ✨</b>

👤 <b>ᴜꜱᴇʀ :</b> <code>{user[2] if user[2] else user[1]}</code>
🆔 <b>ɪᴅ :</b> <code>{user[0]}</code>
💰 <b>ꜱᴀʟᴅᴏ :</b> <code>{format_rupiah(user[6])}</code>
📦 <b>ᴛᴏᴛᴀʟ ꜱᴇᴛᴏʀ :</b> <code>{user[7]} Akun</code>
💸 <b>ᴛᴏᴛᴀʟ ᴡᴅ :</b> <code>{format_rupiah(user[8])}</code>
🔗 <b>ʀᴇꜰᴇʀʀᴀʟ :</b> <code>{user[9]}</code>

<b><i>Silakan pilih menu di bawah ini untuk memulai:</i></b></blockquote>
    """

# ========== START COMMAND ==========
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

    if user_id in ADMIN_ID or user[10] == 1:
        if user_id in ADMIN_ID and user[10] == 0:
            db.set_verified(user_id)
        bot.send_photo(message.chat.id, photo=PHOTO_URL, caption=get_caption_main_menu(user), reply_markup=generate_main_markup(), parse_mode='HTML')
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

# ========== CALLBACK: VERIFIKASI CHANNEL ==========
@bot.callback_query_handler(func=lambda call: call.data == 'verify')
def verify(call):
    user_id = call.from_user.id
    if user_id in ADMIN_ID:
        db.set_verified(user_id)
        user = db.get_user(user_id)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_photo(call.message.chat.id, photo=PHOTO_URL, caption=get_caption_main_menu(user), reply_markup=generate_main_markup(), parse_mode='HTML')
        bot.answer_callback_query(call.id, "👑 Akses Admin Diterima!")
        return

    try:
        chat_target = CHANNEL_USERNAME if CHANNEL_USERNAME.startswith('@') else f"@{CHANNEL_USERNAME}"
        member = bot.get_chat_member(chat_target, user_id)
        
        if member.status in ['member', 'administrator', 'creator']:
            db.set_verified(user_id)
            user = db.get_user(user_id)
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_photo(call.message.chat.id, photo=PHOTO_URL, caption=get_caption_main_menu(user), reply_markup=generate_main_markup(), parse_mode='HTML')
            bot.answer_callback_query(call.id, "⚡ Verifikasi Berhasil!")
        else:
            bot.answer_callback_query(call.id, "❌ Kamu belum join channel!", show_alert=True)
    except Exception as e:
        bot.answer_callback_query(call.id, "⚠️ Gagal mengecek status channel! Pastikan Bot sudah ADMIN.", show_alert=True)

# ========== CALLBACK: BACK TO MAIN MENU ==========
@bot.callback_query_handler(func=lambda call: call.data == 'back_to_main')
def back_to_main(call):
    user_id = call.from_user.id
    user = db.get_user(user_id)
    if not user:
        bot.answer_callback_query(call.id, "User tidak ditemukan. Gunakan /start")
        return

    bot.answer_callback_query(call.id)
    try:
        # Edit caption jika berupa photo, jika tidak kirim ulang photo menu
        bot.edit_message_caption(
            caption=get_caption_main_menu(user),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=generate_main_markup(),
            parse_mode='HTML'
        )
    except:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_photo(call.message.chat.id, photo=PHOTO_URL, caption=get_caption_main_menu(user), reply_markup=generate_main_markup(), parse_mode='HTML')

# ========== CALLBACK: GENERATE NAMA ==========
@bot.callback_query_handler(func=lambda call: call.data == 'generate')
def generate_name(call):
    user_id = call.from_user.id
    prefix = generate_random_prefix(10)
    db.set_generated_prefix(user_id, prefix)
    
    text = f"""
<blockquote><b>🎲 ɢᴇɴᴇʀᴀᴛᴇ ɴᴀᴍᴀ ɢᴍᴀɪʟ</b>

PREFIX NAMA AKUN:
<code>{prefix}</code>

<b>📌 Step Pembuatan:</b>
1. Buat Gmail baru sesuai prefix: <code>{prefix}@gmail.com</code>
2. Gunakan Password Wajib: <code>{REQUIRED_PASSWORD}</code>
3. Klik tombol <b>SETOR GMAIL</b> untuk mengirimkan.

⚠️ <i>Prefix ini berlaku untuk 1x setoran.</i></blockquote>
    """
    markup = types.InlineKeyboardMarkup()
    btn_setor = types.InlineKeyboardButton("📤 ʟᴀɴɢꜱᴜɴɢ ꜱᴇᴛᴏʀ", callback_data="setor")
    btn_back = types.InlineKeyboardButton("🔙 ᴋᴇᴍʙᴀʟɪ", callback_data="back_to_main")
    markup.add(btn_setor)
    markup.add(btn_back)

    bot.answer_callback_query(call.id, "✅ Prefix berhasil dibuat!")
    try:
        bot.edit_message_caption(caption=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
    except:
        bot.edit_message_text(text=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

# ========== CALLBACK: BALANCE ==========
@bot.callback_query_handler(func=lambda call: call.data == 'balance')
def balance(call):
    user_id = call.from_user.id
    user = db.get_user(user_id)
    bot.answer_callback_query(call.id)
    if user:
        text = f"""
<blockquote><b>💰 ɪɴꜰᴏ ꜱᴀʟᴅᴏ & ʙᴀʟᴀɴᴄᴇ</b>

💵 <b>Saldo Aktif:</b> <code>{format_rupiah(user[6])}</code>
📦 <b>Total Setor:</b> <code>{user[7]} Akun</code>
💸 <b>Total WD:</b> <code>{format_rupiah(user[8])}</code>

📌 <i>Minimal Penarikan (WD): {format_rupiah(MIN_WITHDRAW)}</i></blockquote>
        """
        try:
            bot.edit_message_caption(caption=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=generate_back_markup(), parse_mode='HTML')
        except:
            bot.edit_message_text(text=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=generate_back_markup(), parse_mode='HTML')

# ========== CALLBACK: RULES ==========
@bot.callback_query_handler(func=lambda call: call.data == 'rules')
def rules(call):
    bot.answer_callback_query(call.id)
    text = f"""
<blockquote><b>📜 ʀᴜʟᴇꜱ & ꜱʏᴀʀᴀᴛ ꜱᴇᴛᴏʀ ɢᴍᴀɪʟ</b>

1️⃣ <b>Akun Fresh (Baru dibuat).</b>
2️⃣ <b>Wajib menggunakan NAMA HASIL GENERATE dari bot.</b>
   - Tidak boleh mengubah atau menambah karakter prefix.
3️⃣ <b>Umur akun minimal 18 tahun+ (Tahun Lahir &lt;= 2005).</b>
4️⃣ <b>Password Wajib:</b> <code>{REQUIRED_PASSWORD}</code>
5️⃣ <b>Dilarang menautkan Nomor HP / Email Pemulihan.</b>
6️⃣ <b>Cek kualitas akun di:</b> https://en.gmailcheck.com/

⚠️ <i>Pelanggaran aturan berpotensi menyebabkan akun ditolak.</i></blockquote>
    """
    try:
        bot.edit_message_caption(caption=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=generate_back_markup(), parse_mode='HTML')
    except:
        bot.edit_message_text(text=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=generate_back_markup(), parse_mode='HTML')

# ========== CALLBACK: REFERRAL DINAMIS ==========
@bot.callback_query_handler(func=lambda call: call.data == 'referral')
def referral(call):
    user_id = call.from_user.id
    user = db.get_user(user_id)
    bot.answer_callback_query(call.id)
    if user:
        link = f"https://t.me/{BOT_USERNAME}?start={user[9]}"
        total_ref = db.count_referrals(user_id)
        text = f"""
<blockquote><b>🔗 ᴘʀᴏɢʀᴀᴍ ʀᴇꜰᴇʀʀᴀʟ</b>

🔑 <b>Kode Reff:</b> <code>{user[9]}</code>
👥 <b>Total Reff:</b> <code>{total_ref} Orang</code>
💰 <b>Komisi:</b> <code>{format_rupiah(REFERRAL_BONUS)} / User</code>

<b>📤 Link Undangan Unik Kamu:</b>
<code>{link}</code>

<i>Bagikan link di atas dan dapatkan bonus saldo otomatis saat user bergabung!</i></blockquote>
        """
        try:
            bot.edit_message_caption(caption=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=generate_back_markup(), parse_mode='HTML')
        except:
            bot.edit_message_text(text=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=generate_back_markup(), parse_mode='HTML')

# ========== CALLBACK: RANKING ==========
@bot.callback_query_handler(func=lambda call: call.data == 'ranking')
def ranking(call):
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🏆 ꜱᴇᴛᴏʀ ᴛᴇʀʙᴀɴʏᴀᴋ", callback_data="rank_setor")
    btn2 = types.InlineKeyboardButton("💰 ᴡᴅ ᴛᴇʀʙᴀɴʏᴀᴋ", callback_data="rank_wd")
    btn_back = types.InlineKeyboardButton("🔙 ᴋᴇᴍʙᴀʟɪ", callback_data="back_to_main")
    markup.add(btn1, btn2)
    markup.add(btn_back)

    text = "<blockquote><b>📊 ᴘɪʟɪʜ ᴋᴀᴛᴇɢᴏʀɪ ᴘᴇʀɪɴɢᴋᴀᴛ:</b></blockquote>"
    try:
        bot.edit_message_caption(caption=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
    except:
        bot.edit_message_text(text=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('rank_'))
def show_ranking(call):
    tipe = call.data.split('_')[1]
    data = db.get_ranking(tipe)
    bot.answer_callback_query(call.id)

    text = f"<blockquote><b>🏆 ᴘᴇʀɪɴɢᴋᴀᴛ TOP 10 ({'SETOR' if tipe == 'setor' else 'WITHDRAW'})</b>\n\n"
    if data:
        for i, row in enumerate(data, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"<b>{i}.</b>"
            value = f"{row[1]} Akun" if tipe == 'setor' else format_rupiah(row[1])
            text += f"{medal} @{row[0] or 'User'} — <code>{value}</code>\n"
    else:
        text += "<i>Belum ada data terkumpul.</i>"
    text += "</blockquote>"

    try:
        bot.edit_message_caption(caption=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=generate_back_markup(), parse_mode='HTML')
    except:
        bot.edit_message_text(text=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=generate_back_markup(), parse_mode='HTML')

# ========== CALLBACK: SETOR GMAIL ==========
@bot.callback_query_handler(func=lambda call: call.data == 'setor')
def setor_gmail(call):
    user_id = call.from_user.id
    generated = db.get_generated_prefix(user_id)
    if not generated:
        bot.answer_callback_query(call.id, "❌ Kamu belum generate nama!", show_alert=True)
        return

    bot.answer_callback_query(call.id)
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

        if not generated_prefix or email_prefix != generated_prefix:
            bot.reply_to(message, f"<blockquote>❌ <b>NAMA TIDAK SESUAI!</b>\n• Hasil Generate: <code>{generated_prefix}</code></blockquote>", parse_mode='HTML')
            return

        if password != REQUIRED_PASSWORD:
            bot.reply_to(message, f"<blockquote>❌ <b>PASSWORD SALAH!</b> Gunakan <code>{REQUIRED_PASSWORD}</code>.</blockquote>", parse_mode='HTML')
            return

        if not check_gmail_valid(email, password):
            bot.reply_to(message, "<blockquote>❌ <b>LOGIN GAGAL!</b> Gmail tidak aktif atau tidak bisa diakses IMAP.</blockquote>", parse_mode='HTML')
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

✅ <i>IMAP LIVE & Prefix Match!</i></blockquote>
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

        bot.reply_to(message, f"<blockquote>✅ <b>GMAIL BERHASIL DIKIRIM!</b>\n📧 Email: <code>{email}</code>\n⏳ <i>Sedang diverifikasi oleh Admin.</i></blockquote>", parse_mode='HTML')
    except:
        bot.reply_to(message, "<blockquote>❌ <b>FORMAT SALAH!</b> Gunakan format pemisah: <code>email|password</code></blockquote>", parse_mode='HTML')

# ========== CALLBACK: WITHDRAW ==========
@bot.callback_query_handler(func=lambda call: call.data == 'withdraw')
def withdraw(call):
    user_id = call.from_user.id
    user = db.get_user(user_id)
    if not user:
        return
    if user[6] < MIN_WITHDRAW:
        bot.answer_callback_query(call.id, f"❌ Saldo kurang! Minimal WD {format_rupiah(MIN_WITHDRAW)}", show_alert=True)
        return

    bot.answer_callback_query(call.id)
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

        if not is_valid_dana(dana_number) or amount < MIN_WITHDRAW or amount > user[6]:
            bot.reply_to(message, "<blockquote>❌ Nomor DANA tidak valid atau saldo tidak mencukupi!</blockquote>", parse_mode='HTML')
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

        bot.reply_to(message, f"<blockquote>✅ <b>REQUEST WD SUCCESS!</b>\n💸 Nominal: <code>{format_rupiah(amount)}</code>\n📱 No DANA: <code>{dana_number}</code></blockquote>", parse_mode='HTML')
    except:
        bot.reply_to(message, "<blockquote>❌ <b>FORMAT SALAH!</b> Gunakan format: <code>nomor|jumlah</code></blockquote>", parse_mode='HTML')

# ========== ADMIN ACTIONS (APPROVE / REJECT / DOWNLOAD) ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_gmail_') or call.data.startswith('reject_gmail_'))
def admin_approve_gmail(call):
    if call.from_user.id not in ADMIN_ID:
        bot.answer_callback_query(call.id, "Akses ditolak.", show_alert=True)
        return

    parts = call.data.split('_')
    action, gmail_id = parts[0], int(parts[2])
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
        msg = f"<blockquote>❌ <b>ɢᴍᴀɪʟ ᴅɪᴛᴏʟᴀᴋ</b>\n📧 Email: <code>{gmail[1]}</code></blockquote>"
        bot.answer_callback_query(call.id, "❌ Gmail ditolak.", show_alert=True)

    try:
        bot.send_message(user_id, msg, parse_mode='HTML')
    except:
        pass
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ========== ADMIN CONTROL PANEL ==========
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
        bot.send_document(call.message.chat.id, file_obj, caption=f"<blockquote>✅ <b>DOWNLOAD SUCCESS</b>\n📦 Total: <b>{len(accounts)} Akun</b></blockquote>", parse_mode='HTML')
        bot.answer_callback_query(call.id, f"✅ {len(accounts)} akun diunduh!")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Gagal: {str(e)}", show_alert=True)

# ========== MAIN POLLING LOOP ==========
if __name__ == '__main__':
    print("🚀 JOB GMAIL PRO BOT FULL ONLINE...")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
