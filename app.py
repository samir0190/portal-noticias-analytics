import os
from flask import Flask, jsonify, request
import psycopg2
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configurações de conexão 
DB_URI = "postgresql://postgres.ruwagoepsujdemktrqno:C66236DBCc.@aws-1-us-east-1.pooler.supabase.com:6543/postgres"

def conectar():
    return psycopg2.connect(DB_URI)

# --- ROTAS DE NOTÍCIAS ---\n
@app.route("/noticias")
def noticias():
    conn = conectar()
    cursor = conn.cursor()
    # Filtrado para trazer apenas as 3 categorias desejadas na aba "Todas"
    cursor.execute("""
        SELECT titulo, descricao, url, imagem, categoria 
        FROM noticias 
        WHERE TRIM(categoria) IN ('Tecnologia', 'Esportes', 'Economia')
        ORDER BY data_publicacao DESC
    """)
    dados = cursor.fetchall()
    conn.close()
    return jsonify([{"titulo": d[0], "descricao": d[1], "url": d[2], "imagem": d[3], "categoria": d[4]} for d in dados])

@app.route("/categoria/<categoria>")
def categoria_rota(categoria):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT titulo, descricao, url, imagem, categoria FROM noticias WHERE TRIM(categoria) ILIKE %s ORDER BY data_publicacao DESC", (categoria,))
    dados = cursor.fetchall()
    conn.close()
    return jsonify([{"titulo": d[0], "descricao": d[1], "url": d[2], "imagem": d[3], "categoria": d[4]} for d in dados])

@app.route("/data/<data_sel>")
def buscar_por_data(data_sel):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT titulo, descricao, url, imagem, categoria FROM noticias WHERE DATE(data_publicacao) = %s AND TRIM(categoria) IN ('Tecnologia', 'Esportes', 'Economia') ORDER BY data_publicacao DESC", (data_sel,))
    dados = cursor.fetchall()
    conn.close()
    return jsonify([{"titulo": d[0], "descricao": d[1], "url": d[2], "imagem": d[3], "categoria": d[4]} for d in dados])

@app.route("/buscar/<termo>")
def buscar(termo):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT titulo, descricao, url, imagem, categoria FROM noticias WHERE (titulo ILIKE %s OR descricao ILIKE %s) AND TRIM(categoria) IN ('Tecnologia', 'Esportes', 'Economia') ORDER BY data_publicacao DESC", (f"%{termo}%", f"%{termo}%"))
    dados = cursor.fetchall()
    conn.close()
    return jsonify([{"titulo": d[0], "descricao": d[1], "url": d[2], "imagem": d[3], "categoria": d[4]} for d in dados])

@app.route("/datas_disponiveis")
def datas_disponiveis():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT DATE(data_publicacao) as dt FROM noticias WHERE TRIM(categoria) IN ('Tecnologia', 'Esportes', 'Economia') ORDER BY dt DESC")
    dados = cursor.fetchall()
    conn.close()
    return jsonify([str(d[0]) for d in dados])

@app.route("/contar_acesso/<path:url>", methods=["POST"])
def contar_acesso(url):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("UPDATE noticias SET acessos = COALESCE(acessos, 0) + 1 WHERE url = %s", (url,))
    conn.commit()
    conn.close()
    return jsonify({"status": "sucesso"})

# --- ROTA DO DASHBOARD ---

@app.route("/dashboard")
def gerar_dashboard_analitico():
    categoria_selecionada = request.args.get("categoria", "Todas")
    
    conexao = conectar()
    leitor_banco = conexao.cursor()

    # Define o filtro com base na categoria escolhida para o Dashboard
    if categoria_selecionada != "Todas":
        filtro_sql = "WHERE TRIM(categoria) ILIKE %s"
        parametros_filtro = (categoria_selecionada,)
    else:
        filtro_sql = "WHERE TRIM(categoria) IN ('Tecnologia', 'Esportes', 'Economia')"
        parametros_filtro = ()

    # --- METRICA 1: VOLUME TOTAL E ENGAJAMENTO ---
    leitor_banco.execute(f"SELECT COUNT(*), COALESCE(SUM(acessos), 0) FROM noticias {filtro_sql}", parametros_filtro)
    total_noticias, total_cliques = leitor_banco.fetchone()

    # Tratamento para caso a base de dados esteja vazia
    if total_noticias == 0:
        conexao.close()
        return jsonify({"mensagem": "Sem dados para o filtro selecionado"})

    # --- METRICA 2: PADRÃO TEXTUAL (Média do tamanho dos títulos) ---
    leitor_banco.execute(f"SELECT AVG(LENGTH(titulo)) FROM noticias {filtro_sql}", parametros_filtro)
    tamanho_medio_titulo = round(float(leitor_banco.fetchone()[0] or 0), 1)

    # --- METRICA 3: QUALIDADE E COMPLETUDE DOS DADOS ---
    leitor_banco.execute(f"SELECT COUNT(*) FROM noticias {filtro_sql} AND imagem IS NOT NULL AND imagem != ''", parametros_filtro)
    noticias_com_imagem = leitor_banco.fetchone()[0]

    leitor_banco.execute(f"SELECT COUNT(*) FROM noticias {filtro_sql} AND descricao IS NOT NULL AND descricao != ''", parametros_filtro)
    noticias_com_descricao = leitor_banco.fetchone()[0]

    # --- METRICA 4: ANALISE DE SENSACIONALISMO (Heurística) ---
    termos_sensacionalistas = ['bomba', 'urgente', 'choque', 'revelado', 'escândalo', 'inacreditável', 'assusta', 'misterioso']
    condicoes_sql = " OR ".join(["titulo ILIKE %s" for _ in termos_sensacionalistas])
    
    if categoria_selecionada != "Todas":
        query_sensacionalismo = f"SELECT COUNT(*) FROM noticias WHERE ({condicoes_sql}) AND TRIM(categoria) ILIKE %s"
        parametros_sensa = tuple(f"%{termo}%" for termo in termos_sensacionalistas) + (categoria_selecionada,)
    else:
        query_sensacionalismo = f"SELECT COUNT(*) FROM noticias WHERE ({condicoes_sql}) AND TRIM(categoria) IN ('Tecnologia', 'Esportes', 'Economia')"
        parametros_sensa = tuple(f"%{termo}%" for termo in termos_sensacionalistas)

    leitor_banco.execute(query_sensacionalismo, parametros_sensa)
    total_noticias_sensacionalistas = leitor_banco.fetchone()[0]

    # --- METRICA 5: ANALISE DE FRESCOR (Série Temporal / Latência) ---
    leitor_banco.execute(f"SELECT data_publicacao FROM noticias {filtro_sql} ORDER BY data_publicacao DESC LIMIT 20", parametros_filtro)
    ultimas_20_noticias = leitor_banco.fetchall()
    
    lista_de_delays = []
    timestamps_grafico = []
    for linha in ultimas_20_noticias:
        data_publicacao = linha[0]
        if data_publicacao:
            # Calcula a diferença em horas entre a publicação e o momento atual
            diferenca_horas = (datetime.utcnow() - data_publicacao.replace(tzinfo=None)).total_seconds() / 3600
            lista_de_delays.append(round(max(0, diferenca_horas), 1))
            timestamps_grafico.append(data_publicacao.strftime("%H:%M"))

    atraso_medio_publicacao = round(sum(lista_de_delays)/len(lista_de_delays), 1) if lista_de_delays else 0

    # --- METRICA 6: DISTRIBUIÇÃO FREQUENCIAL (Pico de Postagem) ---
    leitor_banco.execute(f"SELECT EXTRACT(HOUR FROM data_publicacao) FROM noticias {filtro_sql}", parametros_filtro)
    lista_de_horas = [linha[0] for linha in leitor_banco.fetchall()]
    
    distribuicao_relogio = {"manha": 0, "tarde": 0, "noite": 0, "madrugada": 0}
    for hora in lista_de_horas:
        if 6 <= hora < 12: distribuicao_relogio["manha"] += 1
        elif 12 <= hora < 18: distribuicao_relogio["tarde"] += 1
        elif 18 <= hora < 24: distribuicao_relogio["noite"] += 1
        else: distribuicao_relogio["madrugada"] += 1

    # --- METRICA 7: ANALISE DE SENTIMENTO (Dicionário Léxico) ---
    termos_positivos = ['ganha', 'vence', 'lidera', 'sucesso', 'avanço', 'novo', 'cresce', 'tecnologia', 'ouro', 'campeão', 'lucro']
    termos_negativos = ['morre', 'crise', 'perde', 'queda', 'roubo', 'crime', 'inflação', 'alerta', 'perigo', 'cancela', 'derrota']
    
    condicoes_positivas = " OR ".join(["titulo ILIKE %s" for _ in termos_positivos])
    condicoes_negativas = " OR ".join(["titulo ILIKE %s" for _ in termos_negativos])
    
    if categoria_selecionada != "Todas":
        leitor_banco.execute(f"SELECT COUNT(*) FROM noticias WHERE ({condicoes_positivas}) AND TRIM(categoria) ILIKE %s", tuple(f"%{p}%" for p in termos_positivos) + (categoria_selecionada,))
        ocorrencias_positivas = leitor_banco.fetchone()[0]
        leitor_banco.execute(f"SELECT COUNT(*) FROM noticias WHERE ({condicoes_negativas}) AND TRIM(categoria) ILIKE %s", tuple(f"%{p}%" for p in termos_negativos) + (categoria_selecionada,))
        ocorrencias_negativas = leitor_banco.fetchone()[0]
    else:
        leitor_banco.execute(f"SELECT COUNT(*) FROM noticias WHERE ({condicoes_positivas}) AND TRIM(categoria) IN ('Tecnologia', 'Esportes', 'Economia')", tuple(f"%{p}%" for p in termos_positivos))
        ocorrencias_positivas = leitor_banco.fetchone()[0]
        leitor_banco.execute(f"SELECT COUNT(*) FROM noticias WHERE ({condicoes_negativas}) AND TRIM(categoria) IN ('Tecnologia', 'Esportes', 'Economia')", tuple(f"%{p}%" for p in termos_negativos))
        ocorrencias_negativas = leitor_banco.fetchone()[0]

    total_termos_encontrados = ocorrencias_positivas + ocorrencias_negativas
    score_positividade = round((ocorrencias_positivas / total_termos_encontrados * 100)) if total_termos_encontrados > 0 else 50

    # --- METRICA 8: MARKET SHARE DE FONTES (Top 5 Veículos) ---
    leitor_banco.execute(f"SELECT fonte, COUNT(*) as qtd FROM noticias {filtro_sql} GROUP BY fonte ORDER BY qtd DESC LIMIT 5", parametros_filtro)
    top_5_fontes = [{"nome": linha[0] or "Desconhecida", "quantidade": linha[1]} for linha in leitor_banco.fetchall()]

    conexao.close()
    
    # Retorno estruturado dos indicadores analíticos
    return jsonify({
        "total_noticias": total_noticias,
        "total_cliques": int(total_acessos),
        "tamanho_medio_titulo": tamanho_medio_titulo,
        "frescor_medio_horas": atraso_medio_publicacao,
        "indicadores_qualidade": {
            "porcentagem_com_imagem": round((noticias_com_imagem/total_noticias)*100, 1), 
            "porcentagem_com_descricao": round((noticias_com_descricao/total_noticias)*100, 1)
        },
        "porcentagem_sensacionalismo": round((total_noticias_sensacionalistas/total_noticias)*100, 1),
        "score_sentimento": score_positividade,
        "distribuicao_horaria": distribuicao_relogio,
        "principais_fontes": top_5_fontes
    })

if __name__ == "__main__":
    app.run(debug=True)