import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re
import sqlite3

HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
        "Referer": "https://www.google.com/"
    }
]

URL = "https://lista.mercadolivre.com.br/celular_Desde_"


class MercadoLivre:

    def __init__(self, url):
        self.url = url


    # REQUEST COM RETRY
    def safe_request(self, url):
        for i in range(3):
            try:
                headers = random.choice(HEADERS_LIST)

                print(f"Requisição: {url} (tentativa {i+1})")

                res = requests.get(url, headers=headers, timeout=10)

                print("Status:", res.status_code)

                if res.status_code == 200:
                    return res.text

                time.sleep(random.uniform(8, 15))

            except Exception as e:
                print("Erro:", e)
                time.sleep(2)

        print("Falhou:", url)
        return None

    # SCRAPING
    def get_url_itens(self):
        produtos = []

        for offset in range(1, 1400, 50):
            url = f"{self.url}{offset}"
            html = self.safe_request(url)
            
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            
            input(soup)

            items = soup.find_all("li", class_="ui-search-layout__item")

            print(f"Itens encontrados: {len(items)}")

            for item in items:
                try:
                    title = item.select_one(".poly-component__title")
                    price = item.select_one(".poly-price__current .andes-money-amount__fraction")
                    old_price = item.select_one("s .andes-money-amount__fraction")
                    rating = item.select_one(".poly-phrase-label")
                    loja = item.select_one(".poly-component__seller")
                    shipping = item.select_one(".poly-component__shipping span")
                    discount = item.select_one(".andes-money-amount__discount")
                    link = item.select_one("a.poly-component__title")

                    # texto
                    title = title.text if title else None
                    price = price.text if price else None
                    old_price = old_price.text if old_price else None
                    rating = rating.text if rating else None
                    loja = loja.text.strip() if loja else None
                    shipping = shipping.text if shipping else None
                    link = link["href"] if link else None

                    # desconto (%)
                    if discount:
                        match = re.search(r"(\d+)%", discount.text)
                        discount = int(match.group(1)) if match else None
                    else:
                        discount = None

                    produtos.append({
                        "titulo": title,
                        "preco": price,
                        "preco_antigo": old_price,
                        "avaliacao": rating,
                        "loja": loja,
                        "frete": shipping,
                        "desconto_pct": discount,
                        "link": link
                    })

                except Exception as e:
                    print("Erro item:", e)

            time.sleep(random.uniform(8, 15))

        return produtos

    # TRATAMENTO
    def parse_data(self, produtos):

        df = pd.DataFrame(produtos)
        print("\n===== ANTES DO TRATAMENTO =====")
        print("\nDescribe:")
        print(df.describe(include='all'))
        print("\nNulos:")
        print(df.isnull().sum())

        # LIMPEZA DE PREÇO
        df["preco"] = df["preco"].astype(str).str.replace(".", "", regex=False)
        df["preco"] = pd.to_numeric(df["preco"], errors="coerce")

        df["preco_antigo"] = df["preco_antigo"].astype(str).str.replace(".", "", regex=False)
        df["preco_antigo"] = pd.to_numeric(df["preco_antigo"], errors="coerce")


        # AVALIAÇÃO
        df["avaliacao"] = pd.to_numeric(df["avaliacao"], errors="coerce")


        # LIMPEZA GERAL
        df["titulo"] = df["titulo"].str.strip()
        df["loja"] = df["loja"].str.replace("por", "").str.strip()
        df["loja"] = df["loja"].fillna("Desconhecida")
        df["frete"] = df["frete"].fillna("Não informado")


        # NULOS
        df["preco_antigo"] = df["preco_antigo"].fillna(df["preco"])
        df["avaliacao"] = df["avaliacao"].fillna(df["avaliacao"].median())
        
        
        # OUTLIERS (PREÇOS MUITO BAIXOS)
        antes = len(df)
        df = df[df["preco"] >= 500]
        depois = len(df)
        

        # DESCONTO CALCULADO
        df["desconto_pct"] = (
            (df["preco_antigo"] - df["preco"]) / df["preco_antigo"]
        ) * 100

        df["desconto_pct"] = df["desconto_pct"].fillna(0).round(0).astype(int)


        # FEATURES
        df["tem_desconto"] = (df["desconto_pct"] > 0).astype(int)
        
        df["frete_gratis"] = df["frete"].str.contains("grátis", case=False, na=False).astype(int)
        
        df["faixa_preco"] = pd.cut(
            df["preco"],
            bins=[0, 500, 1000, 2000, 5000, 10000, float("inf")],
            labels=["0-500", "500-1k", "1k-2k", "2k-5k", "5k-10k", "10k+"]
        )
        
        df["score"] = (
            df["avaliacao"].fillna(0) * 0.5 +
            df["desconto_pct"] * 0.3 +
            df["frete_gratis"] * 10
        )
        
        # DEPOIS DO TRATAMENTO
        print("\n===== DEPOIS DO TRATAMENTO =====")

        print("\nDescribe:")
        print(df.describe())

        print("\nNulos:")
        print(df.isnull().sum())

        print("\nTotal final:", len(df))

        # EXPORT CSV
        df.to_csv("celulares.csv", index=False)


        # SQLITE
        conn = sqlite3.connect("celulares.db")
        df.to_sql("celulares", conn, if_exists="replace", index=False)
        conn.close()


        # OUTPUT
        print("\nDataset pronto:")
        print(df.head())


# EXECUÇÃO
bot = MercadoLivre(URL)
dados = bot.get_url_itens()
bot.parse_data(dados)