import requests
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

async def forward_to_discord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    if msg:
        print(f"[Telegram] Nova mensagem recebida: {msg}")
        data = {
            "content": f"🤑 Nova Promoção na área!:\n{msg}"
        }

        response = requests.post(DISCORD_WEBHOOK_URL, json=data)

        if response.status_code == 204:
            print("[Discord] Mensagem enviada com sucesso!")
        else:
            print(f"[Discord] Erro ao enviar mensagem: {response.status_code} - {response.text}")

if __name__ == "__main__":
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    print("🤖 Bot Telegram → Discord iniciado.")
    app = ApplicationBuilder().token(bot_token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_to_discord))
    app.run_polling()
