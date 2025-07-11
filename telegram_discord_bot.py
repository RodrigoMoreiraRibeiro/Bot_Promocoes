import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

async def forward_to_discord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text or "[Sem texto]"
    payload = {"content": msg}
    requests.post(DISCORD_WEBHOOK_URL, json=payload)
    print(f"[Telegram] Mensagem enviada para Discord: {msg[:50]}")

if __name__ == "__main__":
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = ApplicationBuilder().token(bot_token).build()
    app.add_handler(MessageHandler(filters.TEXT, forward_to_discord))
    app.run_polling()
