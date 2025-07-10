import requests
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

async def forward_to_discord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text

    if msg:
        print(f"[Telegram] Nova mensagem recebida: {msg}")

        # 1) Mensagem com embed customizado (sem descrição para evitar link repetido)
        embed_data = {
            "embeds": [
                {
                    "title": "📦 Nova Promoção Detectada",
                    "color": 0x00ff00,  # verde
                    "footer": {
                        "text": "Bot de Promoções",
                    }
                }
            ]
        }

        # Envia a mensagem com embed
        response_embed = requests.post(DISCORD_WEBHOOK_URL, json=embed_data)
        if response_embed.status_code == 204:
            print("[Discord] Embed enviado com sucesso!")
        else:
            print(f"[Discord] Erro ao enviar embed: {response_embed.status_code} - {response_embed.text}")

        # 2) Mensagem com o link puro no content para gerar preview automático
        content_data = {
            "content": msg
        }

        # Envia a mensagem com o link puro
        response_content = requests.post(DISCORD_WEBHOOK_URL, json=content_data)
        if response_content.status_code == 204:
            print("[Discord] Conteúdo enviado com sucesso!")
        else:
            print(f"[Discord] Erro ao enviar conteúdo: {response_content.status_code} - {response_content.text}")

if __name__ == "__main__":
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    print("🤖 Bot Telegram → Discord iniciado.")
    app = ApplicationBuilder().token(bot_token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_to_discord))
    app.run_polling()
