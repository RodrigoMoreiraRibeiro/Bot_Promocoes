import os
import logging
import nest_asyncio
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# Aplica patch para permitir rodar asyncio em ambiente que já tem event loop
nest_asyncio.apply()

# Configura logging para ajudar no debug
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Pega as variáveis de ambiente (lembre de configurar os secrets no GitHub)
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]


async def forward_to_discord(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        msg = update.message
        if not msg:
            return

        # Exemplo simples: enviar texto para o Discord via webhook
        import aiohttp

        content = msg.text or msg.caption or ""
        # Você pode montar um JSON com embeds, imagens etc aqui
        payload = {"content": f"📢 Nova mensagem do Telegram:\n{content}"}

        async with aiohttp.ClientSession() as session:
            async with session.post(DISCORD_WEBHOOK_URL, json=payload) as resp:
                if resp.status != 204 and resp.status != 200:
                    logger.error(f"Erro ao enviar mensagem para Discord: {resp.status}")
                else:
                    logger.info("Mensagem enviada para o Discord com sucesso!")

    except Exception as e:
        logger.error(f"Erro em forward_to_discord: {e}", exc_info=True)


async def main():
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    # Adiciona handler para mensagens de texto, fotos com legenda, documentos etc
    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.PHOTO | filters.DOCUMENT | filters.VIDEO,
            forward_to_discord,
        )
    )

    logger.info("🤖 Bot Telegram → Discord iniciado.")
    await app.run_polling()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
