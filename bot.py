import os, re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters, ConversationHandler
from data import SERVICES, BANK_PLATFORM

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

ASK_TANGGAL, ASK_DURASI, ASK_NAMA, ASK_KONFIRM, ASK_BAYAR, ASK_BUKTI = range(6)

def get_harga(detail):
    m = re.search(r"Rp\s?([\d\.]+)", detail)
    if m: return int(m.group(1).replace(".",""))
    return 350000

def main_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton(v["title"], callback_data=f"cat:{k}")] for k,v in SERVICES.items()])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("<b>Visit Samosir 🏝️</b>\nPesan layanan + bayar langsung via bot. Komisi otomatis.", reply_markup=main_menu(), parse_mode=ParseMode.HTML)

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    if d == "home":
        context.user_data.clear()
        await q.edit_message_text("Pilih layanan:", reply_markup=main_menu())
        return
    if d.startswith("cat:"):
        cat = d.split(":")[1]
        btns = [[InlineKeyboardButton(it["name"], callback_data=f"view:{cat}:{i}")] for i,it in enumerate(SERVICES[cat]["items"])]
        btns.append([InlineKeyboardButton("⬅️ Menu", callback_data="home")])
        await q.edit_message_text(f"<b>{SERVICES[cat]['title']}</b>\n{SERVICES[cat]['description']}", reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.HTML)
    if d.startswith("view:"):
        _, cat, idx = d.split(":")
        item = SERVICES[cat]["items"][int(idx)]
        context.user_data.update({"cat": cat, "item": item, "harga": get_harga(item["detail"])})
        txt = f"<b>{item['name']}</b>\n{item['detail']}\nHarga: Rp {context.user_data['harga']:,}"
        btns = [[InlineKeyboardButton("🛒 Pesan Sekarang", callback_data="order:start")],[InlineKeyboardButton("⬅️ Kembali", callback_data=f"cat:{cat}")]]
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.HTML)
    if d == "order:start":
        await q.edit_message_text("📅 Tanggal pakai? (contoh: 5 Nov 2026)")
        return ASK_TANGGAL

async def ask_tanggal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["tanggal"] = update.message.text
    await update.message.reply_text("⏱️ Durasi berapa hari? (ketik angka, misal: 2)")
    return ASK_DURASI

async def ask_durasi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: dur = int(re.findall(r"\d+", update.message.text)[0])
    except: dur = 1
    context.user_data["durasi"] = dur
    context.user_data["total"] = context.user_data["harga"] * dur
    await update.message.reply_text(f"Total {dur} hari = Rp {context.user_data['total']:,}\n👤 Atas nama siapa?")
    return ASK_NAMA

async def ask_nama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nama"] = update.message.text
    total = context.user_data["total"]
    komisi = context.user_data["item"].get("komisi", 0.15)
    txt = (
        f"<b>Konfirmasi</b>\n"
        f"{context.user_data['item']['name']}\n"
        f"Tgl: {context.user_data['tanggal']} | {context.user_data['durasi']} hari\n"
        f"Nama: {context.user_data['nama']}\n"
        f"Total Bayar: Rp {total:,}\n\n"
        f"Lanjut bayar ke platform?"
    )
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Lanjut Bayar", callback_data="confirm:yes")]]), parse_mode=ParseMode.HTML)
    return ASK_KONFIRM

async def ask_konfirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    txt = f"💳 Transfer ke Platform:\n{BANK_PLATFORM}\n\nTotal: <b>Rp {context.user_data['total']:,}</b>"
    btns = [[InlineKeyboardButton("✅ Sudah Transfer", callback_data="bayar:transfer")],[InlineKeyboardButton("📲 QRIS", callback_data="bayar:qris")],[InlineKeyboardButton("💵 COD", callback_data="bayar:cod")]]
    await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.HTML)
    return ASK_BAYAR

async def ask_bayar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    metode = q.data.split(":")[1].upper()
    context.user_data["metode"] = metode
    if metode == "COD":
        await q.edit_message_text("✅ Pesanan COD dicatat. Admin akan hubungi.")
        await kirim_admin(update, context, bukti=False)
        context.user_data.clear()
        return ConversationHandler.END
    else:
        await q.edit_message_text(f"Kamu pilih {metode}. Upload bukti transfer (kirim FOTO):")
        return ASK_BUKTI

async def ask_bukti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.photo[-1].file_id if update.message.photo else None
    context.user_data["bukti"] = file_id
    # Balas ke user
    await update.message.reply_text(
        f"✅ Bukti diterima!\nPesanan lunas. Kontak supir/pemilik: {context.user_data['item']['contact']}\nAdmin akan teruskan pembayaran ke pemilik setelah potong komisi.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menu", callback_data="home")]])
    )
    await kirim_admin(update, context, bukti=True)
    context.user_data.clear()
    return ConversationHandler.END

async def kirim_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, bukti=False):
    item = context.user_data["item"]
    total = context.user_data["total"]
    persen = item.get("komisi", 0.15)
    komisi_rp = int(total * persen)
    bersih = total - komisi_rp
    caption = (
        f"🔥 <b>ORDER LUNAS - {context.user_data['metode']}</b>\n\n"
        f"Item: {item['name']}\n"
        f"Tgl: {context.user_data['tanggal']} | {context.user_data['durasi']} hari\n"
        f"Nama: {context.user_data['nama']} | @{update.effective_user.username}\n\n"
        f"Total User: Rp {total:,}\n"
        f"Komisi {int(persen*100)}%: Rp {komisi_rp:,}\n"
        f"<b>Hak Pemilik: Rp {bersih:,}</b>\n"
        f"Bank Pemilik: {item.get('bank_pemilik','-')}\n\n"
        f"ACTION: Transfer Rp {bersih:,} ke pemilik!"
    )
    if ADMIN_ID:
        try:
            if bukti and context.user_data.get("bukti"):
                await context.bot.send_photo(chat_id=ADMIN_ID, photo=context.user_data["bukti"], caption=caption, parse_mode=ParseMode.HTML)
            else:
                await context.bot.send_message(chat_id=ADMIN_ID, text=caption, parse_mode=ParseMode.HTML)
        except Exception as e:
            print(e)

def main():
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(menu_handler, pattern="^order:start")],
        states={
            ASK_TANGGAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_tanggal)],
            ASK_DURASI: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_durasi)],
            ASK_NAMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_nama)],
            ASK_KONFIRM: [CallbackQueryHandler(ask_konfirm, pattern="^confirm:")],
            ASK_BAYAR: [CallbackQueryHandler(ask_bayar, pattern="^bayar:")],
            ASK_BUKTI: [MessageHandler(filters.PHOTO, ask_bukti)],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_handler, pattern="^(home|cat:|view:)"))
    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()
