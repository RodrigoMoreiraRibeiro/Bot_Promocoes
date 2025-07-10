# kabum_gpu_bot.py
import requests
from bs4 import BeautifulSoup
import re
import time
import os
import json
from datetime import datetime
import logging

# ==== CONFIGURACOES ====
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1392933781886992566/NfSnIQIhXj-3NLb3OMx1R4-429334d3-o3BQU0lYETQZZv2W8fj-8AFNPwSry87h85M8")

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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extrair_preco(texto):
    """Extrai preço do texto, lidando com diferentes formatos"""
    if not texto:
        return None
    
    # Remove caracteres especiais e limpa o texto
    texto = texto.replace('\xa0', '').replace('R$', '').strip()
    
    # Busca por padrões de preço
    patterns = [
        r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',  # 1.999,99 ou 999,99
        r'(\d+,\d{2})',  # 999,99
        r'(\d+\.\d{2})',  # 999.99
        r'(\d+)'  # 999
    ]
    
    for pattern in patterns:
        match = re.search(pattern, texto)
        if match:
            preco_str = match.group(1)
            try:
                # Converte para float
                if ',' in preco_str and '.' in preco_str:
                    # Formato brasileiro: 1.999,99
                    preco_str = preco_str.replace('.', '').replace(',', '.')
                elif ',' in preco_str:
                    # Formato: 999,99
                    preco_str = preco_str.replace(',', '.')
                
                return float(preco_str)
            except ValueError:
                continue
    
    return None

def buscar_ofertas(gpu_term, max_price):
    """Busca ofertas na Kabum com tratamento de erros melhorado"""
    try:
        # Normaliza o termo de busca
        termo_busca = gpu_term.replace(' ', '-').lower()
        busca_url = f"https://www.kabum.com.br/busca/{termo_busca}"
        
        logger.info(f"Buscando: {busca_url}")
        
        response = requests.get(busca_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Tenta diferentes seletores para os cards de produto
        cards = soup.find_all("div", class_="productCard") or \
                soup.find_all("div", class_=re.compile("productCard")) or \
                soup.find_all("article", class_=re.compile("productCard"))
        
        if not cards:
            logger.warning(f"Nenhum card encontrado para {gpu_term}")
            return []
        
        ofertas = []
        for card in cards:
            try:
                # Busca título com diferentes seletores
                titulo_elem = card.find("span", class_="nameCard") or \
                             card.find("h3") or \
                             card.find("h2") or \
                             card.find("a", class_=re.compile("name"))
                
                if not titulo_elem:
                    continue
                
                titulo = titulo_elem.get_text(strip=True)
                
                # Filtra por GPUs relevantes
                if not any(gpu.lower() in titulo.lower() for gpu in [gpu_term.split()[0], gpu_term.split()[1] if len(gpu_term.split()) > 1 else ""]):
                    continue
                
                # Busca preços com diferentes seletores
                precos_possiveis = card.find_all("span", class_=re.compile("price")) + \
                                 card.find_all("div", class_=re.compile("price")) + \
                                 card.find_all("strong", class_=re.compile("price"))
                
                preco = None
                for p in precos_possiveis:
                    valor = extrair_preco(p.get_text())
                    if valor and valor > 100:  # Filtra preços muito baixos (provavelmente erros)
                        if preco is None or valor < preco:
                            preco = valor
                
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
                            "url": "https://i.imgur.com/GPU_ICON.png"  # Substitua por um ícone de GPU
                        }
                    }
                ]
            }
            
            response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
            response.raise_for_status()
            
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
            "gpus_monitoradas": len(GPU_LISTA)
        }
        
        with open("historico_ofertas.json", "w", encoding="utf-8") as f:
            json.dump(historico, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Histórico salvo: {ofertas_totais} ofertas encontradas")
        
    except Exception as e:
        logger.error(f"Erro ao salvar histórico: {e}")

def main():
    """Função principal do bot"""
    logger.info("=== INICIANDO BUSCA DE OFERTAS KABUM ===")
    
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
            time.sleep(3)
    
    # Salva histórico
    salvar_historico(ofertas_totais)
    
    logger.info(f"=== BUSCA FINALIZADA: {ofertas_totais} ofertas encontradas ===")

if __name__ == "__main__":
    main()