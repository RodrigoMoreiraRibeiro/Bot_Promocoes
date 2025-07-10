# kabum_gpu_bot.py - Versão Corrigida com Seletores Atualizados
import requests
from bs4 import BeautifulSoup
import re
import time
import os
import json
from datetime import datetime
import logging
import random
from urllib.parse import quote_plus

# ==== CONFIGURAÇÕES ====
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

GPU_LISTA = {
    "RTX": {
        "3060": 1700,
        "3070": 2800,
        "4060": 2500,
        "4070": 3000,
        "4070 Ti": 3800,
        "4080": 6000,
        "4090": 8000
    },
    "GTX": {
        "1660": 1100,
        "1650": 950,
        "1660 Ti": 1300,
        "1660 Super": 1200
    },
    "RX": {
        "6600": 1300,
        "6700": 1800,
        "6700 XT": 2200,
        "6800": 2500,
        "6800 XT": 2800,
        "7600": 1800,
        "7700 XT": 2500,
        "7800 XT": 3000
    }
}

# Headers mais realistas
HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "DNT": "1",
        "Pragma": "no-cache"
    }
]

# Configurar logging
debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
log_level = logging.DEBUG if debug_mode else logging.INFO
logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_random_headers():
    """Retorna headers aleatórios para evitar detecção"""
    return random.choice(HEADERS_LIST)

def extrair_preco(texto):
    """Extrai preço do texto com melhor precisão para formatos brasileiros"""
    if not texto:
        return None
    
    # Limpa o texto
    texto = texto.replace('\xa0', ' ').replace('\n', ' ').replace('\t', ' ').strip()
    
    # Remove prefixos comuns
    texto = re.sub(r'^(R\$|RS|por|de|até)\s*', '', texto, flags=re.IGNORECASE)
    
    # Pula textos que claramente não são preços à vista
    termos_excluir = ['sem juros', 'parcela', 'x de', '12x', '10x', '/mês', 'cartão', 'dividido', 'parcelado', 'boleto']
    if any(termo in texto.lower() for termo in termos_excluir):
        return None
    
    # Padrões de preço brasileiros mais precisos
    patterns = [
        r'(\d{1,2}\.\d{3},\d{2})',  # 12.299,99
        r'(\d{1,3}\.\d{3},\d{2})',  # 2.299,99
        r'(\d{3,4},\d{2})',         # 2299,99
        r'(\d{1,2}\.\d{3})',        # 12.299
        r'(\d{3,4})'                # 2299
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, texto)
        for match in matches:
            try:
                # Converte para float
                if '.' in match and ',' in match:
                    # Formato brasileiro: 2.299,99
                    valor_str = match.replace('.', '').replace(',', '.')
                elif ',' in match:
                    # Formato: 2299,99
                    valor_str = match.replace(',', '.')
                else:
                    # Formato: 2299
                    valor_str = match
                
                valor = float(valor_str)
                
                # Validação: preço deve estar em uma faixa realista para GPUs
                if 200 <= valor <= 20000:
                    return valor
                    
            except ValueError:
                continue
    
    return None

def criar_urls_busca(gpu_term):
    """Cria URLs de busca otimizadas para a Kabum"""
    # Normaliza o termo
    term_clean = gpu_term.strip().lower()
    term_dash = term_clean.replace(' ', '-')
    term_plus = quote_plus(gpu_term)
    
    urls = [
        # URL principal de busca
        f"https://www.kabum.com.br/busca/{term_dash}",
        
        # URL com parâmetros
        f"https://www.kabum.com.br/busca?query={term_plus}",
        
        # URL específica para placas de vídeo
        f"https://www.kabum.com.br/hardware/placa-de-video-vga?string={term_plus}",
        
        # URL de categoria com filtro
        f"https://www.kabum.com.br/hardware/placa-de-video-vga?order=price&limit=100&string={term_plus}",
    ]
    
    return urls

def extrair_dados_produto(element, gpu_term, debug_mode=False):
    """Extrai dados do produto de um elemento específico"""
    try:
        # Busca título com seletores mais amplos
        titulo_selectors = [
            "span.nameCard",
            "h3.nameCard", 
            "h2.nameCard",
            "a.nameCard",
            "[data-testid='product-name']",
            ".product-name",
            ".productName",
            "h3", "h2", "h1",
            "a[title]",
            "span[title]",
            "div[title]",
            "[class*='name']",
            "[class*='title']"
        ]
        
        titulo_elem = None
        titulo = ""
        
        for selector in titulo_selectors:
            titulo_elem = element.select_one(selector)
            if titulo_elem:
                titulo = titulo_elem.get_text(strip=True) or titulo_elem.get("title", "")
                if titulo:
                    break
        
        # Se não encontrou título, pega de atributos
        if not titulo:
            titulo = element.get("title", "") or element.get("alt", "")
        
        # Se ainda não encontrou, busca em texto
        if not titulo:
            text_content = element.get_text(strip=True)
            if text_content and len(text_content) > 5:
                titulo = text_content[:100]  # Limita a 100 caracteres
        
        if not titulo:
            if debug_mode:
                logger.debug("Título não encontrado")
            return None
        
        if debug_mode:
            logger.debug(f"Título encontrado: {titulo}")
        
        # Verifica se é a GPU procurada
        if not validar_gpu(titulo, gpu_term):
            if debug_mode:
                logger.debug(f"Não é {gpu_term}, pulando...")
            return None
        
        # Busca preços com seletores mais amplos
        preco_selectors = [
            "span.priceCard",
            "span.cashPrice", 
            "span.discountPrice",
            "div.priceCard",
            ".price-card",
            ".cash-price",
            ".discount-price",
            "[data-testid='price']",
            "[data-testid='cash-price']",
            "span[class*='price']",
            "div[class*='price']",
            "strong[class*='price']",
            "[class*='valor']",
            "[class*='preco']",
            "span",
            "div",
            "strong"
        ]
        
        preco = None
        preco_texts = []
        
        # Busca por seletores específicos
        for selector in preco_selectors:
            elements = element.select(selector)
            for elem in elements:
                texto_preco = elem.get_text(strip=True)
                if texto_preco and ('R$' in texto_preco or ',' in texto_preco):
                    preco_texts.append(texto_preco)
                    valor = extrair_preco(texto_preco)
                    if valor and (preco is None or valor < preco):
                        preco = valor
        
        # Busca adicional por texto contendo R$ ou números
        if preco is None:
            all_text = element.get_text()
            preco_regex = re.findall(r'R\$\s*[\d.,]+|\d+[.,]\d+', all_text)
            for text in preco_regex:
                if text.strip():
                    preco_texts.append(text.strip())
                    valor = extrair_preco(text.strip())
                    if valor and (preco is None or valor < preco):
                        preco = valor
        
        if debug_mode:
            logger.debug(f"Preços encontrados: {preco_texts}")
            logger.debug(f"Preço selecionado: R$ {preco}")
        
        if preco is None:
            return None
        
        # Busca link
        link = None
        
        # Se o próprio element é um link
        if element.name == 'a':
            link = element.get("href")
        else:
            # Busca link dentro do elemento
            link_elem = (
                element.select_one("a[href*='/produto/']") or
                element.select_one("a[href*='/hardware/']") or
                element.select_one("a") or
                element.find_parent("a")
            )
            
            if link_elem:
                link = link_elem.get("href")
        
        if link and not link.startswith("http"):
            link = "https://www.kabum.com.br" + link
        
        # Se não encontrou link, usa uma URL de busca
        if not link:
            search_term = quote_plus(titulo)
            link = f"https://www.kabum.com.br/busca?query={search_term}"
        
        return {
            "titulo": titulo,
            "preco": preco,
            "link": link
        }
        
    except Exception as e:
        if debug_mode:
            logger.debug(f"Erro ao extrair dados: {e}")
        return None

def validar_gpu(titulo, gpu_term):
    """Valida se o título corresponde à GPU procurada"""
    titulo_lower = titulo.lower()
    gpu_term_lower = gpu_term.lower()
    
    # Verifica se contém o termo completo
    if gpu_term_lower in titulo_lower:
        return True
    
    # Verifica partes do termo
    gpu_parts = gpu_term.split()
    
    if len(gpu_parts) >= 2:
        gpu_serie = gpu_parts[0].lower()  # rtx, gtx, rx
        gpu_modelo = gpu_parts[1].lower()  # 3060, 4070, etc.
        
        # Verifica se contém a série e o modelo
        if gpu_serie in titulo_lower and gpu_modelo in titulo_lower:
            return True
    
    return False

def buscar_ofertas(gpu_term, max_price):
    """Busca ofertas com estratégia aprimorada"""
    urls = criar_urls_busca(gpu_term)
    
    for url_idx, busca_url in enumerate(urls):
        try:
            logger.info(f"Tentativa {url_idx + 1}/{len(urls)}: {busca_url}")
            
            # Configura sessão
            session = requests.Session()
            session.headers.update(get_random_headers())
            
            # Faz requisição inicial para cookies
            session.get("https://www.kabum.com.br", timeout=30)
            time.sleep(random.uniform(2, 4))
            
            # Faz busca
            response = session.get(busca_url, timeout=30, allow_redirects=True)
            
            if response.status_code != 200:
                logger.warning(f"Status {response.status_code} para {busca_url}")
                continue
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Debug: salva HTML
            if debug_mode:
                filename = f"debug_{gpu_term.replace(' ', '_')}_{url_idx}.html"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(response.text)
                logger.debug(f"HTML salvo: {filename}")
            
            # Estratégia 1: Busca por cards de produto
            card_selectors = [
                "article.productCard",
                "div.productCard", 
                "div[class*='productCard']",
                "div[class*='product-card']",
                "article[class*='product']",
                "div[data-testid*='product']",
                "div[class*='item-card']",
                "div[class*='listing-item']",
                "div[class*='card']",
                "article",
                "div[class*='item']"
            ]
            
            cards = []
            for selector in card_selectors:
                found_cards = soup.select(selector)
                if found_cards:
                    cards.extend(found_cards)
                    logger.info(f"Encontrados {len(found_cards)} cards com seletor: {selector}")
            
            # Estratégia 2: Busca por links de produto
            if not cards:
                logger.info("Tentando estratégia alternativa: links de produto")
                product_links = soup.select("a[href*='/produto/']")
                for link in product_links:
                    # Pega o elemento pai que contém as informações
                    parent = link.find_parent()
                    if parent and parent not in cards:
                        cards.append(parent)
                
                logger.info(f"Encontrados {len(cards)} elementos via links de produto")
            
            # Estratégia 3: Busca por qualquer elemento que contenha preço
            if not cards:
                logger.info("Tentando estratégia alternativa: elementos com preço")
                price_elements = soup.find_all(text=re.compile(r'R\$.*\d'))
                for text in price_elements:
                    element = text.parent
                    if element and element not in cards:
                        # Pega um elemento pai maior que pode conter mais informações
                        for _ in range(3):  # Sobe até 3 níveis
                            parent = element.find_parent()
                            if parent and len(parent.get_text()) > len(element.get_text()):
                                element = parent
                            else:
                                break
                        cards.append(element)
                
                logger.info(f"Encontrados {len(cards)} elementos via preços")
            
            # Remove duplicatas
            cards = list(set(cards))
            
            if not cards:
                logger.warning(f"Nenhum card encontrado para {gpu_term}")
                continue
            
            logger.info(f"Total de {len(cards)} elementos únicos encontrados")
            
            # Processa cards
            ofertas = []
            for card_idx, card in enumerate(cards):
                dados = extrair_dados_produto(card, gpu_term, debug_mode)
                
                if dados and dados["preco"] and dados["preco"] <= max_price:
                    ofertas.append(dados)
                    logger.info(f"✅ Oferta: {dados['titulo'][:50]}... - R$ {dados['preco']:.2f}")
                elif debug_mode and dados:
                    logger.debug(f"❌ Preço alto: {dados['titulo'][:50]}... - R$ {dados['preco']:.2f}")
            
            if ofertas:
                logger.info(f"Encontradas {len(ofertas)} ofertas válidas para {gpu_term}")
                return ofertas
            
        except requests.RequestException as e:
            logger.error(f"Erro na requisição: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
        
        # Delay entre tentativas
        time.sleep(random.uniform(5, 10))
    
    logger.info(f"Nenhuma oferta encontrada para {gpu_term}")
    return []

def enviar_discord(categoria, modelo, ofertas):
    """Envia ofertas para o Discord"""
    if not ofertas or not WEBHOOK_URL:
        return
    
    logger.info(f"Enviando {len(ofertas)} ofertas para {categoria} {modelo}")
    
    cores = {
        "RTX": 0x76B900,  # Verde NVIDIA
        "GTX": 0x76B900,  # Verde NVIDIA  
        "RX": 0xED1C24    # Vermelho AMD
    }
    
    for i, oferta in enumerate(ofertas):
        try:
            payload = {
                "embeds": [
                    {
                        "title": f"🎯 {categoria} {modelo} - Oferta Encontrada!",
                        "url": oferta["link"],
                        "description": f"**{oferta['titulo']}**\n\n💰 **Preço:** R$ {oferta['preco']:.2f}\n🔗 [Ver na Kabum]({oferta['link']})",
                        "color": cores.get(categoria, 0x5793266),
                        "footer": {
                            "text": f"Kabum Bot • {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                        },
                        "thumbnail": {
                            "url": "https://cdn-icons-png.flaticon.com/512/2103/2103633.png"
                        }
                    }
                ]
            }
            
            response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"✅ Enviado: {oferta['titulo'][:50]}... - R$ {oferta['preco']:.2f}")
            
            # Rate limiting
            if i < len(ofertas) - 1:
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"Erro ao enviar Discord: {e}")

def salvar_historico(ofertas_totais):
    """Salva histórico das ofertas"""
    try:
        historico = {
            "timestamp": datetime.now().isoformat(),
            "total_ofertas": ofertas_totais,
            "gpus_monitoradas": sum(len(modelos) for modelos in GPU_LISTA.values()),
            "debug_mode": debug_mode
        }
        
        with open("historico_ofertas.json", "w", encoding="utf-8") as f:
            json.dump(historico, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Histórico salvo: {ofertas_totais} ofertas")
        
    except Exception as e:
        logger.error(f"Erro ao salvar histórico: {e}")

def main():
    """Função principal"""
    logger.info("=== INICIANDO KABUM GPU BOT ===")
    
    if not WEBHOOK_URL:
        logger.error("DISCORD_WEBHOOK_URL não configurada!")
        return
    
    ofertas_totais = 0
    
    # Modo debug: testa apenas RTX 4060
    if debug_mode:
        logger.info("🔍 Modo debug: testando RTX 4060")
        ofertas = buscar_ofertas("RTX 4060", 2500)
        if ofertas:
            ofertas_totais += len(ofertas)
            enviar_discord("RTX", "4060", ofertas)
    else:
        # Modo normal: busca todas as GPUs
        for categoria, modelos in GPU_LISTA.items():
            for modelo, preco_max in modelos.items():
                termo_busca = f"{categoria} {modelo}"
                logger.info(f"🔍 Buscando {termo_busca} (até R$ {preco_max})")
                
                ofertas = buscar_ofertas(termo_busca, preco_max)
                
                if ofertas:
                    ofertas_totais += len(ofertas)
                    enviar_discord(categoria, modelo, ofertas)
                
                # Delay entre buscas
                time.sleep(random.uniform(10, 20))
    
    # Salva histórico
    salvar_historico(ofertas_totais)
    
    logger.info(f"=== FINALIZADO: {ofertas_totais} ofertas encontradas ===")

if __name__ == "__main__":
    main()