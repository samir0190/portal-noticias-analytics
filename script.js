const API_URL = "https://projeto-y7ry.onrender.com";
const cacheNoticias = {};
let noticiasExibidas = [], itensPorPagina = 9, paginaAtual = 1;
let exibindoDashboard = false; 
let datasValidas = [];

// Instâncias Globais dos Gráficos do Chart.js
let instanciasGraficos = { relogio: null, fontes: null, delay: null };

// Inicialização: Configura limites do calendário
async function carregarConfiguracoes() {
    try {
        const res = await fetch(`${API_URL}/datas_disponiveis`);
        datasValidas = await res.json();
        if (datasValidas.length > 0) {
            const campoData = document.getElementById("campoData");
            campoData.min = datasValidas[datasValidas.length - 1];
            campoData.max = datasValidas[0];
        }
    } catch (e) { console.error("Erro ao carregar configurações básicas.", e); }
}
carregarConfiguracoes();

// Auxiliar: Gera a estrutura HTML limpa de cada Card
function gerarHtmlCard(noticia) {
    const imagemPadrao = 'https://via.placeholder.com/300x180';
    return `
        <div class="card fade-in">
            <img src="${noticia.imagem || imagemPadrao}" alt="Imagem da notícia" />
            <div class="card-content">
                <h3>${noticia.titulo}</h3>
                <p class="tag-categoria"><strong>${noticia.categoria}</strong></p>
                <a href="${noticia.url}" target="_blank" onclick="registrarAcesso('${noticia.url}')">Ler na íntegra →</a>
            </div>
        </div>`;
}

function prepararExibicao(lista) {
    exibindoDashboard = false;
    noticiasExibidas = lista; 
    paginaAtual = 1;
    document.getElementById("noticias").innerHTML = "";
    mostrarMais();
}

function mostrarMais() {
    if (exibindoDashboard) return; 

    const div = document.getElementById("noticias");
    const inicio = (paginaAtual - 1) * itensPorPagina;
    const fim = paginaAtual * itensPorPagina;
    const pedaco = noticiasExibidas.slice(inicio, fim);
    
    if (pedaco.length === 0) return;
    
    const htmlNovo = pedaco.map(noticia => gerarHtmlCard(noticia)).join('');
    div.insertAdjacentHTML('beforeend', htmlNovo);
    paginaAtual++;
}

// Filtros de pesquisa por requisições de API
async function carregarNoticias() {
    if (cacheNoticias['todas']) return prepararExibicao(cacheNoticias['todas']);
    try {
        const res = await fetch(`${API_URL}/noticias`);
        cacheNoticias['todas'] = await res.json();
        prepararExibicao(cacheNoticias['todas']);
    } catch (e) { document.getElementById("noticias").innerHTML = "<p>Erro ao conectar com o servidor.</p>"; }
}

async function filtrar(categoria) {
    if (cacheNoticias[categoria]) return prepararExibicao(cacheNoticias[categoria]);
    try {
        const res = await fetch(`${API_URL}/categoria/${categoria}`);
        cacheNoticias[categoria] = await res.json();
        prepararExibicao(cacheNoticias[categoria]);
    } catch (e) { console.error(e); }
}

async function buscarPorData() {
    const dataSelecionada = document.getElementById("campoData").value;
    if (!dataSelecionada) return carregarNoticias();

    if (!datasValidas.includes(dataSelecionada)) {
        alert("Ops! Não temos notícias coletadas para este dia específico.");
        return;
    }

    const chaveCache = `data_${dataSelecionada}`;
    if (cacheNoticias[chaveCache]) return prepararExibicao(cacheNoticias[chaveCache]);

    try {
        const res = await fetch(`${API_URL}/data/${dataSelecionada}`);
        cacheNoticias[chaveCache] = await res.json();
        prepararExibicao(cacheNoticias[chaveCache]);
    } catch (e) { console.error(e); }
}

let timeoutBusca = null;
function buscar() {
    clearTimeout(timeoutBusca);
    timeoutBusca = setTimeout(async () => {
        const termo = document.getElementById("campoBusca").value;
        if (termo.length >= 3) {
            const res = await fetch(`${API_URL}/buscar/${termo}`);
            prepararExibicao(await res.json());
        } else if (termo.length === 0) carregarNoticias();
    }, 500); 
}

async function registrarAcesso(url) {
    fetch(`${API_URL}/contar_acesso/${encodeURIComponent(url)}`, { method: 'POST' });
}

// Monitoramento do scroll infinito
window.addEventListener('scroll', () => {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 100) mostrarMais();
});

// --- DASHBOARD RENDERING SYSTEM ---

function destruirGraficosAntigos() {
    Object.keys(instanciasGraficos).forEach(chave => {
        if (instanciasGraficos[chave]) {
            instanciasGraficos[chave].destroy();
            instanciasGraficos[chave] = null;
        }
    });
}

async function mostrarAbaAnalise(categoria = 'Todas') {
    exibindoDashboard = true;
    const div = document.getElementById("noticias");
    div.innerHTML = "<p style='text-align:center; grid-column: 1 / -1;'>Carregando inteligência de dados...</p>";

    try {
        const res = await fetch(`${API_URL}/dashboard?categoria=${categoria}`);
        const dados = await res.json();

        // Injeção da estrutura base estrutural do Dashboard
        div.innerHTML = `
            <div class="dashboard-aba">
                <div class="dashboard-header">
                    <div>
                        <h2>📊 Inteligência de Dados</h2>
                        <p style="color: #666; font-size: 0.95em;">Base de dados: <strong>${dados.total}</strong> notícias analisadas.</p>
                    </div>
                    <select id="filtroCategoriaDashboard" onchange="mostrarAbaAnalise(this.value)">
                        <option value="Todas" ${categoria === 'Todas' ? 'selected' : ''}>Todas as Categorias</option>
                        <option value="Tecnologia" ${categoria === 'Tecnologia' ? 'selected' : ''}>Tecnologia</option>
                        <option value="Esportes" ${categoria === 'Esportes' ? 'selected' : ''}>Esportes</option>
                        <option value="Economia" ${categoria === 'Economia' ? 'selected' : ''}>Economia</option>
                        <option value="Geral" ${categoria === 'Geral' ? 'selected' : ''}>Geral</option>
                    </select>
                </div>

                <div class="secao-metadados">
                    <div class="card-analise">
                        <h3>📰 Top 5 Veículos (Fontes)</h3>
                        <div style="position: relative; height: 250px;"><canvas id="graficoFontes"></canvas></div>
                    </div>
                    <div class="card-analise">
                        <h3>⏰ Pico de Postagem</h3>
                        <div style="position: relative; height: 250px;"><canvas id="graficoRelogio"></canvas></div>
                    </div>
                </div>

                <div class="secao-metadados" style="margin-top: 20px;">
                    <div class="card-analise" style="grid-column: span 2;">
                        <h3>⚡ Histórico de Delay (Últimas Notícias)</h3>
                        <div style="position: relative; height: 220px;"><canvas id="graficoDelay"></canvas></div>
                        <p style="text-align: center; margin-top: 20px;">Média Geral de Delay: <strong>${dados.frescor_medio}h</strong></p>
                    </div>
                    <div class="card-analise" style="display: flex; flex-direction: column; justify-content: center; align-items: center;">
                        <h3>🌡️ Termômetro</h3>
                        <p style="font-size: 1.2em; font-weight:bold; color: ${dados.sentimento.cor};">${dados.sentimento.humor}</p>
                        <div class="barra-sentimento-container"><div class="barra-sentimento" style="width: ${dados.sentimento.score_pos}%; background: ${dados.sentimento.cor}"></div></div>
                        <p style="margin-top: 10px;">Positividade: <strong>${dados.sentimento.score_pos}%</strong></p>
                    </div>
                </div>
            </div>`;

        destruirGraficosAntigos();

        // Renderizadores dos Gráficos com Chart.js
        instanciasGraficos.relogio = new Chart(document.getElementById('graficoRelogio'), {
            type: 'doughnut',
            data: {
                labels: ['Manhã', 'Tarde', 'Noite', 'Madrugada'],
                datasets: [{ data: [dados.relogio.manha, dados.relogio.tarde, dados.relogio.noite, dados.relogio.madrugada], backgroundColor: ['#ffeb3b', '#ff9800', '#3f51b5', '#212121'], borderWidth: 0 }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
        });

        if (dados.fontes && dados.fontes.length > 0) {
            instanciasGraficos.fontes = new Chart(document.getElementById('graficoFontes'), {
                type: 'bar',
                data: {
                    labels: dados.fontes.map(f => f.nome),
                    datasets: [{ data: dados.fontes.map(f => f.quantidade), backgroundColor: 'rgba(26, 115, 232, 0.7)', borderRadius: 4 }]
                },
                options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } }, plugins: { legend: { display: false } } }
            });
        }

        if (dados.historico_delay && dados.historico_delay.dados.length > 0) {
            instanciasGraficos.delay = new Chart(document.getElementById('graficoDelay'), {
                type: 'line',
                data: {
                    labels: dados.historico_delay.labels,
                    datasets: [{ data: dados.historico_delay.dados, borderColor: '#f44336', backgroundColor: 'rgba(244, 67, 54, 0.1)', borderWidth: 2, tension: 0.3, fill: true, pointRadius: 3 }]
                },
                options: { responsive: true, maintainAspectRatio: false, scales: { x: { ticks: { display: false } } }, plugins: { legend: { display: false } } }
            });
        }
    } catch (e) {
        div.innerHTML = "<p style='color:red; text-align:center;'>Erro ao conectar com o servidor.</p>";
        console.error(e);
    }
}

// Inicializa o Portal listando as principais notícias
carregarNoticias();