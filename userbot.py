import os
from telethon import TelegramClient, events, errors
import asyncio
from telethon.tl.functions.channels import JoinChannelRequest

api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
grupo_privado_id = int(os.getenv('GRUPO_PRIVADO_ID'))

canais_para_monitorar = ['ofertaskabum', 'peperaiohardware', 'anrutech']

client = TelegramClient('userbot_session', api_id, api_hash)

async def entrar_canais():
    for canal in canais_para_monitorar:
        try:
            await client(JoinChannelRequest(canal))
            print(f"Entrou no canal @{canal}")
        except errors.UserAlreadyParticipantError:
            print(f"Já inscrito no canal @{canal}")
        except Exception as e:
            print(f"Erro ao entrar no canal @{canal}: {e}")

@client.on(events.NewMessage(chats=canais_para_monitorar))
async def monitorar_mensagens(event):
    print(f"[DEBUG] Mensagem nova no canal @{event.chat.username}: {event.text[:80]}")
    try:
        await event.forward_to(grupo_privado_id)
        print(f"Mensagem encaminhada para o grupo privado (ID: {grupo_privado_id})")
    except Exception as e:
        print(f"Erro ao encaminhar mensagem: {e}")

async def main():
    await client.start()
    await entrar_canais()
    print("Userbot rodando e monitorando canais para DEBUG...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
