import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import re
import os
from dotenv import load_dotenv
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

class PromoMonitor:
    def __init__(self):
        self.base_url = "https://www.kabum.com.br"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Configurações de promoção
        self.gpu_keywords = [
            'RTX 4090', 'RTX 4080', 'RTX 4070', 'RTX 4060',
            'RTX 3080', 'RTX 3070', 'RTX 3060',
            'RX 7900', 'RX 7800', 'RX 7700', 'RX 6800', 'RX 6700'
        ]
        
        # Preços máximos para considerar promoção (em R$)
        self.max_prices = {
            'RTX 4090': 8000,
            'RTX 4080': 6000,
            'RTX 4070': 4000,
            'RTX 4060': 2500,
            'RTX 3080': 4500,
            'RTX 3070': 3500,
            'RTX 3060': 2000,
            'RX 7900': 5000,
            'RX 7800': 4000,
            'RX 7700': 3000,
            'RX 6800': 3500,
            'RX 6700': 2500
        }
        
        # Produtos já enviados (para evitar spam)
        self.sent_products = set()
        
    def extract_price_value(self, price_text: str) -> Optional[float]:
        """Extrai o valor numérico do preço"""
        try:
            # Remove tudo exceto números, vírgulas e pontos
            clean_price = re.sub(r'[^\d,.]', '', price_text)
            
            # Substitui vírgula por ponto se for decimal brasileiro
            if ',' in clean_price and '.' in clean_price:
                # Formato: 1.234,56
                clean_price = clean_price.replace('.', '').replace(',', '.')
            elif ',' in clean_price:
                # Formato: 1234,56
                clean_price = clean_price.replace(',', '.')
            
            return float(clean_price)
        except:
            return None
    
    def is_promotion(self, product_name: str, price: float) -> bool:
        """Verifica se o produto está em promoção"""
        for keyword, max_price in self.max_prices.items():
            if keyword.lower() in product_name.lower():
                return price <= max_price
        return False
    
    def get_discount_percentage(self, product_name: str, price: float) -> Optional[int]:
        """Calcula percentual de desconto baseado no preço máximo"""
        for keyword, max_price in self.max_prices.items():
            if keyword.lower() in product_name.lower():
                if price <= max_price:
                    # Calcula desconto baseado em preço de referência mais alto
                    reference_price = max_price * 1.3  # 30% acima do máximo
                    discount = ((reference_price - price) / reference_price) * 100
                    return int(discount)
        return None
    
    async def search_gpu_promotions(self) -> List[Dict]:
        """Busca promoções de placas de vídeo"""
        promotions = []
        
        try:
            # Buscar por categoria de placas de vídeo
            search_url = f"{self.base_url}/hardware/placa-de-video-vga"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, headers=self.headers) as response:
                    if response.status != 200:
                        logger.error(f"Erro na requisição: {response.status}")
                        return promotions
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Buscar cards de produtos
                    product_cards = soup.find_all('div', class_='productCard')
                    
                    if not product_cards:
                        product_cards = soup.find_all('article', class_='productCard')
                    
                    logger.info(f"Encontrados {len(product_cards)} produtos")
                    
                    for card in product_cards[:20]:  # Limitar a 20 produtos
                        try:
                            # Extrair nome
                            name_elem = card.find('span', class_='nameCard') or card.find('h4', class_='nameCard')
                            if not name_elem:
                                continue
                            
                            name = name_elem.get_text(strip=True)
                            
                            # Verificar se é GPU que monitoramos
                            if not any(keyword.lower() in name.lower() for keyword in self.gpu_keywords):
                                continue
                            
                            # Extrair preço
                            price_elem = card.find('span', class_='priceCard') or card.find('span', {'data-testid': 'price-value'})
                            if not price_elem:
                                continue
                            
                            price_text = price_elem.get_text(strip=True)
                            price_value = self.extract_price_value(price_text)
                            
                            if not price_value:
                                continue
                            
                            # Verificar se é promoção
                            if not self.is_promotion(name, price_value):
                                continue
                            
                            # Extrair link
                            link_elem = card.find('a', href=True)
                            if not link_elem:
                                continue
                            
                            link = f"{self.base_url}{link_elem['href']}"
                            
                            # Verificar se já foi enviado
                            product_id = f"{name}_{price_value}"
                            if product_id in self.sent_products:
                                continue
                            
                            # Extrair imagem
                            img_elem = card.find('img')
                            image_url = ""
                            if img_elem and img_elem.get('src'):
                                image_url = img_elem['src']
                            
                            # Calcular desconto
                            discount = self.get_discount_percentage(name, price_value)
                            
                            promotion = {
                                'name': name,
                                'price': price_value,
                                'price_text': price_text,
                                'link': link,
                                'image': image_url,
                                'discount': discount,
                                'id': product_id
                            }
                            
                            promotions.append(promotion)
                            logger.info(f"Promoção encontrada: {name} - R$ {price_value}")
                            
                        except Exception as e:
                            logger.error(f"Erro ao processar produto: {e}")
                            continue
                    
        except Exception as e:
            logger.error(f"Erro na busca de promoções: {e}")
        
        return promotions

class PromoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        
        self.monitor = PromoMonitor()
        self.promo_channel_id = int(os.getenv('PROMO_CHANNEL_ID', 0))
        
    async def on_ready(self):
        print(f'🤖 {self.user} conectado ao Discord!')
        print(f'📊 Bot está em {len(self.guilds)} servidores')
        
        if self.promo_channel_id:
            channel = self.get_channel(self.promo_channel_id)
            if channel:
                print(f'📢 Canal de promoções: {channel.name}')
                
                # Enviar mensagem de inicialização
                embed = discord.Embed(
                    title="🚀 Bot de Promoções KaBuM Iniciado!",
                    description="Monitorando promoções de placas de vídeo...",
                    color=0x00ff00
                )
                await channel.send(embed=embed)
            else:
                print(f'❌ Canal de promoções não encontrado: {self.promo_channel_id}')
        
        # Iniciar monitoramento
        self.check_promotions.start()
        
        await self.change_presence(activity=discord.Game(name="🔍 Monitorando promoções"))
        
    @tasks.loop(minutes=30)  # Verificar a cada 30 minutos
    async def check_promotions(self):
        """Verifica promoções periodicamente"""
        try:
            logger.info("🔍 Verificando promoções...")
            
            promotions = await self.monitor.search_gpu_promotions()
            
            if not promotions:
                logger.info("❌ Nenhuma promoção encontrada")
                return
            
            if not self.promo_channel_id:
                logger.warning("❌ Canal de promoções não configurado")
                return
            
            channel = self.get_channel(self.promo_channel_id)
            if not channel:
                logger.error(f"❌ Canal {self.promo_channel_id} não encontrado")
                return
            
            # Enviar cada promoção
            for promo in promotions:
                await self.send_promotion(channel, promo)
                
                # Marcar como enviado
                self.monitor.sent_products.add(promo['id'])
                
                # Aguardar um pouco entre envios
                await asyncio.sleep(2)
            
            logger.info(f"✅ Enviadas {len(promotions)} promoções")
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar promoções: {e}")
    
    async def send_promotion(self, channel, promo):
        """Envia uma promoção para o canal"""
        try:
            embed = discord.Embed(
                title="🚨 PROMOÇÃO ENCONTRADA!",
                description=promo['name'],
                color=0xff4444,
                url=promo['link']
            )
            
            embed.add_field(
                name="💰 Preço",
                value=f"**R$ {promo['price']:.2f}**",
                inline=True
            )
            
            if promo['discount']:
                embed.add_field(
                    name="🏷️ Desconto",
                    value=f"**{promo['discount']}% OFF**",
                    inline=True
                )
            
            embed.add_field(
                name="🔗 Link",
                value=f"[Ver na KaBuM]({promo['link']})",
                inline=False
            )
            
            if promo['image']:
                embed.set_thumbnail(url=promo['image'])
            
            embed.set_footer(
                text=f"KaBuM Bot • {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )
            
            # Enviar com menção @everyone ou @here
            await channel.send("🚨 **PROMOÇÃO DE PLACA DE VÍDEO!** 🚨", embed=embed)
            
        except Exception as e:
            logger.error(f"❌ Erro ao enviar promoção: {e}")

bot = PromoBot()

# Comandos manuais
@bot.command(name='verificar', help='Verificar promoções manualmente')
@commands.has_permissions(administrator=True)
async def verificar_promo(ctx):
    """Comando para verificar promoções manualmente"""
    await ctx.send("🔍 Verificando promoções...")
    
    try:
        promotions = await bot.monitor.search_gpu_promotions()
        
        if not promotions:
            await ctx.send("❌ Nenhuma promoção encontrada no momento")
            return
        
        embed = discord.Embed(
            title="🚨 Promoções Encontradas",
            description=f"Foram encontradas {len(promotions)} promoções!",
            color=0x00ff00
        )
        
        for i, promo in enumerate(promotions[:5], 1):
            embed.add_field(
                name=f"{i}. {promo['name'][:40]}...",
                value=f"💰 **R$ {promo['price']:.2f}**\n🔗 [Ver produto]({promo['link']})",
                inline=False
            )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Erro ao verificar promoções: {e}")

@bot.command(name='config', help='Configurar preços máximos')
@commands.has_permissions(administrator=True)
async def configurar(ctx):
    """Mostrar configuração atual"""
    embed = discord.Embed(
        title="⚙️ Configuração do Bot",
        color=0x0099ff
    )
    
    embed.add_field(
        name="📢 Canal de Promoções",
        value=f"<#{bot.promo_channel_id}>" if bot.promo_channel_id else "Não configurado",
        inline=False
    )
    
    embed.add_field(
        name="🔍 Verificação",
        value="A cada 30 minutos",
        inline=True
    )
    
    embed.add_field(
        name="📊 Produtos Enviados",
        value=f"{len(bot.monitor.sent_products)} produtos",
        inline=True
    )
    
    # Mostrar preços máximos
    precos_text = ""
    for gpu, preco in list(bot.monitor.max_prices.items())[:5]:
        precos_text += f"{gpu}: R$ {preco}\n"
    
    embed.add_field(
        name="💰 Preços Máximos (alguns)",
        value=precos_text,
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='limpar', help='Limpar lista de produtos enviados')
@commands.has_permissions(administrator=True)
async def limpar_enviados(ctx):
    """Limpar lista de produtos já enviados"""
    count = len(bot.monitor.sent_products)
    bot.monitor.sent_products.clear()
    await ctx.send(f"✅ Lista de produtos enviados limpa! ({count} produtos removidos)")

@bot.event
async def on_command_error(ctx, error):
    """Tratamento de erros"""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Você não tem permissão para usar este comando!")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Comando não encontrado! Use `!help` para ver os comandos disponíveis.")
    else:
        logger.error(f"Erro não tratado: {error}")

if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_TOKEN')
    PROMO_CHANNEL_ID = os.getenv('PROMO_CHANNEL_ID')
    
    if not TOKEN:
        print("❌ Token do Discord não encontrado!")
        print("Configure DISCORD_TOKEN como variável de ambiente")
        exit(1)
    
    if not PROMO_CHANNEL_ID:
        print("⚠️ Canal de promoções não configurado!")
        print("Configure PROMO_CHANNEL_ID com o ID do canal #promoções")
        print("Para obter o ID: Clique com botão direito no canal > Copiar ID")
    
    print("🚀 Iniciando bot de promoções...")
    
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.error(f"Erro ao executar o bot: {e}")
        exit(1)