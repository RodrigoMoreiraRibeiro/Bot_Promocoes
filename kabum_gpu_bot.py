# kabum_gpu_bot.py
import requests
from bs4 import BeautifulSoup
import re
import time
import os
import json
from datetime import datetime
import logging
import random

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

# Headers mais realistas para evitar detecção
HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
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
    """Extrai preço do texto, lidando com diferentes formatos da Kabum"""
    if not texto:
        return None
    
    # Remove caracteres especiais e limpa o texto
    texto = texto.replace('\xa0', '').replace('R$', '').strip()
    
    # Pula textos que claramente não são preços à vista
    if any(termo in texto.lower() for termo in ['sem juros', 'parcela', 'x de', '12x', '10x', '/mês', 'cartão']):
        return None
    
    # Busca por padrões de preço
    patterns = [
        r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',  # 2.299,99 ou 1.999,99
        r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # 2,299.99 (formato alternativo)
        r'(\d+,\d{2})',  # 999,99
        r'(\d+\.\d{2})',  # 999.99
        r'(\d+)'  # 999
    ]
    
    for pattern in patterns:
        match = re.search(pattern, texto)
        if match:
            preco_str = match.group(1)
            try:
                # Converte para float - formato brasileiro
                if '.' in preco_str and ',' in preco_str:
                    # Formato brasileiro: 2.299,99
                    preco_str = preco_str.replace('.', '').replace(',', '.')
                elif ',' in preco_str and len(preco_str.split(',')[1]) == 2:
                    # Formato: 2299,99
                    preco_str = preco_str.replace(',', '.')
                elif ',' in preco_str:
                    # Formato: 2,299 (sem centavos)
                    preco_str = preco_str.replace(',', '')
                
                valor = float(preco_str)
                
                # Validação: preço deve estar em uma faixa realista para GPUs
                if 200 <= valor <= 15000:
                    return valor
                    
            except ValueError:
                continue
    
    return None

def tentar_diferentes_urls(gpu_term):
    """Tenta diferentes formatos de URL para a busca"""
    urls = [
        f"https://www.kabum.com.br/busca?query={gpu_term.replace(' ', '+').replace('Ti', 'ti').replace('Super', 'super')}",
        f"https://www.kabum.com.br/busca/{gpu_term.replace(' ', '-').lower()}",
        f"https://www.kabum.com.br/hardware/placa-de-video-vga?query={gpu_term.replace(' ', '+')}"
    ]
    return urls

def buscar_ofertas(gpu_term, max_price):
    """Busca ofertas na Kabum com tratamento de redirecionamento melhorado"""
    urls = tentar_diferentes_urls(gpu_term)
    
    for url_idx, busca_url in enumerate(urls):
        try:
            headers = get_random_headers()
            logger.info(f"Tentativa {url_idx + 1}: {busca_url}")
            
            # Criar sessão para manter cookies
            session = requests.Session()
            session.headers.update(headers)
            
            # Primeira requisição para obter cookies
            response = session.get("https://www.kabum.com.br", timeout=30)
            time.sleep(random.uniform(1, 3))  # Delay aleatório
            
            # Requisição de busca
            response = session.get(busca_url, timeout=30, allow_redirects=True)
            
            # Verificar se foi redirecionado para a página inicial
            if response.url == "https://www.kabum.com.br/" or "busca" not in response.url:
                logger.warning(f"Redirecionado para página inicial. URL atual: {response.url}")
                continue
            
            logger.info(f"Sucesso! URL final: {response.url}")
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Debug: salvar HTML para análise
            if debug_mode:
                with open(f"debug_page_{gpu_term.replace(' ', '_')}.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                logger.debug(f"HTML salvo para debug: debug_page_{gpu_term.replace(' ', '_')}.html")
            
            # Tenta diferentes seletores para os cards de produto
            cards = soup.find_all("article", class_="productCard") or \
                    soup.find_all("div", class_="productCard") or \
                    soup.find_all("div", class_=re.compile("productCard")) or \
                    soup.find_all("div", class_=re.compile("product-card")) or \
                    soup.find_all("article", class_=re.compile("product")) or \
                    soup.find_all("div", class_=re.compile("item-card"))
            
            if not cards:
                logger.warning(f"Nenhum card encontrado para {gpu_term} na URL {busca_url}")
                continue
            
            logger.info(f"Encontrados {len(cards)} cards na página")
            
            ofertas = []
            for card_idx, card in enumerate(cards):
                try:
                    # Busca título com diferentes seletores
                    titulo_elem = card.find("span", class_="nameCard") or \
                                 card.find("h3", class_=re.compile("name")) or \
                                 card.find("h2", class_=re.compile("name")) or \
                                 card.find("a", class_=re.compile("name")) or \
                                 card.find("h3") or \
                                 card.find("h2") or \
                                 card.find("a", title=True)
                    
                    if not titulo_elem:
                        if debug_mode:
                            logger.debug(f"Card {card_idx}: Sem título encontrado")
                        continue
                    
                    titulo = titulo_elem.get_text(strip=True) or titulo_elem.get("title", "")
                    
                    if debug_mode:
                        logger.debug(f"Card {card_idx}: Título encontrado: {titulo}")
                    
                    # Filtra por GPUs relevantes - busca mais específica
                    gpu_parts = gpu_term.split()
                    if len(gpu_parts) >= 2:
                        gpu_serie = gpu_parts[0]  # RTX, GTX, RX
                        gpu_modelo = gpu_parts[1]  # 3060, 4070, etc.
                        
                        if not (gpu_serie.lower() in titulo.lower() and gpu_modelo in titulo):
                            if debug_mode:
                                logger.debug(f"Card {card_idx}: Não é {gpu_term}, pulando...")
                            continue
                    else:
                        if not gpu_term.lower() in titulo.lower():
                            if debug_mode:
                                logger.debug(f"Card {card_idx}: Não contém {gpu_term}, pulando...")
                            continue
                    
                    # Busca preços com diferentes seletores
                    preco_elements = [
                        card.find("span", class_="priceCard"),
                        card.find("span", class_="cashPrice"),
                        card.find("span", class_="discountPrice"),
                        card.find("div", class_="priceCard"),
                        card.find("span", class_=re.compile("price")),
                        card.find("div", class_=re.compile("price")),
                        card.find("strong", class_=re.compile("price")),
                        card.find("span", string=re.compile(r"R\$")),
                        card.find("div", string=re.compile(r"R\$"))
                    ]
                    
                    # Remove elementos None
                    preco_elements = [p for p in preco_elements if p is not None]
                    
                    preco = None
                    debug_precos = []
                    
                    for p in preco_elements:
                        if not p:
                            continue
                        
                        texto_preco = p.get_text(strip=True)
                        debug_precos.append(texto_preco)
                        
                        # Pula preços que claramente são parcelados
                        if any(termo in texto_preco.lower() for termo in ['sem juros', 'parcela', 'x de', '12x', '10x', '/mês']):
                            continue
                        
                        valor = extrair_preco(texto_preco)
                        if valor and valor > 100:
                            if preco is None or valor < preco:
                                preco = valor
                                # Se encontrou um preço à vista, prioriza ele
                                if any(termo in texto_preco.lower() for termo in ['à vista', 'avista', 'boleto', 'pix']):
                                    break
                    
                    if debug_mode and debug_precos:
                        logger.debug(f"Card {card_idx}: Preços encontrados: {debug_precos} -> Selecionado: R$ {preco}")
                    
                    if preco is None:
                        if debug_mode:
                            logger.debug(f"Card {card_idx}: Nenhum preço válido encontrado")
                        continue
                    
                    if preco > max_price:
                        if debug_mode:
                            logger.debug(f"Card {card_idx}: Preço R$ {preco} acima do limite R$ {max_price}")
                        continue
                    
                    # Busca link
                    link_elem = card.find("a") or card.find_parent("a")
                    if not link_elem:
                        if debug_mode:
                            logger.debug(f"Card {card_idx}: Sem link encontrado")
                        continue
                    
                    link = link_elem.get("href")
                    if link and not link.startswith("http"):
                        link = "https://www.kabum.com.br" + link
                    
                    ofertas.append({
                        "titulo": titulo,
                        "preco": preco,
                        "link": link
                    })
                    
                    logger.info(f"✅ Oferta encontrada: {titulo} - R$ {preco}")
                    
                except Exception as e:
                    logger.warning(f"Erro ao processar card {card_idx}: {e}")
                    continue
            
            if ofertas:
                logger.info(f"Encontradas {len(ofertas)} ofertas para {gpu_term}")
                return ofertas
            else:
                logger.warning(f"Nenhuma oferta válida encontrada para {gpu_term}")
                
        except requests.RequestException as e:
            logger.error(f"Erro na requisição para {gpu_term} (URL {url_idx + 1}): {e}")
            continue
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar {gpu_term} (URL {url_idx + 1}): {e}")
            continue
        
        # Delay entre tentativas
        time.sleep(random.uniform(2, 5))
    
    logger.info(f"Nenhuma oferta encontrada para {gpu_term} após {len(urls)} tentativas")
    return []

def enviar_discord(categoria, modelo, ofertas):
    """Envia ofertas para o Discord com rate limiting"""
    if not ofertas:
        logger.info(f"Nenhuma oferta para {categoria} {modelo}")
        return
    
    if not WEBHOOK_URL:
        logger.error("DISCORD_WEBHOOK_URL não configurada!")
        return
    
    logger.info(f"Enviando {len(ofertas)} ofertas para {categoria} {modelo}")
    
    for i, oferta in enumerate(ofertas):
        try:
            # Determina cor baseada na categoria
            cores = {
                "RTX": 0x76B900,  # Verde NVIDIA
                "GTX": 0x76B900,  # Verde NVIDIA
                "RX": 0xED1C24    # Vermelho AMD
            }
            
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
            
            logger.info(f"Oferta enviada: {oferta['titulo']} - R$ {oferta['preco']:.2f}")
            
            # Rate limiting - aguarda entre mensagens
            if i < len(ofertas) - 1:
                time.sleep(2)
                
        except requests.RequestException as e:
            logger.error(f"Erro ao enviar para Discord: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao enviar Discord: {e}")

def salvar_historico(ofertas_totais):
    """Salva histórico das ofertas encontradas"""
    try:
        historico = {
            "timestamp": datetime.now().isoformat(),
            "total_ofertas": ofertas_totais,
            "gpus_monitoradas": sum(len(modelos) for modelos in GPU_LISTA.values()),
            "debug_mode": debug_mode
        }
        
        with open("historico_ofertas.json", "w", encoding="utf-8") as f:
            json.dump(historico, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Histórico salvo: {ofertas_totais} ofertas encontradas")
        
    except Exception as e:
        logger.error(f"Erro ao salvar histórico: {e}")

def main():
    """Função principal do bot"""
    logger.info("=== INICIANDO BUSCA DE OFERTAS KABUM ===")
    
    if not WEBHOOK_URL:
        logger.error("DISCORD_WEBHOOK_URL não configurada! Verificar secrets do GitHub.")
        return
    
    ofertas_totais = 0
    
    # Testa apenas RTX 4060 primeiro
    if debug_mode:
        logger.info("Modo debug: testando apenas RTX 4060")
        ofertas = buscar_ofertas("RTX 4060", 2500)
        if ofertas:
            ofertas_totais += len(ofertas)
            enviar_discord("RTX", "4060", ofertas)
    else:
        for categoria, modelos in GPU_LISTA.items():
            for modelo, preco_max in modelos.items():
                termo_busca = f"{categoria} {modelo}"
                logger.info(f"Buscando {termo_busca} (até R$ {preco_max})")
                
                ofertas = buscar_ofertas(termo_busca, preco_max)
                
                if ofertas:
                    ofertas_totais += len(ofertas)
                    enviar_discord(categoria, modelo, ofertas)
                
                # Aguarda entre buscas para evitar rate limiting
                time.sleep(random.uniform(8, 15))
    
    # Salva histórico
    salvar_historico(ofertas_totais)
    
    logger.info(f"=== BUSCA FINALIZADA: {ofertas_totais} ofertas encontradas ===")

if __name__ == "__main__":
    main()