# kabum_gpu_bot.py
import requests
from bs4 import BeautifulSoup
import re

# ==== CONFIGURACOES ====
WEBHOOK_URL = "https://discord.com/api/webhooks/1392933781886992566/NfSnIQIhXj-3NLb3OMx1R4-429334d3-o3BQU0lYETQZZv2W8fj-8AFNPwSry87h85M8"

GPU_LISTA = {
    "RTX": {
        "3060": 1700,
        "4060": 2500,
        "4070": 3000
    },
    "GTX": {
        "1660": 1100,
        "1650": 950
    },
    "RX": {
        "6600": 1300,
        "6700": 1800
    }
}

HEADERS = {"User-Agent": "Mozilla/5.0"}


def extrair_preco(texto):
    texto = texto.replace('\xa0', '').replace('R$', '')  # limpa o espaço especial e símbolo R$
    preco = re.sub(r'[^0-9,]', '', texto).replace(',', '.')
    try:
        return float(preco)
    except:
        return None



def buscar_ofertas(gpu_term, max_price):
    busca_url = f"https://www.kabum.com.br/busca/{gpu_term.replace(' ', '-')}"
    res = requests.get(busca_url, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    cards = soup.find_all("div", class_="productCard")

    ofertas = []
    for card in cards:
        titulo = card.find("span", class_="nameCard").get_text(strip=True)
        precos_possiveis = card.find_all("span", class_=re.compile("priceCard"))
        preco = None

        for p in precos_possiveis:
            valor = extrair_preco(p.get_text())
            if valor:
                if preco is None or valor < preco:
                    preco = valor

        if preco is None:
            continue
        link = "https://www.kabum.com.br" + card.find("a")["href"]

        if preco and preco <= max_price:
            ofertas.append({"titulo": titulo, "preco": preco, "link": link})

    return ofertas


def enviar_discord(categoria, modelo, ofertas):
    if not ofertas:
        print(f"[INFO] Nenhuma oferta para {categoria} {modelo}")
        return

    for o in ofertas:
        payload = {
            "embeds": [
                {
                    "title": f"{categoria} {modelo} - {o['titulo']}",
                    "url": o["link"],
                    "description": f"💰 **Preço:** R$ {o['preco']:.2f}\n🔗 [Ver na Kabum]({o['link']})",
                    "color": 5793266
                }
            ]
        }
        requests.post(WEBHOOK_URL, json=payload)


if __name__ == "__main__":
    for categoria, modelos in GPU_LISTA.items():
        for modelo, preco_max in modelos.items():
            termo_busca = f"{categoria} {modelo}"
            print(f"[BUSCA] {termo_busca} (<= R$ {preco_max})")
            ofertas = buscar_ofertas(termo_busca, preco_max)
            enviar_discord(categoria, modelo, ofertas)
