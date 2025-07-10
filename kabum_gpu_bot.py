# kabum_gpu_bot.py
import requests
from bs4 import BeautifulSoup
import re
import time
import os
import json
from datetime import datetime
import logging

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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Configurar logging
debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
log_level = logging.DEBUG if debug_mode else logging.INFO
logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

def buscar_ofertas(gpu_term, max_price):
    """Busca ofertas na Kabum com tratamento de erros melhorado"""
    try:
        # Normaliza o termo de busca
        termo_busca = gpu_term.replace(' ', '+').replace('Ti', 'ti').replace('Super', 'super')
        busca_url = f"https://www.kabum.com.br/busca?query={termo_busca}"
        
        logger.info(f"Buscando: {busca_url}")
        
        response = requests.get(busca_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Tenta diferentes seletores para os cards de produto
        cards = soup.find_all("article", class_="productCard") or \
                soup.find_all("div", class_="productCard") or \
                soup.find_all("div", class_=re.compile("productCard")) or \
                soup.find_all("div", class_=re.compile("product-card"))
        
        if not cards:
            logger.warning(f"Nenhum card encontrado para {gpu_term}")
            return []
        
        ofertas = []
        for card in cards:
            try:
                # Busca título com diferentes seletores
                titulo_elem = card.find("span", class_="nameCard") or \
                             card.find("h3", class_=re.compile("name")) or \
                             card.find("h2", class_=re.compile("name")) or \
                             card.find("a", class_=re.compile("name")) or \
                             card.find("h3") or \
                             card.find("h2")
                
                if not titulo_elem:
                    continue
                
                titulo = titulo_elem.get_text(strip=True)
                
                # Filtra por GPUs relevantes - busca mais específica
                gpu_parts = gpu_term.split()
                if len(gpu_parts) >= 2:
                    gpu_serie = gpu_parts[0]  # RTX, GTX, RX
                    gpu_modelo = gpu_parts[1]  # 3060, 4070, etc.
                    
                    if not (gpu_serie.lower() in titulo.lower() and gpu_modelo in titulo):
                        continue
                else:
                    if not gpu_term.lower() in titulo.lower():
                        continue
                
                # Busca preços com diferentes seletores, priorizando preço à vista
                precos_possiveis = []
                
                # Seletores específicos da Kabum
                preco_elements = [
                    card.find("span", class_="priceCard"),
                    card.find("span", class_="cashPrice"),
                    card.find("span", class_="discountPrice"),
                    card.find("div", class_="priceCard"),
                    card.find("span", class_=re.compile("price")),
                    card.find("div", class_=re.compile("price")),
                    card.find("strong", class_=re.compile("price"))
                ]
                
                # Remove elementos None
                preco_elements = [p for p in preco_elements if p is not None]
                
                preco = None
                debug_precos = []  # Para debug
                
                for p in preco_elements:
                    if not p:
                        continue
                    
                    texto_preco = p.get_text(strip=True)
                    debug_precos.append(texto_preco)
                    
                    # Pula preços que claramente são parcelados
                    if any(termo in texto_preco.lower() for termo in ['sem juros', 'parcela', 'x de', '12x', '10x', '/mês']):
                        continue
                    
                    valor = extrair_preco(texto_preco)
                    if valor and valor > 100:  # Filtra preços muito baixos (provavelmente erros)
                        if preco is None or valor < preco:
                            preco = valor
                            # Se encontrou um preço à vista, prioriza ele
                            if any(termo in texto_preco.lower() for termo in ['à vista', 'avista', 'boleto', 'pix']):
                                break
                
                # Debug: mostra os preços encontrados
                if debug_precos and debug_mode:
                    logger.debug(f"Preços encontrados para '{titulo}': {debug_precos} -> Selecionado: R$ {preco}")
                
                if preco is None or preco > max_price:
                    continue
                
                # Busca link
                link_elem = card.find("a") or card.find_parent("a")
                if not link_elem:
                    continue
                
                link = link_elem.get("href")
                if link and not link.startswith("http"):
                    link = "https://www.kabum.com.br" + link
                
                ofertas.append({
                    "titulo": titulo,
                    "preco": preco,
                    "link": link
                })
                
            except Exception as e:
                logger.warning(f"Erro ao processar card: {e}")
                continue
        
        logger.info(f"Encontradas {len(ofertas)} ofertas para {gpu_term}")
        return ofertas
        
    except requests.RequestException as e:
        logger.error(f"Erro na requisição para {gpu_term}: {e}")
        return []
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar {gpu_term}: {e}")
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
    
    for categoria, modelos in GPU_LISTA.items():
        for modelo, preco_max in modelos.items():
            termo_busca = f"{categoria} {modelo}"
            logger.info(f"Buscando {termo_busca} (até R$ {preco_max})")
            
            ofertas = buscar_ofertas(termo_busca, preco_max)
            
            if ofertas:
                ofertas_totais += len(ofertas)
                enviar_discord(categoria, modelo, ofertas)
            
            # Aguarda entre buscas para evitar rate limiting
            time.sleep(5)
    
    # Salva histórico
    salvar_historico(ofertas_totais)
    
    logger.info(f"=== BUSCA FINALIZADA: {ofertas_totais} ofertas encontradas ===")

if __name__ == "__main__":
    main()