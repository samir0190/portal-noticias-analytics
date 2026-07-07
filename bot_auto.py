import requests
import psycopg2
import os

# Use a chave que vimos no seu painel
API_KEY = "4790c1898eba8d3924a5d675cbd54e06"
DB_URI = "postgresql://postgres.ruwagoepsujdemktrqno:C66236DBCc.@aws-1-us-east-1.pooler.supabase.com:6543/postgres"

def rodar_coleta():
    print("🚀 Iniciando coleta forçada...")
    try:
        conn = psycopg2.connect(DB_URI)
        cursor = conn.cursor()
        
        # Testando apenas uma categoria para ser rápido
        url = f"https://gnews.io/api/v4/top-headlines?category=general&lang=pt&max=10&token={API_KEY}"
        res = requests.get(url)
        data = res.json()

        if "articles" in data:
            for noticia in data["articles"]:
                cursor.execute("""
                    INSERT INTO noticias (titulo, descricao, url, imagem, fonte, data_publicacao, categoria, acessos)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
                    ON CONFLICT (url) DO NOTHING
                """, (
                    noticia["title"], noticia["description"], noticia["url"],
                    noticia["image"], noticia["source"]["name"], noticia["publishedAt"],
                    "Geral"
                ))
            conn.commit()
            print(f"✅ Sucesso! {len(data['articles'])} notícias processadas.")
        else:
            print(f"⚠️ API não retornou artigos: {data}")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    rodar_coleta()