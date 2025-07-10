#!/usr/bin/env python3
"""
Bot para monitorar preços de GPUs na Kabum
Versão corrigida com melhor parsing de preços e seletores atualizados
"""

import requests
from bs4 import BeautifulSoup
import time
import re
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin, quote_plus
import os
from dataclasses import dataclass

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('kabum_gpu_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class GpuOffer:
    """Classe para representar uma oferta de GPU"""
    name: str
    price: float
    url: str
    availability: str = "Disponível"
    
    def __str__(self):
        return f"{self.name} - R$ {self.price:.2f}"

class KabumGpuBot:
    def __init__(self, max_price: float = 1500.0, debug_mode: bool = False):
        self.max_price = max_price
        self.debug_mode = debug_mode
        self.base_url = "https://www.kabum.com.br"
        self.session = requests.Session()
        
        # Headers mais realistas
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        self.session.headers.update(self.headers)
        
        # Seletores CSS atualizados
        self.selectors = {
            'product_cards': [
                'article.productCard',
                'div.productCard',
                'div[data-testid="product-card"]',
                'div.sc-fqkvVR',
                'div[class*="product"]',
                'div[class*="card"]'
            ],
            'title': [
                'h2.nameCard',
                'h3.nameCard', 
                'h2[class*="name"]',
                'h3[class*="name"]',
                'a[class*="name"]',
                '.productCard h2',
                '.productCard h3',
                'h2',
                'h3'
            ],
            'price': [
                'span.priceCard',
                'span[class*="price"]',
                'div[class*="price"]',
                '.priceCard',
                'span.finalPrice',
                'span[data-testid="price"]',
                'span.sc-dcJsrY',
                'span[class*="final"]'
            ],
            'link': [
                'a.productLink',
                'a[class*="product"]',
                'a[class*="link"]',
                'a[href*="/produto/"]',
                'a'
            ]
        }
        
        # URLs de busca
        self.search_urls = [
            "/busca?query={query}",
            "/hardware/placa-de-video-vga?string={query}",
            "/busca/{query}",
            "/hardware/placa-de-video-vga?order=price&limit=100&string={query}"
        ]
        
        # Padrões de GPU
        self.gpu_patterns = {
            'RTX 4060': r'RTX\s*4060(?!\s*Ti)',
            'RTX 4060 Ti': r'RTX\s*4060\s*Ti',
            'RTX 4070': r'RTX\s*4070(?!\s*Ti)',
            'RTX 4070 Ti': r'RTX\s*4070\s*Ti',
            'RTX 3060': r'RTX\s*3060(?!\s*Ti)',
            'RTX 3060 Ti': r'RTX\s*3060\s*Ti',
            'RTX 3070': r'RTX\s*3070(?!\s*Ti)',
            'RTX 3070 Ti': r'RTX\s*3070\s*Ti',
            'RX 6600': r'RX\s*6600(?!\s*XT)',
            'RX 6600 XT': r'RX\s*6600\s*XT',
            'RX 6700 XT': r'RX\s*6700\s*XT',
            'RX 7600': r'RX\s*7600(?!\s*XT)',
            'RX 7600 XT': r'RX\s*7600\s*XT'
        }
        
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        
        if self.debug_mode:
            logger.setLevel(logging.DEBUG)
            logger.info("🔍 Modo debug ativado")

    def extract_price(self, price_text: str) -> Optional[float]:
        """Extrai o preço do texto, lidando com diferentes formatos"""
        if not price_text:
            return None
            
        # Remove espaços e caracteres especiais
        price_text = price_text.strip()
        
        # Padrões para extrair preço
        patterns = [
            r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',  # R$ 1.234,56
            r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',        # 1.234,56
            r'(\d+,\d{2})',                              # 1234,56
            r'(\d+\.\d{2})',                             # 1234.56
            r'(\d+)'                                     # 1234
        ]
        
        for pattern in patterns:
            match = re.search(pattern, price_text)
            if match:
                price_str = match.group(1)
                try:
                    # Converte para float (formato brasileiro)
                    if ',' in price_str:
                        price_str = price_str.replace('.', '').replace(',', '.')
                    elif '.' in price_str and len(price_str.split('.')[-1]) == 2:
                        # Já está em formato correto (1234.56)
                        pass
                    else:
                        # Remove pontos de milhares
                        price_str = price_str.replace('.', '')
                    
                    price = float(price_str)
                    
                    # Validação básica de preço
                    if 100 <= price <= 50000:  # Preços válidos para GPUs
                        return price
                        
                except (ValueError, TypeError):
                    continue
        
        logger.debug(f"Não foi possível extrair preço de: '{price_text}'")
        return None

    def find_element_by_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> Optional[BeautifulSoup]:
        """Encontra elemento usando múltiplos seletores"""
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    return element
            except Exception as e:
                logger.debug(f"Erro com seletor {selector}: {e}")
        return None

    def find_elements_by_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> List[BeautifulSoup]:
        """Encontra elementos usando múltiplos seletores"""
        elements = []
        for selector in selectors:
            try:
                found = soup.select(selector)
                if found:
                    elements.extend(found)
                    logger.debug(f"Encontrados {len(found)} elementos com seletor: {selector}")
            except Exception as e:
                logger.debug(f"Erro com seletor {selector}: {e}")
        
        # Remove duplicatas mantendo ordem
        unique_elements = []
        seen = set()
        for elem in elements:
            elem_id = id(elem)
            if elem_id not in seen:
                seen.add(elem_id)
                unique_elements.append(elem)
        
        return unique_elements

    def parse_product_card(self, card: BeautifulSoup) -> Optional[GpuOffer]:
        """Extrai informações de um card de produto"""
        try:
            # Busca título
            title_element = self.find_element_by_selectors(card, self.selectors['title'])
            if not title_element:
                logger.debug("Título não encontrado")
                return None
                
            title = title_element.get_text(strip=True)
            if not title:
                logger.debug("Título vazio")
                return None
                
            logger.debug(f"Título encontrado: {title}")
            
            # Verifica se é uma GPU que estamos procurando
            gpu_match = None
            for gpu_name, pattern in self.gpu_patterns.items():
                if re.search(pattern, title, re.IGNORECASE):
                    gpu_match = gpu_name
                    break
            
            if not gpu_match:
                logger.debug(f"Não é uma GPU de interesse: {title}")
                return None
                
            # Busca preço
            price_element = self.find_element_by_selectors(card, self.selectors['price'])
            if not price_element:
                logger.debug("Preço não encontrado")
                return None
                
            price_text = price_element.get_text(strip=True)
            price = self.extract_price(price_text)
            
            if price is None:
                logger.debug(f"Não foi possível extrair preço de: {price_text}")
                return None
                
            # Busca link
            link_element = self.find_element_by_selectors(card, self.selectors['link'])
            product_url = ""
            if link_element:
                href = link_element.get('href')
                if href:
                    product_url = urljoin(self.base_url, href)
            
            # Verifica se o preço está dentro do limite
            if price <= self.max_price:
                logger.info(f"✅ Oferta encontrada: {title} - R$ {price:.2f}")
                return GpuOffer(
                    name=title,
                    price=price,
                    url=product_url
                )
            else:
                logger.debug(f"❌ Preço alto: {title} - R$ {price:.2f}")
                return None
                
        except Exception as e:
            logger.debug(f"Erro ao processar card: {e}")
            return None

    def search_gpus(self, query: str) -> List[GpuOffer]:
        """Busca GPUs com uma query específica"""
        offers = []
        
        for i, url_template in enumerate(self.search_urls):
            try:
                # Constrói URL
                formatted_query = quote_plus(query)
                search_url = self.base_url + url_template.format(query=formatted_query)
                
                logger.info(f"Tentativa {i+1}/{len(self.search_urls)}: {search_url}")
                
                # Faz requisição
                response = self.session.get(search_url, timeout=30)
                response.raise_for_status()
                
                if self.debug_mode:
                    # Salva HTML para debug
                    debug_file = f"debug_{query.replace(' ', '_')}_{i}.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    logger.debug(f"HTML salvo: {debug_file}")
                
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Busca cards de produtos
                product_cards = self.find_elements_by_selectors(soup, self.selectors['product_cards'])
                
                if not product_cards:
                    logger.debug(f"Nenhum card encontrado na tentativa {i+1}")
                    continue
                
                logger.info(f"Total de {len(product_cards)} elementos únicos encontrados")
                
                # Processa cada card
                for card in product_cards:
                    offer = self.parse_product_card(card)
                    if offer:
                        offers.append(offer)
                
                # Se encontrou ofertas, para de tentar outras URLs
                if offers:
                    break
                    
                # Delay entre tentativas
                time.sleep(2)
                
            except requests.RequestException as e:
                logger.error(f"Erro na requisição {i+1}: {e}")
                continue
            except Exception as e:
                logger.error(f"Erro inesperado na tentativa {i+1}: {e}")
                continue
        
        return offers

    def send_discord_notification(self, offers: List[GpuOffer]):
        """Envia notificação para Discord"""
        if not self.discord_webhook or not offers:
            return
            
        try:
            embed = {
                "title": f"🎮 {len(offers)} GPU(s) em Promoção na Kabum!",
                "color": 0x00ff00,
                "timestamp": datetime.now().isoformat(),
                "fields": []
            }
            
            for offer in offers:
                embed["fields"].append({
                    "name": offer.name,
                    "value": f"💰 R$ {offer.price:.2f}\n🔗 [Ver produto]({offer.url})",
                    "inline": True
                })
            
            data = {
                "embeds": [embed]
            }
            
            response = requests.post(self.discord_webhook, json=data, timeout=10)
            if response.status_code == 204:
                logger.info("✅ Notificação Discord enviada com sucesso")
            else:
                logger.error(f"❌ Erro ao enviar Discord: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Erro ao enviar notificação Discord: {e}")

    def save_history(self, offers: List[GpuOffer]):
        """Salva histórico de ofertas"""
        try:
            history_file = "gpu_offers_history.json"
            
            # Carrega histórico existente
            history = []
            if os.path.exists(history_file):
                try:
                    with open(history_file, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                except:
                    history = []
            
            # Adiciona ofertas atuais
            for offer in offers:
                history.append({
                    "timestamp": datetime.now().isoformat(),
                    "name": offer.name,
                    "price": offer.price,
                    "url": offer.url
                })
            
            # Salva histórico atualizado
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Histórico salvo: {len(offers)} ofertas")
            
        except Exception as e:
            logger.error(f"Erro ao salvar histórico: {e}")

    def run(self, gpus_to_monitor: List[str] = None):
        """Executa o monitoramento"""
        if gpus_to_monitor is None:
            gpus_to_monitor = ['RTX 4060', 'RTX 4060 Ti', 'RTX 4070', 'RTX 3060', 'RTX 3060 Ti']
        
        logger.info("=== INICIANDO KABUM GPU BOT ===")
        logger.info(f"💰 Preço máximo: R$ {self.max_price:.2f}")
        logger.info(f"🔍 GPUs monitoradas: {', '.join(gpus_to_monitor)}")
        
        all_offers = []
        
        for gpu in gpus_to_monitor:
            logger.info(f"\n🔍 Buscando: {gpu}")
            
            if self.debug_mode:
                logger.info(f"🔍 Modo debug: testando {gpu}")
            
            offers = self.search_gpus(gpu)
            
            if offers:
                logger.info(f"✅ Encontradas {len(offers)} ofertas para {gpu}")
                all_offers.extend(offers)
            else:
                logger.info(f"❌ Nenhuma oferta encontrada para {gpu}")
            
            # Delay entre buscas
            time.sleep(5)
        
        # Processa resultados
        if all_offers:
            logger.info(f"\n🎉 TOTAL: {len(all_offers)} ofertas encontradas!")
            
            # Remove duplicatas
            unique_offers = []
            seen_names = set()
            for offer in all_offers:
                if offer.name not in seen_names:
                    seen_names.add(offer.name)
                    unique_offers.append(offer)
            
            # Ordena por preço
            unique_offers.sort(key=lambda x: x.price)
            
            # Exibe ofertas
            print("\n" + "="*50)
            print("🎮 OFERTAS ENCONTRADAS:")
            print("="*50)
            for offer in unique_offers:
                print(f"• {offer}")
                if offer.url:
                    print(f"  🔗 {offer.url}")
            print("="*50)
            
            # Salva histórico
            self.save_history(unique_offers)
            
            # Envia notificações
            self.send_discord_notification(unique_offers)
            
        else:
            logger.info("❌ Nenhuma oferta encontrada")
        
        logger.info(f"=== FINALIZADO: {len(all_offers)} ofertas encontradas ===")

def main():
    """Função principal"""
    # Configuração
    MAX_PRICE = float(os.getenv('MAX_PRICE', '1500'))
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    
    # Lista de GPUs para monitorar
    GPUS_TO_MONITOR = [
        'RTX 4060',
        'RTX 4060 Ti', 
        'RTX 4070',
        'RTX 3060',
        'RTX 3060 Ti',
        'RTX 3070',
        'RX 6600',
        'RX 6600 XT',
        'RX 7600'
    ]
    
    try:
        # Cria e executa bot
        bot = KabumGpuBot(max_price=MAX_PRICE, debug_mode=DEBUG_MODE)
        bot.run(GPUS_TO_MONITOR)
        
    except KeyboardInterrupt:
        logger.info("\n⏹️  Bot interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro crítico: {e}")
        raise

if __name__ == "__main__":
    main()