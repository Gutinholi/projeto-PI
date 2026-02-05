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

# Pydeck: Biblioteca para visualização de mapas interativos com WebGL.
# Permite criar mapas com marcadores coloridos por status.
# Documentação: https://pydeck.gl/
import pydeck as pdk

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


@st.cache_data(ttl=CACHE_TTL_SEGUNDOS, show_spinner=False)
def buscar_previsao_horaria(lat, lon):
    """
    Busca previsão horária de precipitação para as próximas 24 horas.

    Utilizado para gerar o gráfico de previsão de chuva.

    Parâmetros:
        lat (float): Latitude do local
        lon (float): Longitude do local

    Retorno:
        dict: Dicionário com listas de horas, precipitação e probabilidade
    """
    parametros = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation,precipitation_probability",
        "timezone": "America/Sao_Paulo",
        "forecast_days": 1
    }

    try:
        resposta = requests.get(API_OPEN_METEO_URL, params=parametros, timeout=10)
        resposta.raise_for_status()
        dados_json = resposta.json()

        hourly = dados_json.get("hourly", {})

        # Extrai os horários e formata para exibição (apenas hora)
        horarios_raw = hourly.get("time", [])
        horarios = [h.split("T")[1][:5] for h in horarios_raw]  # "2026-02-05T14:00" -> "14:00"

        precipitacoes = hourly.get("precipitation", [])
        probabilidades = hourly.get("precipitation_probability", [])

        return {
            "horarios": horarios,
            "precipitacao": precipitacoes,
            "probabilidade": probabilidades
        }

    except Exception as erro:
        print(f"[ERRO API] Falha ao buscar previsão horária: {erro}")
        return {
            "horarios": [],
            "precipitacao": [],
            "probabilidade": []
        }


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


def obter_cor_rgb_status(status):
    """
    Retorna a cor RGB correspondente ao status para uso no mapa pydeck.

    Parâmetros:
        status (str): Status atual do bairro.

    Retorno:
        list: Lista com valores [R, G, B, A] (0-255)
    """
    mapeamento_cores_rgb = {
        "Normal": [40, 167, 69, 200],           # Verde
        "Atenção": [255, 193, 7, 200],          # Amarelo
        "Risco Meteorológico": [253, 126, 20, 200],  # Laranja
        "ALAGADO CONFIRMADO": [220, 53, 69, 200],    # Vermelho
        "Crítico": [220, 53, 69, 200]           # Vermelho
    }
    return mapeamento_cores_rgb.get(status, [128, 128, 128, 200])


# =============================================================================
# FUNÇÃO PRINCIPAL - RENDERIZAÇÃO DA APLICAÇÃO
# =============================================================================

def main():
    """
    Função principal que orquestra toda a renderização da aplicação Streamlit.

    Estrutura da Interface (REDESIGN v2.0):
        1. Cabeçalho compacto
        2. Resumo da cidade (cards de status)
        3. Seletor de bairro na área principal
        4. Painel do bairro com métricas e ações
        5. Abas para Previsão/Mapa/Tabela
        6. Sidebar apenas para admin (escondido)
    """

    # =========================================================================
    # ATUALIZAÇÃO AUTOMÁTICA DO CLIMA
    # =========================================================================
    atualizar_clima_automatico()

    # =========================================================================
    # CABEÇALHO COMPACTO
    # =========================================================================
    st.markdown("""
        <h1 style='text-align: center; margin-bottom: 0;'>🌊 Monitor de Alagamentos</h1>
        <p style='text-align: center; color: gray; margin-top: 0;'>Guarujá/SP • Dados em tempo real</p>
    """, unsafe_allow_html=True)

    # =========================================================================
    # CARREGAMENTO DOS DADOS (OTIMIZADO)
    # =========================================================================
    dados = obter_dados_otimizado()

    if not dados:
        st.warning("⚠️ Nenhum dado disponível. Execute o script de setup primeiro.")
        st.code("python resetar_bairros.py", language="bash")
        st.stop()

    # =========================================================================
    # RESUMO DA CIDADE - CARDS DE STATUS
    # =========================================================================
    # Conta bairros por status para visão geral
    contagem_normal = sum(1 for b in dados if b["status"] == "Normal")
    contagem_atencao = sum(1 for b in dados if b["status"] == "Atenção")
    contagem_risco = sum(1 for b in dados if b["status"] == "Risco Meteorológico")
    contagem_alagado = sum(1 for b in dados if b["status"] == "ALAGADO CONFIRMADO")

    st.markdown("### 📊 Situação Atual da Cidade")

    col_r1, col_r2, col_r3, col_r4 = st.columns(4)

    with col_r1:
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #28a745, #20c997); padding: 15px; border-radius: 10px; text-align: center;">
                <h2 style="color: white; margin: 0;">{contagem_normal}</h2>
                <p style="color: white; margin: 0; font-size: 14px;">🟢 Normais</p>
            </div>
        """, unsafe_allow_html=True)

    with col_r2:
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #ffc107, #fd7e14); padding: 15px; border-radius: 10px; text-align: center;">
                <h2 style="color: white; margin: 0;">{contagem_atencao}</h2>
                <p style="color: white; margin: 0; font-size: 14px;">🟡 Atenção</p>
            </div>
        """, unsafe_allow_html=True)

    with col_r3:
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #fd7e14, #e65100); padding: 15px; border-radius: 10px; text-align: center;">
                <h2 style="color: white; margin: 0;">{contagem_risco}</h2>
                <p style="color: white; margin: 0; font-size: 14px;">🟠 Risco</p>
            </div>
        """, unsafe_allow_html=True)

    with col_r4:
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #dc3545, #c82333); padding: 15px; border-radius: 10px; text-align: center;">
                <h2 style="color: white; margin: 0;">{contagem_alagado}</h2>
                <p style="color: white; margin: 0; font-size: 14px;">🔴 Alagados</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # =========================================================================
    # SELETOR DE BAIRRO - ÁREA PRINCIPAL
    # =========================================================================
    nomes_bairros = [bairro["nome"] for bairro in dados]

    st.markdown("### 📍 Selecione seu Bairro")
    bairro_selecionado_nome = st.selectbox(
        "Escolha o bairro para ver detalhes e reportar:",
        options=nomes_bairros,
        label_visibility="collapsed"
    )

    # =========================================================================
    # SIDEBAR - APENAS ADMIN (ESCONDIDO)
    # =========================================================================
    with st.sidebar:
        st.markdown("### ⚙️ Painel Administrativo")

        with st.expander("🔧 Controles Admin", expanded=False):
            # Botão para atualização manual dos dados meteorológicos
            if st.button("🔄 Atualizar Clima (API)", use_container_width=True):
                with st.spinner("Consultando API Open-Meteo..."):
                    buscar_clima_api.clear()
                    dados = atualizar_clima_todos_bairros(dados)
                    salvar_dados(dados)
                st.toast("✅ Dados meteorológicos atualizados!", icon="🌤️")
                st.rerun()

            # Botão para resetar todos os votos
            if st.button("🗑️ Resetar Votos", use_container_width=True):
                for bairro in dados:
                    bairro["votos"] = 0
                    bairro["status"] = "Normal"
                    bairro["risco"] = "Baixo"
                salvar_dados(dados)
                st.toast("✅ Votos resetados!", icon="🔄")
                st.rerun()

        # Informações do sistema na sidebar
        st.markdown("---")
        st.caption(f"🔄 Atualização: a cada {INTERVALO_ATUALIZACAO} min")
        if "ultima_atualizacao_auto" in st.session_state and st.session_state.ultima_atualizacao_auto:
            ultima = st.session_state.ultima_atualizacao_auto.strftime('%H:%M:%S')
            st.caption(f"⏱️ Última: {ultima}")
        st.caption(f"📍 {len(dados)} bairros monitorados")

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
    # PAINEL DO BAIRRO SELECIONADO
    # =========================================================================
    cor_status = obter_cor_status(bairro_atual["status"])
    emoji_status = obter_emoji_status(bairro_atual["status"])

    # Card de status principal - grande e destacado
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {cor_status}, {cor_status}dd);
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            margin: 20px 0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        ">
            <h1 style="color: white; margin: 0; font-size: 2.5em;">
                {emoji_status} {bairro_atual['status']}
            </h1>
            <p style="color: white; margin: 10px 0 0 0; font-size: 1.2em; opacity: 0.9;">
                📍 {bairro_atual['nome']}
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # =========================================================================
    # MÉTRICAS EM 3 COLUNAS (MOBILE-FRIENDLY)
    # =========================================================================
    col_m1, col_m2, col_m3 = st.columns(3)

    with col_m1:
        st.metric(
            label="🌡️ Temperatura",
            value=f"{bairro_atual.get('temperatura', 0):.1f} °C"
        )

    with col_m2:
        st.metric(
            label="🌧️ Chuva Agora",
            value=f"{bairro_atual.get('chuva_real', 0):.1f} mm"
        )

    with col_m3:
        prob_chuva = bairro_atual.get('probabilidade_chuva', 0)
        st.metric(
            label="🎲 Chance de Chuva",
            value=f"{prob_chuva}%"
        )

    # =========================================================================
    # BOTÃO DE REPORTE - GRANDE E DESTACADO
    # =========================================================================
    st.markdown("<br>", unsafe_allow_html=True)

    # Mostra quantos votos faltam
    votos_faltam = LIMITE_VOTOS_ALAGAMENTO - bairro_atual.get("votos", 0)
    if votos_faltam > 0:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #dc3545, #c82333);
                padding: 20px;
                border-radius: 15px;
                text-align: center;
                margin-bottom: 10px;
                cursor: pointer;
            ">
                <h2 style="color: white; margin: 0;">🚨 REPORTAR ALAGAMENTO</h2>
                <p style="color: white; margin: 5px 0 0 0; opacity: 0.9;">
                    Clique abaixo se há alagamento neste bairro
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Botão funcional
    if st.button(
        f"🌊 CONFIRMAR REPORTE ({bairro_atual.get('votos', 0)}/{LIMITE_VOTOS_ALAGAMENTO} confirmações)",
        type="primary",
        use_container_width=True
    ):
        bairro_atual["votos"] += 1

        if bairro_atual["votos"] >= LIMITE_VOTOS_ALAGAMENTO:
            bairro_atual["status"] = "ALAGADO CONFIRMADO"
            bairro_atual["risco"] = "Crítico"
            st.toast("🚨 ALAGAMENTO CONFIRMADO pela comunidade!", icon="⚠️")
        else:
            if bairro_atual["status"] == "Normal":
                bairro_atual["status"] = "Atenção"
                bairro_atual["risco"] = "Médio"
            st.toast(
                f"✅ Reporte registrado! ({bairro_atual['votos']}/{LIMITE_VOTOS_ALAGAMENTO})",
                icon="📢"
            )

        salvar_dados(dados)
        st.rerun()

    # Barra de progresso visual
    progresso = min(bairro_atual["votos"] / LIMITE_VOTOS_ALAGAMENTO, 1.0)
    st.progress(progresso)

    # =========================================================================
    # ABAS - PREVISÃO / MAPA / TODOS OS BAIRROS
    # =========================================================================
    st.markdown("---")

    tab_previsao, tab_mapa, tab_todos = st.tabs(["📈 Previsão 24h", "🗺️ Mapa", "📋 Todos os Bairros"])

    # ----- ABA 1: PREVISÃO HORÁRIA -----
    with tab_previsao:
        previsao = buscar_previsao_horaria(bairro_atual["lat"], bairro_atual["lon"])

        if previsao["horarios"]:
            df_previsao = pd.DataFrame({
                "Horário": previsao["horarios"],
                "Precipitação (mm)": previsao["precipitacao"],
                "Probabilidade (%)": previsao["probabilidade"]
            })

            st.bar_chart(
                df_previsao.set_index("Horário")["Precipitação (mm)"],
                color="#1E90FF"
            )

            with st.expander("📊 Ver dados detalhados"):
                st.dataframe(df_previsao, hide_index=True)
        else:
            st.warning("Não foi possível carregar a previsão horária.")

    # ----- ABA 2: MAPA COM CORES POR STATUS -----
    with tab_mapa:
        # Prepara dados com cores baseadas no status
        dados_mapa = []
        for bairro in dados:
            cor = obter_cor_rgb_status(bairro["status"])
            raio = 300 + (bairro["votos"] * 100)  # Raio base + votos
            dados_mapa.append({
                "lat": bairro["lat"],
                "lon": bairro["lon"],
                "nome": bairro["nome"],
                "status": bairro["status"],
                "cor": cor,
                "raio": raio
            })

        df_mapa = pd.DataFrame(dados_mapa)

        # Camada de círculos coloridos
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_mapa,
            get_position=["lon", "lat"],
            get_color="cor",
            get_radius="raio",
            pickable=True,
            opacity=0.8,
            stroked=True,
            line_width_min_pixels=2,
        )

        # Configuração da visualização do mapa
        view_state = pdk.ViewState(
            latitude=-23.97,
            longitude=-46.26,
            zoom=11,
            pitch=0,
        )

        # Renderiza o mapa
        st.pydeck_chart(pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={"text": "{nome}\n{status}"}
        ))

        # Legenda de cores
        st.markdown("""
            <div style="display: flex; justify-content: center; gap: 15px; margin-top: 10px; flex-wrap: wrap;">
                <span style="display: flex; align-items: center; gap: 5px;">
                    <div style="width: 15px; height: 15px; background: #28a745; border-radius: 50%;"></div>
                    <small>Normal</small>
                </span>
                <span style="display: flex; align-items: center; gap: 5px;">
                    <div style="width: 15px; height: 15px; background: #ffc107; border-radius: 50%;"></div>
                    <small>Atenção</small>
                </span>
                <span style="display: flex; align-items: center; gap: 5px;">
                    <div style="width: 15px; height: 15px; background: #fd7e14; border-radius: 50%;"></div>
                    <small>Risco</small>
                </span>
                <span style="display: flex; align-items: center; gap: 5px;">
                    <div style="width: 15px; height: 15px; background: #dc3545; border-radius: 50%;"></div>
                    <small>Alagado</small>
                </span>
            </div>
        """, unsafe_allow_html=True)

    # ----- ABA 3: TODOS OS BAIRROS -----
    with tab_todos:
        dados_tabela = []
        for bairro in dados:
            emoji = obter_emoji_status(bairro["status"])
            dados_tabela.append({
                "Bairro": bairro["nome"],
                "Status": f"{emoji} {bairro['status']}",
                "Temp": f"{bairro.get('temperatura', 0):.1f}°C",
                "Chuva": f"{bairro.get('chuva_real', 0):.1f}mm",
                "Prob": f"{bairro.get('probabilidade_chuva', 0)}%",
                "Votos": bairro.get("votos", 0)
            })

        df_resumo = pd.DataFrame(dados_tabela)
        st.dataframe(df_resumo, hide_index=True)

    # =========================================================================
    # RODAPÉ DA APLICAÇÃO
    # =========================================================================
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: gray; font-size: 12px;">
            🎓 <b>Projeto Integrador</b> | Sistema de Monitoramento de Alagamentos<br>
            Python + Streamlit | API: Open-Meteo | Guarujá/SP
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
