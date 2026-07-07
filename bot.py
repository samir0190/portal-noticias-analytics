import requests
import psycopg2

# 🔑 SUA API GNews
API_KEY = "4790c1898eba8d3924a5d675cbd54e06"

# 🔥 Apenas as categorias oficiais que vais usar no projeto
categorias_api = {
    "Tecnologia": "technology",
    "Esportes": "sports",
    "Economia": "business"
}  

# Conexão com o banco de dados
conn = psycopg2.connect("postgresql://postgres.ruwagoepsujdemktrqno:C66236DBCc.@aws-1-us-east-1.pooler.supabase.com:5432/postgres")
cursor = conn.cursor()

# 📡 BUSCAR NOTÍCIAS
for nome_categoria, api_categoria in categorias_api.items():

    print(f"🔄 Buscando {nome_categoria}...")

    url = f"https://gnews.io/api/v4/top-headlines?category={api_categoria}&lang=pt&max=10&token={API_KEY}"

    res = requests.get(url)
    data = res.json()

    if "articles" in data:
        for noticia in data["articles"]:
            try:
                cursor.execute("""
                    INSERT INTO noticias (titulo, descricao, url, imagem, fonte, data_publicacao, categoria)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (url) DO NOTHING
                """, (
                    noticia["title"],
                    noticia["description"],
                    noticia["url"],
                    noticia["image"],
                    noticia["source"]["name"],
                    noticia["publishedAt"],
                    nome_categoria
                ))
            except Exception as e:
                print(f"Erro no banco: {e}")
    else:
        print(f"Erro ao buscar {nome_categoria}: {data.get('errors', 'Erro desconhecido')}")

conn.commit()
cursor.close()
conn.close()
print("✅ Coleta finalizada com sucesso!")