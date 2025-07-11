import requests
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

async def forward_to_discord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Verifica se há mensagem
    if not update.message:
        print("[DEBUG] Nenhuma mensagem encontrada no update")
        return
    
    # Debug: Informações da mensagem
    print(f"[DEBUG] Tipo de mensagem: {type(update.message)}")
    print(f"[DEBUG] Message ID: {update.message.message_id}")
    print(f"[DEBUG] From: {update.message.from_user}")
    print(f"[DEBUG] Chat: {update.message.chat}")
    print(f"[DEBUG] É encaminhada: {bool(update.message.forward_origin)}")
    
    # Extrai o texto da mensagem
    msg = None
    
    # Verifica diferentes tipos de conteúdo
    if update.message.text:
        msg = update.message.text
        print(f"[DEBUG] Texto encontrado: {msg[:100]}")
    elif update.message.caption:
        msg = update.message.caption
        print(f"[DEBUG] Caption encontrada: {msg[:100]}")
    elif update.message.photo:
        msg = "[Foto]"
        print(f"[DEBUG] Foto detectada")
    elif update.message.document:
        msg = "[Documento]"
        print(f"[DEBUG] Documento detectado")
    elif update.message.video:
        msg = "[Vídeo]"
        print(f"[DEBUG] Vídeo detectado")
    else:
        msg = "[Mídia sem texto]"
        print(f"[DEBUG] Mídia sem texto detectada")
    
    # Informações sobre encaminhamento
    origem_info = ""
    if update.message.forward_origin:
        if hasattr(update.message.forward_origin, 'sender_user') and update.message.forward_origin.sender_user:
            user = update.message.forward_origin.sender_user
            origem_info = f"👤 Encaminhada de: {user.first_name} {user.last_name or ''}".strip()
        elif hasattr(update.message.forward_origin, 'chat') and update.message.forward_origin.chat:
            chat = update.message.forward_origin.chat
            origem_info = f"📢 Encaminhada de: {chat.title}"
        elif hasattr(update.message.forward_origin, 'sender_user_name') and update.message.forward_origin.sender_user_name:
            origem_info = f"👤 Encaminhada de: {update.message.forward_origin.sender_user_name}"
        else:
            origem_info = "📤 Mensagem encaminhada"
    else:
        origem_info = f"👤 Enviada por: {update.message.from_user.first_name} {update.message.from_user.last_name or ''}".strip()
    
    print(f"[DEBUG] Origem: {origem_info}")
    
    if msg:
        print(f"[Telegram] Nova mensagem recebida: {msg[:100]}")

        # 1) Mensagem com embed customizado
        embed_data = {
            "embeds": [
                {
                    "title": "🔥🔥 Nova Promoção Detectada 🔥🔥",
                    "description": f"**{origem_info}**\n\n{msg[:2000]}",  # Limite do Discord
                    "color": 0x00ff00,  # verde
                    "footer": {
                        "text": "Bot de Promoções",
                    },
                    "timestamp": update.message.date.isoformat()
                }
            ]
        }

        # Envia a mensagem com embed
        response_embed = requests.post(DISCORD_WEBHOOK_URL, json=embed_data)
        if response_embed.status_code == 204:
            print("[Discord] Embed enviado com sucesso!")
        else:
            print(f"[Discord] Erro ao enviar embed: {response_embed.status_code} - {response_embed.text}")

        # 2) Se a mensagem contém links, envia também o conteúdo puro para preview
        if "http" in msg.lower():
            content_data = {
                "content": msg
            }
            
            # Envia a mensagem com o link puro
            response_content = requests.post(DISCORD_WEBHOOK_URL, json=content_data)
            if response_content.status_code == 204:
                print("[Discord] Conteúdo enviado com sucesso!")
            else:
                print(f"[Discord] Erro ao enviar conteúdo: {response_content.status_code} - {response_content.text}")
    else:
        print("[DEBUG] Nenhum texto encontrado na mensagem")

if __name__ == "__main__":
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    print("🤖 Bot Telegram → Discord iniciado.")
    app = ApplicationBuilder().token(bot_token).build()
    
    # IMPORTANTE: Usar filters mais específicos para capturar TUDO
    # Combinando múltiplos filtros para garantir que capture tudo
    all_filters = (
        filters.TEXT |
        filters.PHOTO |
        filters.VIDEO |
        filters.DOCUMENT |
        filters.AUDIO |
        filters.VOICE |
        filters.FORWARDED
    )
    
    app.add_handler(MessageHandler(all_filters, forward_to_discord))
    
    print("🔍 Filtros configurados para capturar:")
    print("  - Mensagens de texto")
    print("  - Mensagens com mídia")
    print("  - Mensagens encaminhadas")
    print("  - Todos os tipos de update")
    
    app.run_polling()