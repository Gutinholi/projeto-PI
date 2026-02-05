"""
=============================================================================
SISTEMA DE MONITORAMENTO DE ALAGAMENTOS - GUARUJÁ/SP
=============================================================================
Projeto Integrador - Tecnologia da Informação

Descrição:
    Sistema colaborativo (Crowdsourcing) para monitoramento de alagamentos
    em tempo real, integrando dados meteorológicos da API Open-Meteo com
    reportes da comunidade local.

Tecnologias Utilizadas:
    - Python 3.10+
    - Streamlit: Framework para criação de aplicações web interativas
    - Requests: Biblioteca para consumo de APIs REST
    - Pandas: Biblioteca para manipulação de dados tabulares
    - JSON: Formato de persistência de dados

Arquitetura:
    Este sistema segue o padrão de arquitetura em camadas:
    1. Camada de Dados: Funções de leitura/escrita do arquivo JSON
    2. Camada de Serviço: Integração com API externa (Open-Meteo)
    3. Camada de Apresentação: Interface Streamlit (UI/UX)

Autor: [Seu Nome]
Data: 2024
=============================================================================
"""

# =============================================================================
# IMPORTAÇÃO DE BIBLIOTECAS
# =============================================================================

# Streamlit: Framework open-source para criação de aplicações web em Python.
# Permite criar interfaces interativas sem conhecimento de HTML/CSS/JavaScript.
# Documentação: https://docs.streamlit.io/
import streamlit as st

# Requests: Biblioteca HTTP para Python que permite fazer requisições a APIs REST.
# É o padrão de mercado para consumo de serviços web externos.
# Documentação: https://requests.readthedocs.io/
import requests

# JSON: Módulo nativo do Python para serialização/deserialização de dados.
# JSON (JavaScript Object Notation) é um formato leve de troca de dados.
import json

# Pandas: Biblioteca poderosa para análise e manipulação de dados.
# Utilizamos para criar DataFrames que alimentam o componente de mapa.
# Documentação: https://pandas.pydata.org/
import pandas as pd

# Datetime: Módulo nativo para manipulação de datas e horários.
# Utilizado para registrar timestamps das atualizações.
# timedelta: Utilizado para definir intervalos de tempo na atualização automática.
from datetime import datetime, timedelta

# OS: Módulo nativo para interação com o sistema operacional.
# Utilizado para obter o caminho absoluto do diretório do script.
import os

# concurrent.futures: Módulo para execução paralela de tarefas.
# Utilizado para fazer múltiplas requisições de API simultaneamente,
# reduzindo drasticamente o tempo de atualização dos dados meteorológicos.
from concurrent.futures import ThreadPoolExecutor, as_completed

# =============================================================================
# CONFIGURAÇÃO INICIAL DA PÁGINA STREAMLIT
# =============================================================================
# A função set_page_config() deve ser a primeira chamada Streamlit no script.
# Ela configura metadados da página como título, ícone e layout.
st.set_page_config(
    page_title="Monitor de Alagamentos - Guarujá",  # Título na aba do navegador
    page_icon="🌊",  # Emoji exibido como favicon
    layout="wide",  # Layout expandido (usa toda largura da tela)
    initial_sidebar_state="expanded"  # Sidebar aberta por padrão
)

# =============================================================================
# CONSTANTES E CONFIGURAÇÕES GLOBAIS
# =============================================================================
# Definimos constantes em MAIÚSCULAS seguindo convenções Python (PEP 8).
# Isso facilita a manutenção e evita "números mágicos" espalhados no código.

# Obtém o diretório onde o script está localizado
DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_DADOS = os.path.join(DIRETORIO_BASE, "dados.json")  # Caminho absoluto do arquivo
LIMITE_VOTOS_ALAGAMENTO = 5   # Mínimo de votos para confirmar alagamento
LIMITE_CHUVA_RISCO = 10.0     # Precipitação (mm) que dispara alerta automático
INTERVALO_ATUALIZACAO = 10    # Intervalo em minutos para atualização automática do clima (aumentado para performance)
MAX_WORKERS_API = 5           # Número máximo de requisições paralelas à API
CACHE_TTL_SEGUNDOS = 120      # Tempo de vida do cache em segundos (2 minutos)

# URL base da API Open-Meteo (serviço gratuito de dados meteorológicos)
# Documentação: https://open-meteo.com/en/docs
API_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# =============================================================================
# CAMADA DE DADOS - FUNÇÕES DE PERSISTÊNCIA
# =============================================================================
# Esta seção contém funções responsáveis pela leitura e escrita do arquivo JSON.
# Seguimos o princípio de responsabilidade única (SOLID): cada função faz uma coisa.

def carregar_dados():
    """
    Carrega os dados dos bairros a partir do arquivo JSON.

    Implementação:
        Utiliza o gerenciador de contexto 'with' para garantir que o arquivo
        será fechado corretamente após a leitura, mesmo em caso de erro.

    Retorno:
        list: Lista de dicionários contendo os dados de cada bairro.

    Tratamento de Erros:
        - FileNotFoundError: Arquivo não existe (precisa rodar resetar_bairros.py)
        - json.JSONDecodeError: Arquivo corrompido ou mal formatado
    """
    try:
        with open(ARQUIVO_DADOS, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
            return dados
    except FileNotFoundError:
        # Exibe erro amigável na interface se o arquivo não existir
        st.error("❌ Arquivo dados.json não encontrado! Execute primeiro: python resetar_bairros.py")
        return []
    except json.JSONDecodeError:
        st.error("❌ Erro ao ler dados.json. Arquivo pode estar corrompido.")
        return []


def salvar_dados(dados):
    """
    Persiste os dados dos bairros no arquivo JSON e atualiza o session_state.

    Parâmetros:
        dados (list): Lista de dicionários com dados atualizados dos bairros.

    Detalhes Técnicos:
        - indent=4: Formatação com 4 espaços para legibilidade
        - ensure_ascii=False: Preserva caracteres acentuados do português
        - encoding="utf-8": Padrão universal para caracteres especiais
    """
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, indent=4, ensure_ascii=False)

    # OTIMIZAÇÃO: Atualiza o cache em memória após salvar
    st.session_state.dados_bairros = dados


def obter_dados_otimizado():
    """
    Obtém dados dos bairros de forma otimizada usando session_state.

    OTIMIZAÇÃO: Evita leituras repetidas do arquivo JSON mantendo
    os dados em memória no session_state do Streamlit.

    Retorno:
        list: Lista de dicionários com dados dos bairros.

    Lógica:
        1. Se dados já estão no session_state, retorna direto (rápido)
        2. Se não, carrega do arquivo e armazena no session_state
    """
    if "dados_bairros" not in st.session_state or st.session_state.dados_bairros is None:
        st.session_state.dados_bairros = carregar_dados()

    return st.session_state.dados_bairros


def forcar_recarregamento_dados():
    """
    Força o recarregamento dos dados do arquivo JSON.

    Útil quando sabemos que o arquivo foi modificado externamente
    ou quando queremos garantir dados frescos.
    """
    st.session_state.dados_bairros = carregar_dados()
    return st.session_state.dados_bairros


# =============================================================================
# CAMADA DE SERVIÇO - INTEGRAÇÃO COM API EXTERNA
# =============================================================================
# Esta seção implementa a comunicação com a API REST da Open-Meteo.
# APIs REST utilizam o protocolo HTTP para troca de dados em formato JSON.

@st.cache_data(ttl=CACHE_TTL_SEGUNDOS, show_spinner=False)
def buscar_clima_api(lat, lon):
    """
    Consulta a API Open-Meteo para obter dados de temperatura e precipitação em tempo real.

    OTIMIZAÇÃO: Utiliza cache do Streamlit para evitar requisições repetidas.
    O cache expira após CACHE_TTL_SEGUNDOS (padrão: 120 segundos).

    Parâmetros:
        lat (float): Latitude do local (coordenada geográfica)
        lon (float): Longitude do local (coordenada geográfica)

    Retorno:
        dict: Dicionário com 'chuva' (mm) e 'temperatura' (°C).
              Retorna valores padrão em caso de erro na requisição.

    Funcionamento da API Open-Meteo:
        A API é gratuita e não requer autenticação (API Key).
        Endpoint utilizado: /v1/forecast
        Parâmetro 'current': Solicita dados meteorológicos atuais
        Parâmetros: rain (precipitação), temperature_2m (temperatura a 2m do solo)

    Tratamento de Erros:
        - requests.RequestException: Captura erros de conexão, timeout, etc.
        - KeyError: Resposta da API sem o campo esperado
    """
    # Montagem dos parâmetros da requisição HTTP GET
    # Aqui consumimos a API REST da Open-Meteo
    # CORREÇÃO: Usando 'precipitation' (inclui garoa/chuvisco) em vez de 'rain' (só chuva forte)
    # Também adicionamos precipitation_probability para mostrar chance de chuva
    parametros = {
        "latitude": lat,
        "longitude": lon,
        "current": "precipitation,temperature_2m",  # Precipitação total (não só chuva forte)
        "hourly": "precipitation,precipitation_probability",  # Dados horários para previsão
        "timezone": "America/Sao_Paulo",  # Fuso horário de Guarujá
        "forecast_days": 1  # Apenas hoje para reduzir dados
    }

    try:
        # Realiza a requisição HTTP GET para a API
        # timeout=10: Aguarda no máximo 10 segundos pela resposta
        resposta = requests.get(API_OPEN_METEO_URL, params=parametros, timeout=10)

        # Verifica se a requisição foi bem-sucedida (código HTTP 200)
        resposta.raise_for_status()

        # Converte a resposta JSON para dicionário Python
        dados_json = resposta.json()

        # Extrai os valores de precipitação e temperatura da estrutura de dados retornada
        # Estrutura: {"current": {"precipitation": 0.0, "temperature_2m": 25.0}, "hourly": {...}}
        current = dados_json.get("current", {})
        hourly = dados_json.get("hourly", {})

        # Precipitação atual (inclui chuva, garoa, chuvisco - mais preciso que só 'rain')
        precipitacao = current.get("precipitation", 0.0)
        temperatura = current.get("temperature_2m", 0.0)

        # Probabilidade de chuva: pega a hora atual dos dados horários
        # Os dados horários vêm em listas, pegamos o índice da hora atual
        probabilidades = hourly.get("precipitation_probability", [])
        precipitacoes_hora = hourly.get("precipitation", [])

        # Pega a hora atual para indexar os dados horários
        hora_atual = datetime.now().hour
        probabilidade = probabilidades[hora_atual] if hora_atual < len(probabilidades) else 0
        precip_proxima_hora = precipitacoes_hora[hora_atual] if hora_atual < len(precipitacoes_hora) else 0.0

        return {
            "chuva": precipitacao,
            "temperatura": temperatura,
            "probabilidade_chuva": probabilidade,
            "precipitacao_proxima_hora": precip_proxima_hora
        }

    except requests.RequestException as erro:
        # Log do erro para debugging (aparece no terminal do Streamlit)
        print(f"[ERRO API] Falha ao consultar Open-Meteo: {erro}")
        return {"chuva": 0.0, "temperatura": 0.0, "probabilidade_chuva": 0, "precipitacao_proxima_hora": 0.0}
    except (KeyError, TypeError, IndexError) as erro:
        print(f"[ERRO API] Resposta inesperada da API: {erro}")
        return {"chuva": 0.0, "temperatura": 0.0, "probabilidade_chuva": 0, "precipitacao_proxima_hora": 0.0}


def _buscar_clima_bairro(bairro):
    """
    Função auxiliar para buscar clima de um único bairro.
    Utilizada internamente pelo ThreadPoolExecutor para paralelização.

    Parâmetros:
        bairro (dict): Dicionário com dados do bairro (deve conter 'lat' e 'lon')

    Retorno:
        tuple: (id_bairro, dados_clima) para identificação posterior
    """
    clima = buscar_clima_api(bairro["lat"], bairro["lon"])
    return (bairro["id"], clima)


def atualizar_clima_todos_bairros(dados):
    """
    Atualiza os dados meteorológicos de todos os bairros consultando a API.

    OTIMIZAÇÃO: Utiliza ThreadPoolExecutor para fazer requisições em PARALELO,
    reduzindo o tempo de ~15 segundos (sequencial) para ~1-2 segundos.

    Esta função implementa a REGRA DE AUTOMAÇÃO 1 (API):
    Se a precipitação for superior a 10mm, o status é automaticamente
    alterado para "Risco Meteorológico", alertando a população.

    Parâmetros:
        dados (list): Lista de bairros a serem atualizados.

    Retorno:
        list: Lista de bairros com dados meteorológicos atualizados.

    Lógica de Negócio:
        - Consulta API para cada bairro (em paralelo)
        - Atualiza campo 'chuva_real' e 'temperatura' com valores retornados
        - Aplica regra de automação se chuva > LIMITE_CHUVA_RISCO
    """
    # Dicionário para armazenar resultados indexados por ID
    resultados_clima = {}

    # Executa requisições em paralelo usando ThreadPoolExecutor
    # MAX_WORKERS_API limita o número de conexões simultâneas
    with ThreadPoolExecutor(max_workers=MAX_WORKERS_API) as executor:
        # Submete todas as tarefas para execução paralela
        futures = {executor.submit(_buscar_clima_bairro, bairro): bairro for bairro in dados}

        # Coleta resultados à medida que ficam prontos
        for future in as_completed(futures):
            try:
                bairro_id, clima = future.result()
                resultados_clima[bairro_id] = clima
            except Exception as erro:
                print(f"[ERRO] Falha ao buscar clima: {erro}")

    # Atualiza os dados dos bairros com os resultados obtidos
    for bairro in dados:
        clima = resultados_clima.get(bairro["id"], {
            "chuva": 0.0,
            "temperatura": 0.0,
            "probabilidade_chuva": 0,
            "precipitacao_proxima_hora": 0.0
        })
        bairro["chuva_real"] = clima["chuva"]
        bairro["temperatura"] = clima["temperatura"]
        bairro["probabilidade_chuva"] = clima.get("probabilidade_chuva", 0)
        bairro["precipitacao_proxima_hora"] = clima.get("precipitacao_proxima_hora", 0.0)

        # REGRA DE AUTOMAÇÃO 1: Alerta automático por dados meteorológicos
        # Se a precipitação atual exceder o limite configurado (10mm), o sistema
        # automaticamente altera o status para alertar a população.
        # NOVO: Também alerta se probabilidade de chuva for muito alta (>80%)
        if clima["chuva"] > LIMITE_CHUVA_RISCO:
            bairro["status"] = "Risco Meteorológico"
            bairro["risco"] = "Alto"
        elif clima.get("probabilidade_chuva", 0) >= 80 and bairro["status"] == "Normal":
            bairro["status"] = "Atenção"
            bairro["risco"] = "Médio"

    return dados


# =============================================================================
# ATUALIZAÇÃO AUTOMÁTICA - FRAGMENTO STREAMLIT
# =============================================================================
# O decorator @st.fragment com run_every permite executar esta função
# automaticamente em intervalos regulares sem recarregar toda a página.
# Isso mantém os dados meteorológicos sempre atualizados.

@st.fragment(run_every=timedelta(minutes=INTERVALO_ATUALIZACAO))
def atualizar_clima_automatico():
    """
    Fragmento que atualiza automaticamente os dados meteorológicos.

    Executa a cada INTERVALO_ATUALIZACAO minutos (padrão: 10 minutos).
    Utiliza o recurso de fragmentos do Streamlit para atualização parcial
    da página, evitando recarregamento completo da interface.

    OTIMIZAÇÕES APLICADAS:
        - Usa obter_dados_otimizado() para evitar leitura desnecessária do JSON
        - Chamadas de API em paralelo via ThreadPoolExecutor
        - Cache nas requisições individuais

    Benefícios:
        - Dados sempre atualizados sem intervenção do usuário
        - Não interfere na navegação do usuário
        - Eficiente em termos de recursos (atualiza apenas o necessário)
    """
    dados = obter_dados_otimizado()

    if dados:
        dados = atualizar_clima_todos_bairros(dados)
        salvar_dados(dados)

        # Armazena timestamp da última atualização automática
        st.session_state.ultima_atualizacao_auto = datetime.now()


# =============================================================================
# CAMADA DE APRESENTAÇÃO - FUNÇÕES AUXILIARES DE UI
# =============================================================================
# Funções que auxiliam na renderização da interface do usuário.

def obter_cor_status(status):
    """
    Retorna a cor correspondente ao status do bairro para feedback visual.

    Parâmetros:
        status (str): Status atual do bairro.

    Retorno:
        str: Nome da cor em inglês (usado pelo Streamlit).

    Design de UX:
        Utilizamos o padrão semafórico (verde/amarelo/vermelho) que é
        universalmente compreendido, facilitando a interpretação rápida.
    """
    mapeamento_cores = {
        "Normal": "green",           # Verde: Situação segura
        "Atenção": "orange",         # Amarelo/Laranja: Requer atenção
        "Risco Meteorológico": "orange",
        "ALAGADO CONFIRMADO": "red", # Vermelho: Situação crítica
        "Crítico": "red"
    }
    return mapeamento_cores.get(status, "gray")


def obter_emoji_status(status):
    """
    Retorna um emoji representativo do status para melhorar a comunicação visual.

    Parâmetros:
        status (str): Status atual do bairro.

    Retorno:
        str: Emoji correspondente ao status.
    """
    mapeamento_emojis = {
        "Normal": "✅",
        "Atenção": "⚠️",
        "Risco Meteorológico": "🌧️",
        "ALAGADO CONFIRMADO": "🚨",
        "Crítico": "🚨"
    }
    return mapeamento_emojis.get(status, "❓")


# =============================================================================
# FUNÇÃO PRINCIPAL - RENDERIZAÇÃO DA APLICAÇÃO
# =============================================================================

def main():
    """
    Função principal que orquestra toda a renderização da aplicação Streamlit.

    Estrutura da Interface:
        1. Cabeçalho com título e descrição
        2. Sidebar com seleção de bairro e controles administrativos
        3. Área principal dividida em duas colunas:
           - Coluna 1: Painel detalhado do bairro selecionado
           - Coluna 2: Mapa geral da cidade com todos os bairros
    """

    # =========================================================================
    # ATUALIZAÇÃO AUTOMÁTICA DO CLIMA
    # =========================================================================
    # Chama o fragmento que executa automaticamente a cada X minutos
    atualizar_clima_automatico()

    # =========================================================================
    # CABEÇALHO DA APLICAÇÃO
    # =========================================================================
    st.title("🌊 Monitor de Alagamentos - Guarujá/SP")
    st.markdown("""
    **Sistema Colaborativo de Monitoramento** | Dados em tempo real + Reportes da Comunidade

    ---
    """)

    # =========================================================================
    # CARREGAMENTO DOS DADOS (OTIMIZADO)
    # =========================================================================
    # Usa session_state para evitar releituras desnecessárias do arquivo JSON
    dados = obter_dados_otimizado()

    # Verifica se os dados foram carregados corretamente
    if not dados:
        st.warning("⚠️ Nenhum dado disponível. Execute o script de setup primeiro.")
        st.code("python resetar_bairros.py", language="bash")
        st.stop()  # Interrompe a execução se não há dados

    # Cria lista de nomes de bairros para o seletor
    nomes_bairros = [bairro["nome"] for bairro in dados]

    # =========================================================================
    # SIDEBAR - MENU LATERAL
    # =========================================================================
    # A sidebar é ideal para controles e filtros que não são o foco principal.
    with st.sidebar:
        st.header("📍 Selecione seu Bairro")

        # Selectbox: Componente de seleção dropdown
        # Permite ao usuário escolher em qual bairro ele está localizado
        bairro_selecionado_nome = st.selectbox(
            "Bairro:",
            options=nomes_bairros,
            help="Escolha o bairro para visualizar detalhes e reportar alagamentos"
        )

        st.markdown("---")

        # =====================================================================
        # PAINEL ADMINISTRATIVO
        # =====================================================================
        st.header("⚙️ Painel Admin")

        # Botão para atualização manual dos dados meteorológicos
        # Em produção, isso poderia ser automatizado com agendamento (cron)
        if st.button("🔄 Atualizar Clima (API)", use_container_width=True):
            # Exibe spinner durante a operação (feedback visual)
            with st.spinner("Consultando API Open-Meteo..."):
                # Limpa o cache da API para forçar requisições frescas
                buscar_clima_api.clear()
                dados = atualizar_clima_todos_bairros(dados)
                salvar_dados(dados)

            # Toast: Notificação temporária não-intrusiva
            st.toast("✅ Dados meteorológicos atualizados!", icon="🌤️")
            # Rerun força atualização da página com novos dados
            st.rerun()

        # Botão para resetar todos os votos (útil para testes/demonstrações)
        if st.button("🗑️ Resetar Votos", use_container_width=True):
            for bairro in dados:
                bairro["votos"] = 0
                bairro["status"] = "Normal"
                bairro["risco"] = "Baixo"
            salvar_dados(dados)
            st.toast("✅ Votos resetados!", icon="🔄")
            st.rerun()

        st.markdown("---")

        # Informações do sistema
        st.caption("ℹ️ **Sobre o Sistema**")

        # Exibe informação sobre atualização automática
        st.caption(f"🔄 **Atualização automática:** a cada {INTERVALO_ATUALIZACAO} min")

        # Mostra última atualização automática se disponível
        if "ultima_atualizacao_auto" in st.session_state and st.session_state.ultima_atualizacao_auto:
            ultima = st.session_state.ultima_atualizacao_auto.strftime('%H:%M:%S')
            st.caption(f"⏱️ Última atualização: {ultima}")
        else:
            st.caption(f"⏱️ Última atualização: {datetime.now().strftime('%H:%M:%S')}")

        st.caption(f"📍 Total de bairros: {len(dados)}")

    # =========================================================================
    # LOCALIZA O BAIRRO SELECIONADO NOS DADOS
    # =========================================================================
    # Utiliza compreensão de lista com filtro para encontrar o bairro
    bairro_atual = next(
        (b for b in dados if b["nome"] == bairro_selecionado_nome),
        None
    )

    if not bairro_atual:
        st.error("Erro ao localizar bairro selecionado.")
        st.stop()

    # =========================================================================
    # ÁREA PRINCIPAL - LAYOUT EM DUAS COLUNAS
    # =========================================================================
    # st.columns() cria um layout responsivo em colunas
    # [1.2, 1] significa proporção 1.2:1 (primeira coluna levemente maior)
    col_painel, col_mapa = st.columns([1.2, 1])

    # =========================================================================
    # COLUNA 1: PAINEL DO BAIRRO SELECIONADO
    # =========================================================================
    with col_painel:
        st.subheader(f"📊 Painel: {bairro_atual['nome']}")

        # Obtém cor e emoji baseados no status atual
        cor_status = obter_cor_status(bairro_atual["status"])
        emoji_status = obter_emoji_status(bairro_atual["status"])

        # Exibe status com formatação colorida usando HTML inline
        # O parâmetro unsafe_allow_html=True permite renderizar HTML
        st.markdown(
            f"""
            <div style="
                background-color: {cor_status};
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                margin-bottom: 20px;
            ">
                <h2 style="color: white; margin: 0;">
                    {emoji_status} {bairro_atual['status']}
                </h2>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Métricas em linha usando colunas internas
        # st.metric() exibe valores com destaque visual
        metrica_col1, metrica_col2, metrica_col3, metrica_col4, metrica_col5 = st.columns(5)

        with metrica_col1:
            st.metric(
                label="🌡️ Temperatura",
                value=f"{bairro_atual.get('temperatura', 0):.1f} °C",
                help="Temperatura atual obtida da API Open-Meteo"
            )

        with metrica_col2:
            st.metric(
                label="🌧️ Chuva Agora",
                value=f"{bairro_atual.get('chuva_real', 0):.1f} mm",
                help="Precipitação atual (inclui chuva, garoa, chuvisco)"
            )

        with metrica_col3:
            # NOVO: Probabilidade de chuva
            prob_chuva = bairro_atual.get('probabilidade_chuva', 0)
            st.metric(
                label="🎲 Chance Chuva",
                value=f"{prob_chuva}%",
                help="Probabilidade de precipitação na próxima hora"
            )

        with metrica_col4:
            st.metric(
                label="📢 Reportes",
                value=bairro_atual.get("votos", 0),
                help="Número de reportes da comunidade"
            )

        with metrica_col5:
            st.metric(
                label="⚡ Risco",
                value=bairro_atual.get("risco", "Baixo"),
                help="Classificação de risco atual"
            )

        st.markdown("---")

        # =====================================================================
        # BOTÃO DE REPORTE - CROWDSOURCING
        # =====================================================================
        st.subheader("🚨 Reportar Situação")
        st.caption("Ajude a comunidade informando sobre alagamentos no seu bairro!")

        # Botão principal de reporte
        if st.button(
            "🌊 REPORTAR ALAGAMENTO",
            type="primary",  # Botão em destaque (azul)
            use_container_width=True
        ):
            # Incrementa contador de votos (Crowdsourcing)
            bairro_atual["votos"] += 1

            # =================================================================
            # REGRA DE AUTOMAÇÃO 2 (CROWDSOURCING)
            # Aqui aplicamos a lógica de validação colaborativa:
            # Quando o número de reportes atinge o limite configurado (5),
            # o sistema confirma automaticamente o alagamento.
            # Esta abordagem evita falsos positivos de reportes isolados.
            # =================================================================
            if bairro_atual["votos"] >= LIMITE_VOTOS_ALAGAMENTO:
                bairro_atual["status"] = "ALAGADO CONFIRMADO"
                bairro_atual["risco"] = "Crítico"
                st.toast("🚨 ALAGAMENTO CONFIRMADO pela comunidade!", icon="⚠️")
            else:
                # Atualiza para "Atenção" se houver pelo menos 1 reporte
                if bairro_atual["status"] == "Normal":
                    bairro_atual["status"] = "Atenção"
                    bairro_atual["risco"] = "Médio"
                st.toast(
                    f"✅ Reporte registrado! ({bairro_atual['votos']}/{LIMITE_VOTOS_ALAGAMENTO})",
                    icon="📢"
                )

            # Persiste as alterações no arquivo JSON
            salvar_dados(dados)

            # Atualiza a interface para refletir mudanças
            st.rerun()

        # Barra de progresso visual dos votos
        progresso = min(bairro_atual["votos"] / LIMITE_VOTOS_ALAGAMENTO, 1.0)
        st.progress(progresso, text=f"Votos: {bairro_atual['votos']}/{LIMITE_VOTOS_ALAGAMENTO}")

        # Coordenadas do bairro (informativo)
        with st.expander("📍 Coordenadas do Bairro"):
            st.write(f"**Latitude:** {bairro_atual['lat']}")
            st.write(f"**Longitude:** {bairro_atual['lon']}")

    # =========================================================================
    # COLUNA 2: MAPA GERAL DA CIDADE
    # =========================================================================
    with col_mapa:
        st.subheader("🗺️ Mapa de Guarujá")

        # =====================================================================
        # PREPARAÇÃO DOS DADOS PARA O MAPA
        # =====================================================================
        # O componente st.map() requer um DataFrame pandas com colunas
        # específicas: 'lat', 'lon' e opcionalmente 'size' para tamanho.

        # Criamos uma lista de dicionários com os dados necessários
        dados_mapa = []
        for bairro in dados:
            # Calcula o tamanho da bolinha baseado nos votos
            # Fórmula: tamanho base (100) + votos * multiplicador (80)
            # Isso cria visualização proporcional ao número de reportes
            tamanho = 100 + (bairro["votos"] * 80)

            dados_mapa.append({
                "lat": bairro["lat"],
                "lon": bairro["lon"],
                "size": tamanho
            })

        # Converte para DataFrame do Pandas
        # DataFrame é a estrutura de dados tabular do Pandas
        df_mapa = pd.DataFrame(dados_mapa)

        # Renderiza o mapa com st.map()
        # O parâmetro 'size' controla o tamanho dos marcadores
        st.map(df_mapa, size="size", zoom=11)

        # Legenda explicativa do mapa
        st.caption("📌 **Legenda:** Círculos maiores = Mais reportes de alagamento")

        # =====================================================================
        # TABELA RESUMO DE TODOS OS BAIRROS
        # =====================================================================
        st.markdown("---")
        st.subheader("📋 Resumo Geral")

        # Prepara dados para tabela resumo
        dados_tabela = []
        for bairro in dados:
            emoji = obter_emoji_status(bairro["status"])
            dados_tabela.append({
                "Bairro": bairro["nome"],
                "Status": f"{emoji} {bairro['status']}",
                "Temp (°C)": f"{bairro.get('temperatura', 0):.1f}",
                "Chuva (mm)": f"{bairro.get('chuva_real', 0):.1f}",
                "Prob (%)": f"{bairro.get('probabilidade_chuva', 0)}",
                "Reportes": bairro.get("votos", 0)
            })

        # Cria e exibe DataFrame como tabela
        df_resumo = pd.DataFrame(dados_tabela)

        # st.dataframe() renderiza uma tabela interativa
        st.dataframe(
            df_resumo,
            use_container_width=True,
            hide_index=True  # Oculta índice numérico
        )

    # =========================================================================
    # RODAPÉ DA APLICAÇÃO
    # =========================================================================
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: gray; font-size: 12px;">
            🎓 <b>Projeto Integrador</b> | Sistema de Monitoramento de Alagamentos<br>
            Desenvolvido com Python + Streamlit | API: Open-Meteo<br>
            Guarujá/SP - 2024
        </div>
        """,
        unsafe_allow_html=True
    )


# =============================================================================
# PONTO DE ENTRADA DA APLICAÇÃO
# =============================================================================
# Verifica se o script está sendo executado diretamente (não importado)
# e chama a função principal.
if __name__ == "__main__":
    main()
