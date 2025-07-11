import requests
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

async def forward_to_discord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        print("[DEBUG] Nenhuma mensagem encontrada no update")
        return

    # Debug info
    print(f"[DEBUG] Message ID: {message.message_id}")
    print(f"[DEBUG] From: {message.from_user}")
    print(f"[DEBUG] Chat: {message.chat}")
    print(f"[DEBUG] É encaminhada: {bool(message.forward_date)}")

    # Extrair texto ou indicar tipo da mídia
    if message.text:
        msg = message.text
    elif message.caption:
        msg = message.caption
    elif message.photo:
        msg = "[Foto]"
    elif message.document:
        msg = "[Documento]"
    elif message.video:
        msg = "[Vídeo]"
    elif message.audio:
        msg = "[Áudio]"
    elif message.voice:
        msg = "[Mensagem de voz]"
    else:
        msg = "[Mídia sem texto]"

    # Origem da mensagem (encaminhada ou enviada diretamente)
    if message.forward_date:
        origem_info = "📤 Mensagem encaminhada"
        if message.forward_from:
            origem_info = f"👤 Encaminhada de: {message.forward_from.first_name} {message.forward_from.last_name or ''}".strip()
        elif message.forward_from_chat:
            origem_info = f"📢 Encaminhada de: {message.forward_from_chat.title}"
    else:
        origem_info = f"👤 Enviada por: {message.from_user.first_name} {message.from_user.last_name or ''}".strip()

    print(f"[DEBUG] Origem: {origem_info}")

    # Enviar para Discord via webhook
    if msg:
        print(f"[Telegram] Nova mensagem recebida: {msg[:100]}")

        embed_data = {
            "embeds": [
                {
                    "title": "🔥🔥 Nova Promoção Detectada 🔥🔥",
                    "description": f"**{origem_info}**\n\n{msg[:2000]}",
                    "color": 0x00ff00,
                    "footer": {"text": "Bot de Promoções"},
                    "timestamp": message.date.isoformat()
                }
            ]
        }

        response_embed = requests.post(DISCORD_WEBHOOK_URL, json=embed_data)
        if response_embed.status_code == 204:
            print("[Discord] Embed enviado com sucesso!")
        else:
            print(f"[Discord] Erro ao enviar embed: {response_embed.status_code} - {response_embed.text}")

        # Se tem link, enviar texto puro para preview
        if "http" in msg.lower():
            content_data = {"content": msg}
            response_content = requests.post(DISCORD_WEBHOOK_URL, json=content_data)
            if response_content.status_code == 204:
                print("[Discord] Conteúdo enviado com sucesso!")
            else:
                print(f"[Discord] Erro ao enviar conteúdo: {response_content.status_code} - {response_content.text}")

if __name__ == "__main__":
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    print("🤖 Bot Telegram → Discord iniciado.")
    app = ApplicationBuilder().token(bot_token).build()

    all_filters = (
        filters.Text
        | filters.Caption
        | filters._Photo
        | filters._Video
        | filters.Document
        | filters.Audio
        | filters.Voice
        | filters.Forwarded
    )


    app.add_handler(MessageHandler(all_filters, forward_to_discord))

    print("🔍 Filtros configurados para capturar tudo.")
    app.run_polling()
