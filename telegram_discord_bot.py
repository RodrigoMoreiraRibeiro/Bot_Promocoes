import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# Configuração básica de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lê as variáveis de ambiente
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
if not DISCORD_WEBHOOK_URL:
    logger.error("🚨 Variável DISCORD_WEBHOOK_URL não configurada!")
    exit(1)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logger.error("🚨 Variável TELEGRAM_BOT_TOKEN não configurada!")
    exit(1)

async def forward_to_discord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        text = message.text or message.caption or ""
        logger.info(f"[Telegram] Mensagem recebida: {text[:50]}...")

        # Monta o payload para o embed do Discord
        embed = {
            "title": "📦 Nova Promoção Detectada",
            "description": text,
            "color": 0x00ff00,
            "footer": {
                "text": "Bot de Promoções",
            }
        }

        # Se tiver foto (ou mídia que tenha thumbnail), pega a última foto
        if message.photo:
            photo_file = await message.photo[-1].get_file()
            photo_url = photo_file.file_path
            embed["image"] = {"url": photo_url}

        payload = {
            "embeds": [embed]
        }

        # Envia para o Discord via webhook
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if response.status_code not in (200, 204):
            logger.error(f"Erro ao enviar para Discord: {response.status_code} - {response.text}")

    except Exception as e:
        logger.exception(f"Erro no forward_to_discord: {e}")

async def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Escuta mensagens de texto e fotos (você pode expandir filtros se quiser)
    handler = MessageHandler(filters.TEXT | filters.PHOTO, forward_to_discord)
    app.add_handler(handler)

    logger.info("🤖 Bot Telegram → Discord iniciado.")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
