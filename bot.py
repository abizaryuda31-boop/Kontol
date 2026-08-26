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

# ========== KEYBOARD UTAMA ==========
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
    ref_code = user[4] if user[4] else "-"
    status_maintenance = "🔴 (TUTUP)" if db.is_maintenance() else "🟢 (BUKA)"
    return f"""
<blockquote><b>✨ ═══ ᴊᴏB ɢᴍᴀɪʟ ᴘʀᴏ ═══ ✨</b>

👤 <b>ᴜꜱᴇʀ :</b> <code>{user[2] if user[2] else user[1]}</code>
🆔 <b>ɪᴅ :</b> <code>{user[0]}</code>
💰 <b>ꜱᴀʟᴅᴏ :</b> <code>{format_rupiah(user[6])}</code>
📦 <b>ᴛᴏᴛᴀʟ ꜱᴇᴛᴏʀ :</b> <code>{user[7]} Akun</code>
💸 <b>ᴛᴏᴛᴀʟ ᴡᴅ :</b> <code>{format_rupiah(user[8])}</code>
🔗 <b>ʀᴇꜰᴇʀʀᴀʟ :</b> <code>{ref_code}</code>
⚙️ <b>ꜱᴛᴀᴛᴜꜱ ꜱᴇᴛᴏʀ :</b> {status_maintenance}

<b><i>Silakan pilih menu di bawah ini untuk memulai:</i></b></blockquote>
    """

# ========== START COMMAND (2 CHANNEL) ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Tidak ada"
    full_name = message.from_user.full_name or "Tidak ada"

    user = db.get_user(user_id)
    if not user:
        ref_code = generate_referral_code()
        referrer_id = 0
        if len(message.text.split()) > 1:
            incoming_ref = message.text.split()[1]
            db.c.execute("SELECT user_id FROM users WHERE referral_code = ?", (incoming_ref,))
            row = db.c.fetchone()
            if row:
                referrer_id = row[0]
        
        db.add_user(user_id, username, full_name, None, ref_code, referrer_id)
        
        if referrer_id > 0:
            db.update_balance(referrer_id, REFERRAL_BONUS)
            db.c.execute(
                "INSERT INTO referrals (referrer_id, referred_id, bonus, date) VALUES (?,?,?,?)",
                (referrer_id, user_id, REFERRAL_BONUS, datetime.now().isoformat())
            )
            db.conn.commit()
            try:
                bot.send_message(referrer_id, f"<blockquote>🎉 <b>BONUS REFERRAL!</b>\nSeseorang bergabung menggunakan link kamu. Saldo +{format_rupiah(REFERRAL_BONUS)}</blockquote>", parse_mode='HTML')
            except:
                pass
        user = db.get_user(user_id)

    if user_id in ADMIN_ID or user[10] == 1:
        if user_id in ADMIN_ID and user[10] == 0:
            db.set_verified(user_id)
            user = db.get_user(user_id)
        bot.send_photo(message.chat.id, photo=PHOTO_URL, caption=get_caption_main_menu(user), reply_markup=generate_main_markup(), parse_mode='HTML')
    else:
        text = f"""
<blockquote><b>✦ ═══ 📢 VERIFIKASI CHANNEL ═══ ✦</b>

<i>Selamat Datang di <b>JOB GMAIL PRO</b>!</i>
Sebelum mengakses fitur bot, kamu <b>WAJIB</b> bergabung ke 2 channel resmi kami:

1️⃣ <b>Channel Utama:</b> {CHANNEL_USERNAME}
2️⃣ <b>Channel Bukti TF:</b> {CHANNEL_MONITOR}

Silakan klik tombol <b>JOIN</b> di bawah, lalu pilih <b>VERIFIKASI</b>.</blockquote>
        """
        markup = types.InlineKeyboardMarkup(row_width=1)
        clean_channel1 = CHANNEL_USERNAME.replace('@','').strip()
        clean_channel2 = CHANNEL_MONITOR.replace('@','').strip()
        
        btn_join1 = types.InlineKeyboardButton("📢 ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ ᴜᴛᴀᴍᴀ", url=f"https://t.me/{clean_channel1}")
        btn_join2 = types.InlineKeyboardButton("💸 ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ ʙᴜᴋᴛɪ ᴛꜰ", url=f"https://t.me/{clean_channel2}")
        btn_verify = types.InlineKeyboardButton("✅ ᴠᴇʀɪꜰɪᴋᴀꜱɪ", callback_data="verify")
        
        markup.add(btn_join1, btn_join2, btn_verify)
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='HTML')

# ========== CALLBACK VERIFIKASI ==========
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
        chat_target1 = CHANNEL_USERNAME if CHANNEL_USERNAME.startswith('@') else f"@{CHANNEL_USERNAME}"
        chat_target2 = CHANNEL_MONITOR if CHANNEL_MONITOR.startswith('@') else f"@{CHANNEL_MONITOR}"
        
        member1 = bot.get_chat_member(chat_target1, user_id)
        member2 = bot.get_chat_member(chat_target2, user_id)
        
        valid_status = ['member', 'administrator', 'creator']
        
        if member1.status in valid_status and member2.status in valid_status:
            db.set_verified(user_id)
            user = db.get_user(user_id)
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_photo(call.message.chat.id, photo=PHOTO_URL, caption=get_caption_main_menu(user), reply_markup=generate_main_markup(), parse_mode='HTML')
            bot.answer_callback_query(call.id, "⚡ Verifikasi Berhasil!")
        else:
            bot.answer_callback_query(call.id, "❌ Kamu belum join ke SEMUA channel!", show_alert=True)
    except Exception as e:
        bot.answer_callback_query(call.id, "⚠️ Gagal ngecek channel! Pastikan Bot udah jadi ADMIN di kedua channel.", show_alert=True)

# ========== BACK TO MAIN ==========
@bot.callback_query_handler(func=lambda call: call.data == 'back_to_main')
def back_to_main(call):
    user_id = call.from_user.id
    user = db.get_user(user_id)
    if not user:
        bot.answer_callback_query(call.id, "User tidak ditemukan. Gunakan /start")
        return

    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_caption(caption=get_caption_main_menu(user), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=generate_main_markup(), parse_mode='HTML')
    except:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_photo(call.message.chat.id, photo=PHOTO_URL, caption=get_caption_main_menu(user), reply_markup=generate_main_markup(), parse_mode='HTML')

# ========== GENERATE NAMA (DENGAN CEK MAINTENANCE) ==========
@bot.callback_query_handler(func=lambda call: call.data == 'generate')
def generate_name(call):
    # Cek Maintenance
    if db.is_maintenance() and call.from_user.id not in ADMIN_ID:
        bot.answer_callback_query(call.id, "🛠️ Setor Gmail sedang MAINTENANCE / TUTUP oleh Admin!", show_alert=True)
        return

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
3. Klik tombol <b>SETOR GMAIL</b> untuk mengirimkan.</blockquote>
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

# ========== SALDO, RULES, REFERRAL, RANKING ==========
@bot.callback_query_handler(func=lambda call: call.data == 'balance')
def balance(call):
    user = db.get_user(call.from_user.id)
    bot.answer_callback_query(call.id)
    if user:
        text = f"<blockquote><b>💰 ɪɴꜰᴏ ꜱᴀʟᴅᴏ & ʙᴀʟᴀɴᴄᴇ</b>\n\n💵 <b>Saldo Aktif:</b> <code>{format_rupiah(user[6])}</code>\n📦 <b>Total Setor:</b> <code>{user[7]} Akun</code>\n💸 <b>Total WD:</b> <code>{format_rupiah(user[8])}</code>\n\n📌 <i>Min WD: {format_rupiah(MIN_WITHDRAW)}</i></blockquote>"
        try:
            bot.edit_message_caption(caption=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=generate_back_markup(), parse_mode='HTML')
        except:
            bot.edit_message_text(text=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=generate_back_markup(), parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == 'rules')
def rules(call):
    bot.answer_callback_query(call.id)
    text = f"<blockquote><b>📜 ʀᴜʟᴇꜱ & ꜱʏᴀʀᴀᴛ ꜱᴇᴛᴏʀ ɢᴍᴀɪʟ</b>\n\n1️⃣ Akun Fresh\n2️⃣ Wajib nama generate bot\n3️⃣ Umur 18+ (Tahun &lt;= 2005)\n4️⃣ Password: <code>{REQUIRED_PASSWORD}</code>\n5️⃣ No HP / Email Pemulihan dilarang!</blockquote>"
    try:
        bot.edit_message_caption(caption=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=generate_back_markup(), parse_mode='HTML')
    except:
        bot.edit_message_text(text=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=generate_back_markup(), parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == 'referral')
def referral(call):
    user_id = call.from_user.id
    user = db.get_user(user_id)
    bot.answer_callback_query(call.id)
    if user:
        ref_code = user[4] if user[4] else "ERR"
        link = f"https://t.me/{BOT_USERNAME}?start={ref_code}"
        text = f"<blockquote><b>🔗 ᴘʀᴏɢʀᴀᴍ ʀᴇꜰᴇʀʀᴀʟ</b>\n\n🔑 <b>Kode Reff:</b> <code>{ref_code}</code>\n👥 <b>Total Reff:</b> <code>{db.count_referrals(user_id)} Orang</code>\n💰 <b>Komisi:</b> <code>{format_rupiah(REFERRAL_BONUS)} / User</code>\n\n<b>📤 Link Undangan:</b>\n<code>{link}</code></blockquote>"
        try:
            bot.edit_message_caption(caption=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=generate_back_markup(), parse_mode='HTML')
        except:
            bot.edit_message_text(text=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=generate_back_markup(), parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == 'ranking')
def ranking(call):
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🏆 ꜱᴇᴛᴏʀ ᴛᴇʀʙᴀɴʏᴀᴋ", callback_data="rank_setor"), types.InlineKeyboardButton("💰 ᴡᴅ ᴛᴇʀʙᴀɴʏᴀᴋ", callback_data="rank_wd"))
    markup.add(types.InlineKeyboardButton("🔙 ᴋᴇᴍʙᴀʟɪ", callback_data="back_to_main"))
    try:
        bot.edit_message_caption(caption="<blockquote><b>📊 ᴘɪʟɪʜ ᴋᴀᴛᴇɢᴏʀɪ ᴘᴇʀɪɴɢᴋᴀᴛ:</b></blockquote>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
    except:
        bot.edit_message_text(text="<blockquote><b>📊 ᴘɪʟɪʜ ᴋᴀᴛᴇɢᴏʀɪ ᴘᴇʀɪɴɢᴋᴀᴛ:</b></blockquote>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('rank_'))
def show_ranking(call):
    tipe = call.data.split('_')[1]
    data = db.get_ranking(tipe)
    bot.answer_callback_query(call.id)
    text = f"<blockquote><b>🏆 ᴘᴇʀɪɴɢᴋᴀᴛ TOP 10 ({'SETOR' if tipe == 'setor' else 'WITHDRAW'})</b>\n\n"
    if data:
        for i, row in enumerate(data, 1):
            medal = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"<b>{i}.</b>"
            val = f"{row[1]} Akun" if tipe == 'setor' else format_rupiah(row[1])
            text += f"{medal} @{row[0] or 'User'} — <code>{val}</code>\n"
    else:
        text += "<i>Belum ada data.</i>"
    text += "</blockquote>"
    try:
        bot.edit_message_caption(caption=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=generate_back_markup(), parse_mode='HTML')
    except:
        bot.edit_message_text(text=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=generate_back_markup(), parse_mode='HTML')

# ========== SETOR GMAIL (DENGAN CEK MAINTENANCE) ==========
@bot.callback_query_handler(func=lambda call: call.data == 'setor')
def setor_gmail(call):
    # Cek Maintenance
    if db.is_maintenance() and call.from_user.id not in ADMIN_ID:
        bot.answer_callback_query(call.id, "🛠️ Setor Gmail sedang MAINTENANCE / TUTUP oleh Admin!", show_alert=True)
        return

    user_id = call.from_user.id
    generated = db.get_generated_prefix(user_id)
    if not generated:
        bot.answer_callback_query(call.id, "❌ Kamu belum generate nama!", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, f"<blockquote><b>📧 ꜰᴏʀᴍᴀᴛ ꜱᴇᴛᴏʀ ɢᴍᴀɪʟ</b>\n\nKirim format: <code>email|password</code>\nContoh: <code>{generated}@gmail.com|{REQUIRED_PASSWORD}</code></blockquote>", parse_mode='HTML')
    bot.register_next_step_handler(msg, proses_setor)

def proses_setor(message):
    user_id = message.from_user.id
    if db.is_maintenance() and user_id not in ADMIN_ID:
        bot.reply_to(message, "<blockquote>🛠️ <b>SETORAN GMAIL SEDANG MAINTENANCE / TUTUP!</b></blockquote>", parse_mode='HTML')
        return

    try:
        email, password = message.text.split('|')
        email_prefix = email.split('@')[0]
        generated_prefix = db.get_generated_prefix(user_id)

        if not validate_email(email) or not generated_prefix or email_prefix != generated_prefix or password != REQUIRED_PASSWORD:
            bot.reply_to(message, "<blockquote>❌ <b>FORMAT / NAMA / PASSWORD SALAH!</b></blockquote>", parse_mode='HTML')
            return

        if not check_gmail_valid(email, password):
            bot.reply_to(message, "<blockquote>❌ <b>LOGIN GAGAL!</b> Gmail tidak aktif.</blockquote>", parse_mode='HTML')
            return

        gmail_id = db.add_gmail(email, password, user_id)
        db.clear_generated_prefix(user_id)

        admin_text = f"<blockquote><b>📥 ꜱᴇᴛᴏʀᴀɴ ɢᴍᴀɪʟ (PENDING)</b>\n\n👤 <b>User:</b> @{message.from_user.username or message.from_user.id}\n📧 <b>Email:</b> <code>{email}</code>\n🔑 <b>Password:</b> <code>{password}</code></blockquote>"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ ᴛᴇʀɪᴍᴀ", callback_data=f"approve_gmail_{gmail_id}"), types.InlineKeyboardButton("❌ ᴛᴏʟᴀᴋ", callback_data=f"reject_gmail_{gmail_id}"))

        for admin in ADMIN_ID:
            try: bot.send_message(admin, admin_text, reply_markup=markup, parse_mode='HTML')
            except: pass

        bot.reply_to(message, f"<blockquote>✅ <b>GMAIL DIKIRIM!</b>\n⏳ <i>Sedang diverifikasi Admin.</i></blockquote>", parse_mode='HTML')
    except:
        bot.reply_to(message, "<blockquote>❌ Gunakan format: <code>email|password</code></blockquote>", parse_mode='HTML')

# ========== WITHDRAW + AUTO POST MONITOR ==========
@bot.callback_query_handler(func=lambda call: call.data == 'withdraw')
def withdraw(call):
    user = db.get_user(call.from_user.id)
    if not user: return
    if user[6] < MIN_WITHDRAW:
        bot.answer_callback_query(call.id, f"❌ Saldo kurang! Min WD {format_rupiah(MIN_WITHDRAW)}", show_alert=True)
        return

    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, f"<blockquote><b>💸 ꜰᴏʀᴍᴀᴛ ᴡɪᴛʜᴅʀᴀᴡ (ᴅᴀɴᴀ)</b>\n\nKirim format: <code>nomor|jumlah</code>\nContoh: <code>081234567890|10000</code>\n💰 <b>Saldo:</b> <code>{format_rupiah(user[6])}</code></blockquote>", parse_mode='HTML')
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

        # 1. Kirim Notif ke Admin
        admin_text = f"<blockquote><b>💸 ᴘᴇɴᴀʀɪᴋᴀɴ (PENDING)</b>\n👤 <b>User:</b> @{message.from_user.username or message.from_user.id}\n📱 <b>No DANA:</b> <code>{dana_number}</code>\n💰 <b>Nominal:</b> <code>{format_rupiah(amount)}</code></blockquote>"
        for admin in ADMIN_ID:
            try: bot.send_message(admin, admin_text, parse_mode='HTML')
            except: pass

        # 2. Kirim Auto-Post ke Channel Monitor
        waktu_sekarang = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        masked_nomor = mask_dana(dana_number)
        
        monitor_text = f"""
<blockquote><b>💸 REQUEST WITHDRAW BARU</b>

👤 <b>User:</b> @{message.from_user.username or message.from_user.id}
🏦 <b>Metode:</b> DANA
📱 <b>Nomor:</b> <code>{masked_nomor}</code>
💰 <b>Nominal:</b> <code>{format_rupiah(amount)}</code>
🕒 <b>Waktu:</b> <code>{waktu_sekarang} WIB</code>

⏳ <i>Status: Sedang dalam antrean pencairan...</i></blockquote>
        """
        try:
            bot.send_message(CHANNEL_MONITOR, monitor_text, parse_mode='HTML')
        except Exception as e:
            print(f"Gagal kirim ke monitor: {e}")

        bot.reply_to(message, f"<blockquote>✅ <b>WD SUCCESS!</b>\n💸 Rp <code>{amount:,}</code>\n📱 No DANA: <code>{dana_number}</code>\n\n<i>Cek antrean di channel bukti TF!</i></blockquote>", parse_mode='HTML')
    except:
        bot.reply_to(message, "❌ Format salah: <code>nomor|jumlah</code>", parse_mode='HTML')

# ========== ADMIN ACTIONS ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_gmail_') or call.data.startswith('reject_gmail_'))
def admin_approve_gmail(call):
    if call.from_user.id not in ADMIN_ID:
        return bot.answer_callback_query(call.id, "Akses ditolak.", show_alert=True)

    data_parts = call.data.split('_')
    action, gmail_id = data_parts[0], int(data_parts[2])
    status = 'verified' if action == 'approve' else 'rejected'
    gmail = db.approve_gmail(gmail_id, call.from_user.id, status)
    
    if not gmail: return bot.answer_callback_query(call.id, "Gmail tidak ada.", show_alert=True)

    user_id = gmail[3]
    if action == 'approve':
        user = db.get_user(user_id)
        msg = f"<blockquote>✅ <b>ɢᴍᴀɪʟ ᴅɪᴛᴇʀɪᴍᴀ!</b>\n📧 <code>{gmail[1]}</code>\n💰 Bonus: <b>+{format_rupiah(PRICE_PER_EMAIL)}</b>\n💳 Saldo: <code>{format_rupiah(user[6])}</code></blockquote>"
        bot.answer_callback_query(call.id, "✅ ACC!")
    else:
        msg = f"<blockquote>❌ <b>ɢᴍᴀɪʟ ᴅɪᴛᴏʟᴀᴋ</b>\n📧 <code>{gmail[1]}</code></blockquote>"
        bot.answer_callback_query(call.id, "❌ Tolak.")

    try: bot.send_message(user_id, msg, parse_mode='HTML')
    except: pass
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass

# ========== ADMIN PANEL & MAINTENANCE SYSTEM ==========
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_ID: return
    status_mt = "🔴 TUTUP" if db.is_maintenance() else "🟢 BUKA"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📥 ɢᴍᴀɪʟ ᴘᴇɴᴅɪɴɢ", callback_data="admin_gmail"),
        types.InlineKeyboardButton("💸 ᴡᴅ ᴘᴇɴᴅɪɴɢ", callback_data="admin_wd"),
        types.InlineKeyboardButton("📊 ꜱᴛᴀᴛɪꜱᴛɪᴋ", callback_data="admin_stats"),
        types.InlineKeyboardButton("📥 ᴅᴏᴡɴʟᴏᴀᴅ ᴀᴋᴜɴ", callback_data="admin_download"),
        types.InlineKeyboardButton("🛠️ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ", callback_data="admin_mt_menu")
    )
    bot.send_message(message.chat.id, f"<blockquote><b>🛡️ ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ</b>\n⚙️ Status Setor: <b>{status_mt}</b></blockquote>", reply_markup=markup, parse_mode='HTML')

# Submenu Maintenance
@bot.callback_query_handler(func=lambda call: call.data == 'admin_mt_menu')
def admin_mt_menu(call):
    if call.from_user.id not in ADMIN_ID: return
    status_mt = "🔴 TUTUP (Maintenance)" if db.is_maintenance() else "🟢 BUKA (Normal)"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_buka = types.InlineKeyboardButton("🟢 ʙᴜᴋᴀ ꜱᴇᴛᴏʀ", callback_data="set_mt_0")
    btn_tutup = types.InlineKeyboardButton("🔴 ᴛᴜᴛᴜᴘ ꜱᴇᴛᴏʀ", callback_data="set_mt_1")
    btn_back = types.InlineKeyboardButton("🔙 ᴋᴇᴍʙᴀʟɪ", callback_data="back_to_admin")
    markup.add(btn_buka, btn_tutup)
    markup.add(btn_back)

    bot.answer_callback_query(call.id)
    bot.edit_message_text(f"<blockquote><b>🛠️ 𝖯𝖤𝖭𝖦𝖴𝖳𝖴𝖱𝖠𝖭 𝖬𝖠𝖨𝖭𝖳𝖤𝖭𝖠𝖭𝖢𝖤</b>\n\nStatus Setoran Gmail Sekarang: <b>{status_mt}</b>\n\nPilih opsi di bawah untuk mengubah status:</blockquote>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

# Handler Set Buka/Tutup Maintenance
@bot.callback_query_handler(func=lambda call: call.data.startswith('set_mt_'))
def set_maintenance_action(call):
    if call.from_user.id not in ADMIN_ID: return
    val = call.data.split('_')[2]
    db.set_maintenance(val)
    
    if val == '1':
        bot.answer_callback_query(call.id, "🔴 Setoran BERHASIL DITUTUP!", show_alert=True)
    else:
        bot.answer_callback_query(call.id, "🟢 Setoran BERHASIL DIBUKA!", show_alert=True)
        
    admin_mt_menu(call) # Refresh tampilan menu maintenance

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_admin')
def back_to_admin(call):
    if call.from_user.id not in ADMIN_ID: return
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    admin_panel(call.message)

@bot.callback_query_handler(func=lambda call: call.data in ['admin_gmail', 'admin_wd', 'admin_stats', 'admin_download'])
def admin_menu(call):
    if call.from_user.id not in ADMIN_ID: return
    bot.answer_callback_query(call.id)
    
    if call.data == 'admin_gmail':
        pending = db.get_pending_gmails()
        text = f"<blockquote><b>📥 GMAIL PENDING ({len(pending)})</b>\n" + "".join([f"• ID <code>{r[0]}</code> | <code>{r[1]}</code>\n" for r in pending[:10]]) + "</blockquote>" if pending else "KOSONG"
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')
        
    elif call.data == 'admin_wd':
        pending = db.get_pending_withdraws()
        text = f"<blockquote><b>💸 WD PENDING ({len(pending)})</b>\n" + "".join([f"• ID <code>{r[0]}</code> | Rp <code>{r[2]:,}</code> | <code>{r[3]}</code>\n" for r in pending[:10]]) + "</blockquote>" if pending else "KOSONG"
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')
        
    elif call.data == 'admin_stats':
        tot_user, tot_setor, tot_bal = db.get_stats()
        text = f"<blockquote><b>📊 ꜱᴛᴀᴛɪꜱᴛɪᴋ ʙᴏᴛ</b>\n👥 <b>User:</b> <code>{tot_user}</code>\n📦 <b>Akun:</b> <code>{tot_setor}</code>\n💳 <b>Saldo:</b> <code>{format_rupiah(tot_bal)}</code></blockquote>"
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')

    elif call.data == 'admin_download':
        accounts = db.get_and_clear_verified_gmails()
        if not accounts: return bot.send_message(call.message.chat.id, "Kosong bro.")
        content = "\n".join([f"{e}:{p}" for e, p in accounts])
        file_obj = io.BytesIO(content.encode('utf-8'))
        file_obj.name = "akun_verified.txt"
        bot.send_document(call.message.chat.id, file_obj, caption=f"Total: {len(accounts)} Akun")

if __name__ == '__main__':
    print("🚀 BOT NYALA BRO!")
    bot.polling(none_stop=True)
