# -*- coding: utf-8 -*-
"""
Visit Samosir - Telegram Bot
Menyediakan jasa layanan angkutan, penginapan, rental drone,
rental musik tradisional Batak, catering, dan rental mobil.
"""

import logging
import os

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from data import SERVICES

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CONTACT = os.getenv("ADMIN_CONTACT", "-")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("visit_samosir_bot")


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Keyboard menu utama."""
    buttons = [
        [InlineKeyboardButton(SERVICES["angkutan"]["title"], callback_data="svc:angkutan")],
        [InlineKeyboardButton(SERVICES["penginapan"]["title"], callback_data="svc:penginapan")],
        [InlineKeyboardButton(SERVICES["drone"]["title"], callback_data="svc:drone")],
        [InlineKeyboardButton(SERVICES["musik"]["title"], callback_data="svc:musik")],
        [InlineKeyboardButton(SERVICES["catering"]["title"], callback_data="svc:catering")],
        [InlineKeyboardButton(SERVICES["mobil"]["title"], callback_data="svc:mobil")],
    ]
    return InlineKeyboardMarkup(buttons)


def back_keyboard() -> InlineKeyboardMarkup:
    """Tombol kembali ke menu utama."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data="menu")]]
    )


def format_service(key: str) -> str:
    """Membentuk teks detail untuk satu kategori layanan."""
    service = SERVICES[key]
    lines = [f"<b>{service['title']}</b>", "", service["description"], ""]
    for idx, item in enumerate(service["items"], start=1):
        lines.append(f"<b>{idx}. {item['name']}</b>")
        lines.append(item["detail"])
        lines.append(f"📞 Kontak: {item['contact']}")
        lines.append("")
    return "\n".join(lines).strip()


WELCOME_TEXT = (
    "<b>Selamat datang di Visit Samosir! 🌄</b>\n\n"
    "Temukan berbagai layanan wisata di Pulau Samosir, "
    "Danau Toba.\n\n"
    "Silakan pilih layanan yang Anda butuhkan:"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /start."""
    await update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.HTML,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /help."""
    text = (
        "<b>Panduan Visit Samosir</b>\n\n"
        "/start - Tampilkan menu utama\n"
        "/menu - Tampilkan menu utama\n"
        "/help - Tampilkan bantuan\n"
        "/kontak - Hubungi admin\n\n"
        "Pilih layanan melalui tombol yang tersedia."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def kontak(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /kontak."""
    await update.message.reply_text(
        f"Hubungi admin kami: {ADMIN_CONTACT}"
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani semua klik tombol inline."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu":
        await query.edit_message_text(
            WELCOME_TEXT,
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        return

    if data.startswith("svc:"):
        key = data.split(":", 1)[1]
        if key in SERVICES:
            await query.edit_message_text(
                format_service(key),
                reply_markup=back_keyboard(),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mencatat error agar mudah di-debug di log hosting."""
    logger.error("Terjadi error: %s", context.error, exc_info=context.error)


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN belum diatur. Isi di file .env atau di environment variable."
        )

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("kontak", kontak))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)

    logger.info("Visit Samosir Bot berjalan...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
