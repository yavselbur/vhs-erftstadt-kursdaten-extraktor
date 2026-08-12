# -*- coding: utf-8 -*-
"""
VHS Erftstadt Telegram Bot
-------------------------------
Bu program, Telegram üzerinden gelen mesajları RAG sistemimize (rag_core.py)
gönderir ve cevabı kullanıcıya geri yollar.

Çalıştırmadan önce:
1. .env dosyasında TELEGRAM_BOT_TOKEN tanımlı olmalı.
2. Ollama arka planda çalışıyor olmalı.
"""

import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

from rag_core import cevap_uret

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN bulunamadı! '.env' dosyasını oluşturduğundan emin ol."
    )


async def baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı /start yazdığında çalışır."""
    await update.message.reply_text(
        "Merhaba! Ben VHS Erftstadt kurs asistanıyım. 🎓\n\n"
        "Türkçe, Deutsch veya English - hangi dilde isterseniz o dilde "
        "sorabilirsiniz. Örneğin:\n"
        "- 'İspanyolca kursu var mı?'\n"
        "- 'Gibt es Yoga-Kurse?'\n"
        "- 'Any beginner Excel courses?'"
    )


async def mesaj_isle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcıdan normal bir metin mesajı geldiğinde çalışır."""
    soru = update.message.text

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        cevap = cevap_uret(soru)
    except Exception as e:
        cevap = f"Üzgünüm, bir hata oluştu: {e}"

    await update.message.reply_text(cevap)


if __name__ == "__main__":
    print("Bot başlatılıyor...")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", baslat))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj_isle))

    print("Bot çalışıyor. Telegram'da botuna mesaj yazabilirsin. Durdurmak için Ctrl+C.")
    app.run_polling()
