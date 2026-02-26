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

# Plotly: Biblioteca para criação de gráficos interativos.
# Usamos para o gráfico de previsão horária com área e linhas.
# Documentação: https://plotly.com/python/
import plotly.graph_objects as go

# Datetime: Módulo nativo para manipulação de datas e horários.
# Utilizado para registrar timestamps das atualizações.
# timedelta: Utilizado para definir intervalos de tempo na atualização automática.
from datetime import datetime, timedelta, timezone

# Zoneinfo: Módulo para manipulação de fusos horários (Python 3.9+)
# Utilizado para garantir que todos os horários estejam em UTC-3 (Brasília)
try:
    from zoneinfo import ZoneInfo
    FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")
except ImportError:
    # Fallback para sistemas sem zoneinfo
    FUSO_BRASILIA = timezone(timedelta(hours=-3))

# OS: Módulo nativo para interação com o sistema operacional.
# Utilizado para obter o caminho absoluto do diretório do script.
import os

# concurrent.futures: Módulo para execução paralela de tarefas.
# Utilizado para fazer múltiplas requisições de API simultaneamente,
# reduzindo drasticamente o tempo de atualização dos dados meteorológicos.
from concurrent.futures import ThreadPoolExecutor, as_completed

# Supabase: Cliente Python para o Supabase (PostgreSQL na nuvem).
# Utilizado para persistência de dados sincronizada entre usuários.
# Documentação: https://supabase.com/docs/reference/python/introduction
from supabase import create_client, Client

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
INTERVALO_ATUALIZACAO = 1     # Intervalo em minutos para atualização automática do clima
MAX_WORKERS_API = 5           # Número máximo de requisições paralelas à API
CACHE_TTL_SEGUNDOS = 60       # Tempo de vida do cache em segundos (1 minuto)

# URL base da API Open-Meteo (serviço gratuito de dados meteorológicos)
# Documentação: https://open-meteo.com/en/docs
API_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# =============================================================================
# MAPEAMENTO DE WEATHER CODES (WMO)
# =============================================================================
# Códigos padronizados pela Organização Meteorológica Mundial (WMO)
# Usados para identificar condições climáticas e calcular risco de alagamento

WEATHER_CODES = {
    0: {"descricao": "Céu limpo", "emoji": "☀️", "risco": 0},
    1: {"descricao": "Principalmente limpo", "emoji": "🌤️", "risco": 0},
    2: {"descricao": "Parcialmente nublado", "emoji": "⛅", "risco": 0},
    3: {"descricao": "Nublado", "emoji": "☁️", "risco": 0},
    45: {"descricao": "Neblina", "emoji": "🌫️", "risco": 0},
    48: {"descricao": "Neblina com geada", "emoji": "🌫️", "risco": 0},
    51: {"descricao": "Garoa leve", "emoji": "🌦️", "risco": 1},
    53: {"descricao": "Garoa moderada", "emoji": "🌦️", "risco": 1},
    55: {"descricao": "Garoa intensa", "emoji": "🌧️", "risco": 2},
    56: {"descricao": "Garoa congelante leve", "emoji": "🌨️", "risco": 1},
    57: {"descricao": "Garoa congelante intensa", "emoji": "🌨️", "risco": 2},
    61: {"descricao": "Chuva leve", "emoji": "🌧️", "risco": 2},
    63: {"descricao": "Chuva moderada", "emoji": "🌧️", "risco": 3},
    65: {"descricao": "Chuva forte", "emoji": "🌧️", "risco": 4},
    66: {"descricao": "Chuva congelante leve", "emoji": "🌨️", "risco": 2},
    67: {"descricao": "Chuva congelante forte", "emoji": "🌨️", "risco": 3},
    71: {"descricao": "Neve leve", "emoji": "🌨️", "risco": 1},
    73: {"descricao": "Neve moderada", "emoji": "🌨️", "risco": 2},
    75: {"descricao": "Neve forte", "emoji": "❄️", "risco": 2},
    77: {"descricao": "Grãos de neve", "emoji": "❄️", "risco": 1},
    80: {"descricao": "Pancadas leves", "emoji": "🌦️", "risco": 2},
    81: {"descricao": "Pancadas moderadas", "emoji": "🌧️", "risco": 3},
    82: {"descricao": "Pancadas violentas", "emoji": "⛈️", "risco": 5},
    85: {"descricao": "Pancadas de neve leves", "emoji": "🌨️", "risco": 2},
    86: {"descricao": "Pancadas de neve fortes", "emoji": "❄️", "risco": 3},
    95: {"descricao": "Tempestade", "emoji": "⛈️", "risco": 5},
    96: {"descricao": "Tempestade com granizo leve", "emoji": "⛈️", "risco": 5},
    99: {"descricao": "Tempestade com granizo forte", "emoji": "⛈️", "risco": 5},
}


def obter_info_weather_code(code):
    """
    Retorna informações sobre o código de clima (WMO Weather Code).

    Parâmetros:
        code (int): Código de clima da API Open-Meteo

    Retorno:
        dict: Dicionário com descrição, emoji e nível de risco (0-5)
    """
    return WEATHER_CODES.get(code, {"descricao": "Desconhecido", "emoji": "❓", "risco": 0})


def calcular_risco_alagamento(clima_data):
    """
    Calcula o nível de risco de alagamento baseado em múltiplos fatores.

    Combina dados de precipitação, weather_code, umidade e tipo de chuva
    para uma avaliação mais precisa do risco.

    Parâmetros:
        clima_data (dict): Dados climáticos retornados por buscar_clima_api()

    Retorno:
        tuple: (nivel_risco: str, pontuacao: int)
               nivel_risco: "Baixo", "Médio", "Alto" ou "Crítico"
               pontuacao: 0-100 representando a gravidade
    """
    pontuacao = 0

    # Fator 1: Precipitação atual (peso alto)
    precipitacao = clima_data.get("chuva", 0.0)
    if precipitacao > 20:
        pontuacao += 40
    elif precipitacao > 10:
        pontuacao += 30
    elif precipitacao > 5:
        pontuacao += 20
    elif precipitacao > 0:
        pontuacao += 10

    # Fator 2: Pancadas de chuva (peso alto - causa alagamentos rápidos)
    showers = clima_data.get("showers", 0.0)
    if showers > 10:
        pontuacao += 25
    elif showers > 5:
        pontuacao += 15
    elif showers > 0:
        pontuacao += 5

    # Fator 3: Weather code (peso médio)
    weather_code = clima_data.get("weather_code", 0)
    info_clima = obter_info_weather_code(weather_code)
    pontuacao += info_clima["risco"] * 5  # 0-25 pontos

    # Fator 4: Umidade do ar (peso baixo - solo saturado)
    umidade = clima_data.get("umidade", 0)
    if umidade > 90:
        pontuacao += 10
    elif umidade > 80:
        pontuacao += 5

    # Fator 5: Probabilidade de chuva nas próximas horas
    prob_max = clima_data.get("prob_max_dia", 0)
    if prob_max > 80:
        pontuacao += 10
    elif prob_max > 60:
        pontuacao += 5

    # Classifica o risco
    if pontuacao >= 60:
        return ("Crítico", pontuacao)
    elif pontuacao >= 40:
        return ("Alto", pontuacao)
    elif pontuacao >= 20:
        return ("Médio", pontuacao)
    else:
        return ("Baixo", pontuacao)


def agora_brasilia():
    """
    Retorna o horário atual no fuso horário de Brasília (UTC-3).

    Utiliza zoneinfo para garantir consistência em todas as operações
    de data/hora do sistema, independente do timezone do servidor.
    """
    return datetime.now(FUSO_BRASILIA)

# =============================================================================
# CONEXÃO COM SUPABASE
# =============================================================================
# Inicializa a conexão com o banco de dados Supabase usando as credenciais
# armazenadas nos secrets do Streamlit (não ficam no código).

@st.cache_resource
def get_supabase_client() -> Client:
    """
    Cria e retorna uma conexão com o Supabase.

    Utiliza @st.cache_resource para manter uma única conexão
    durante toda a sessão, evitando reconexões desnecessárias.
    """
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# =============================================================================
# CAMADA DE DADOS - FUNÇÕES DE PERSISTÊNCIA (SUPABASE)
# =============================================================================
# Esta seção contém funções responsáveis pela leitura e escrita no Supabase.
# Os dados são sincronizados em tempo real entre todos os usuários.
# OTIMIZAÇÃO: Cache de 30 segundos para evitar consultas excessivas.

# TTL do cache de dados (em segundos) - curto para sincronização rápida
CACHE_DADOS_TTL = 15

@st.cache_data(ttl=CACHE_DADOS_TTL, show_spinner=False)
def carregar_dados():
    """
    Carrega os dados dos bairros a partir do Supabase.

    OTIMIZAÇÃO: Utiliza cache de 30 segundos para evitar consultas
    repetidas ao banco de dados. O cache é invalidado automaticamente
    após o TTL ou manualmente quando há uma atualização.

    Retorno:
        list: Lista de dicionários contendo os dados de cada bairro.
    """
    try:
        supabase = get_supabase_client()
        response = supabase.table("bairros").select("*").order("id").execute()
        return response.data
    except Exception as erro:
        st.error(f"❌ Erro ao conectar com o banco de dados: {erro}")
        return []


def invalidar_cache_dados():
    """
    Invalida o cache de dados para forçar uma nova consulta ao Supabase.
    Chamado após atualizações (votos, clima, etc).
    """
    carregar_dados.clear()


def salvar_bairro(bairro):
    """
    Atualiza os dados de um bairro específico no Supabase.

    Parâmetros:
        bairro (dict): Dicionário com dados atualizados do bairro.
    """
    try:
        supabase = get_supabase_client()
        supabase.table("bairros").update({
            "status": bairro.get("status", "Normal"),
            "risco": bairro.get("risco", "Baixo"),
            "votos": bairro.get("votos", 0),
            "chuva_real": bairro.get("chuva_real", 0),
            "temperatura": bairro.get("temperatura", 0),
            "probabilidade_chuva": bairro.get("probabilidade_chuva", 0),
            "precipitacao_proxima_hora": bairro.get("precipitacao_proxima_hora", 0),
            "updated_at": agora_brasilia().isoformat()
        }).eq("id", bairro["id"]).execute()
    except Exception as erro:
        st.error(f"❌ Erro ao salvar dados: {erro}")


def salvar_dados(dados):
    """
    Atualiza todos os bairros no Supabase.

    Parâmetros:
        dados (list): Lista de dicionários com dados atualizados dos bairros.
    """
    for bairro in dados:
        salvar_bairro(bairro)

    # Invalida o cache para buscar dados frescos na próxima leitura
    invalidar_cache_dados()


def obter_dados_otimizado():
    """
    Obtém dados dos bairros do Supabase com cache inteligente.

    OTIMIZAÇÃO: Usa cache de 30 segundos para performance.
    Os dados são atualizados automaticamente após o TTL.

    Retorno:
        list: Lista de dicionários com dados dos bairros.
    """
    return carregar_dados()


def forcar_recarregamento_dados():
    """
    Força o recarregamento dos dados do Supabase.
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
    # ATUALIZAÇÃO: Parâmetros expandidos para maior precisão no monitoramento de alagamentos
    # - precipitation: total de precipitação (chuva + garoa + neve)
    # - rain: chuva de sistemas meteorológicos (frentes frias, mais contínua)
    # - showers: pancadas de chuva convectiva (mais intensa e rápida)
    # - weather_code: código numérico do tipo de clima (permite identificar tempestades)
    # - relative_humidity_2m: umidade do ar (solo saturado = mais risco de alagamento)
    parametros = {
        "latitude": lat,
        "longitude": lon,
        "current": "precipitation,temperature_2m,relative_humidity_2m,rain,showers,weather_code",
        "hourly": "precipitation,precipitation_probability,rain,showers,weather_code",
        "daily": "precipitation_sum,precipitation_hours,precipitation_probability_max",
        "timezone": "America/Sao_Paulo",
        "forecast_days": 2  # 2 dias para melhor previsão
    }

    try:
        # Realiza a requisição HTTP GET para a API
        # timeout=10: Aguarda no máximo 10 segundos pela resposta
        resposta = requests.get(API_OPEN_METEO_URL, params=parametros, timeout=10)

        # Verifica se a requisição foi bem-sucedida (código HTTP 200)
        resposta.raise_for_status()

        # Converte a resposta JSON para dicionário Python
        dados_json = resposta.json()

        # Extrai os valores da estrutura de dados retornada
        # Estrutura expandida com mais dados para precisão
        current = dados_json.get("current", {})
        hourly = dados_json.get("hourly", {})
        daily = dados_json.get("daily", {})

        # Dados atuais expandidos
        precipitacao = current.get("precipitation", 0.0)  # Total (chuva + garoa + neve)
        temperatura = current.get("temperature_2m", 0.0)
        umidade = current.get("relative_humidity_2m", 0)  # Umidade relativa (%)
        rain = current.get("rain", 0.0)  # Chuva de frentes (contínua)
        showers = current.get("showers", 0.0)  # Pancadas (intensas)
        weather_code = current.get("weather_code", 0)  # Código do clima

        # Dados horários para previsão
        probabilidades = hourly.get("precipitation_probability", [])
        precipitacoes_hora = hourly.get("precipitation", [])
        weather_codes_hora = hourly.get("weather_code", [])

        # Dados diários para visão geral
        precip_total_dia = daily.get("precipitation_sum", [0.0])[0] if daily.get("precipitation_sum") else 0.0
        horas_chuva = daily.get("precipitation_hours", [0])[0] if daily.get("precipitation_hours") else 0
        prob_max_dia = daily.get("precipitation_probability_max", [0])[0] if daily.get("precipitation_probability_max") else 0

        # Pega a hora atual (Brasília) para indexar os dados horários
        hora_atual = agora_brasilia().hour
        probabilidade = probabilidades[hora_atual] if hora_atual < len(probabilidades) else 0
        precip_proxima_hora = precipitacoes_hora[hora_atual] if hora_atual < len(precipitacoes_hora) else 0.0
        weather_code_proxima_hora = weather_codes_hora[hora_atual] if hora_atual < len(weather_codes_hora) else 0

        return {
            "chuva": precipitacao,
            "temperatura": temperatura,
            "probabilidade_chuva": probabilidade,
            "precipitacao_proxima_hora": precip_proxima_hora,
            # Novos campos para maior precisão
            "umidade": umidade,
            "rain": rain,  # Chuva contínua
            "showers": showers,  # Pancadas
            "weather_code": weather_code,
            "weather_code_proxima_hora": weather_code_proxima_hora,
            "precip_total_dia": precip_total_dia,
            "horas_chuva": horas_chuva,
            "prob_max_dia": prob_max_dia
        }

    except requests.RequestException as erro:
        # Log do erro para debugging (aparece no terminal do Streamlit)
        print(f"[ERRO API] Falha ao consultar Open-Meteo: {erro}")
        return {
            "chuva": 0.0, "temperatura": 0.0, "probabilidade_chuva": 0, "precipitacao_proxima_hora": 0.0,
            "umidade": 0, "rain": 0.0, "showers": 0.0, "weather_code": 0, "weather_code_proxima_hora": 0,
            "precip_total_dia": 0.0, "horas_chuva": 0, "prob_max_dia": 0
        }
    except (KeyError, TypeError, IndexError) as erro:
        print(f"[ERRO API] Resposta inesperada da API: {erro}")
        return {
            "chuva": 0.0, "temperatura": 0.0, "probabilidade_chuva": 0, "precipitacao_proxima_hora": 0.0,
            "umidade": 0, "rain": 0.0, "showers": 0.0, "weather_code": 0, "weather_code_proxima_hora": 0,
            "precip_total_dia": 0.0, "horas_chuva": 0, "prob_max_dia": 0
        }


@st.cache_data(ttl=CACHE_TTL_SEGUNDOS, show_spinner=False)
def buscar_previsao_horaria(lat, lon):
    """
    Busca previsão horária de precipitação para as próximas 48 horas.

    ATUALIZAÇÃO: Inclui dados de rain, showers e weather_code para
    maior precisão na previsão de alagamentos.

    Parâmetros:
        lat (float): Latitude do local
        lon (float): Longitude do local

    Retorno:
        dict: Dicionário com listas de horas, precipitação, probabilidade,
              rain, showers e weather_code
    """
    parametros = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation,precipitation_probability,rain,showers,weather_code",
        "timezone": "America/Sao_Paulo",
        "forecast_days": 2  # 48 horas de previsão
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
        rain = hourly.get("rain", [])  # Chuva contínua
        showers = hourly.get("showers", [])  # Pancadas intensas
        weather_codes = hourly.get("weather_code", [])  # Código do clima

        return {
            "horarios": horarios,
            "precipitacao": precipitacoes,
            "probabilidade": probabilidades,
            "rain": rain,
            "showers": showers,
            "weather_code": weather_codes
        }

    except Exception as erro:
        print(f"[ERRO API] Falha ao buscar previsão horária: {erro}")
        return {
            "horarios": [],
            "precipitacao": [],
            "probabilidade": [],
            "rain": [],
            "showers": [],
            "weather_code": []
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
            "chuva": 0.0, "temperatura": 0.0, "probabilidade_chuva": 0,
            "precipitacao_proxima_hora": 0.0, "umidade": 0, "rain": 0.0,
            "showers": 0.0, "weather_code": 0, "weather_code_proxima_hora": 0,
            "precip_total_dia": 0.0, "horas_chuva": 0, "prob_max_dia": 0
        })

        # Atualiza campos básicos
        bairro["chuva_real"] = clima["chuva"]
        bairro["temperatura"] = clima["temperatura"]
        bairro["probabilidade_chuva"] = clima.get("probabilidade_chuva", 0)
        bairro["precipitacao_proxima_hora"] = clima.get("precipitacao_proxima_hora", 0.0)

        # Atualiza novos campos para maior precisão
        bairro["umidade"] = clima.get("umidade", 0)
        bairro["rain"] = clima.get("rain", 0.0)
        bairro["showers"] = clima.get("showers", 0.0)
        bairro["weather_code"] = clima.get("weather_code", 0)
        bairro["precip_total_dia"] = clima.get("precip_total_dia", 0.0)
        bairro["horas_chuva"] = clima.get("horas_chuva", 0)

        # REGRA DE AUTOMAÇÃO MELHORADA: Usa cálculo de risco multi-fator
        # Considera precipitação, pancadas, weather_code, umidade e probabilidade
        nivel_risco, pontuacao_risco = calcular_risco_alagamento(clima)

        # Não sobrescreve status se já foi confirmado alagamento pela comunidade
        if bairro["status"] != "ALAGADO CONFIRMADO":
            if nivel_risco == "Crítico":
                bairro["status"] = "Risco Meteorológico"
                bairro["risco"] = "Crítico"
            elif nivel_risco == "Alto":
                bairro["status"] = "Risco Meteorológico"
                bairro["risco"] = "Alto"
            elif nivel_risco == "Médio" and bairro["status"] == "Normal":
                bairro["status"] = "Atenção"
                bairro["risco"] = "Médio"

        # Armazena pontuação de risco para exibição
        bairro["pontuacao_risco"] = pontuacao_risco

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

    Executa a cada INTERVALO_ATUALIZACAO minutos (padrão: 1 minuto).
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
    # Limpa o cache da API para buscar dados frescos
    buscar_clima_api.clear()

    # Invalida cache de dados do Supabase
    invalidar_cache_dados()

    dados = obter_dados_otimizado()

    if dados:
        dados = atualizar_clima_todos_bairros(dados)
        salvar_dados(dados)

        # Armazena timestamp da última atualização automática (horário de Brasília)
        st.session_state.ultima_atualizacao_auto = agora_brasilia()


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


def registrar_evento_historico(bairro, tipo_evento, detalhes=""):
    """
    Registra um evento no histórico do bairro no Supabase.

    Parâmetros:
        bairro (dict): Dicionário do bairro a ser atualizado
        tipo_evento (str): Tipo do evento (ex: "ALAGAMENTO_CONFIRMADO", "NORMALIZADO")
        detalhes (str): Informações adicionais sobre o evento
    """
    try:
        supabase = get_supabase_client()
        supabase.table("historico").insert({
            "bairro_id": bairro["id"],
            "bairro_nome": bairro["nome"],
            "data": agora_brasilia().strftime("%Y-%m-%d"),
            "hora": agora_brasilia().strftime("%H:%M:%S"),
            "tipo": tipo_evento,
            "detalhes": detalhes
        }).execute()
    except Exception as erro:
        print(f"[ERRO] Falha ao registrar histórico: {erro}")


def carregar_historico():
    """
    Carrega o histórico de eventos do Supabase.

    Retorno:
        list: Lista de eventos ordenados por data/hora (mais recentes primeiro).
    """
    try:
        supabase = get_supabase_client()
        response = supabase.table("historico").select("*").order("created_at", desc=True).limit(100).execute()
        return response.data
    except Exception as erro:
        st.error(f"❌ Erro ao carregar histórico: {erro}")
        return []


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
    # SIDEBAR - INFORMAÇÕES E ADMIN PROTEGIDO
    # =========================================================================
    with st.sidebar:
        # Informações públicas do sistema
        st.markdown("### ℹ️ Informações")
        st.caption(f"🔄 Atualização: a cada {INTERVALO_ATUALIZACAO} min")
        if "ultima_atualizacao_auto" in st.session_state and st.session_state.ultima_atualizacao_auto:
            ultima = st.session_state.ultima_atualizacao_auto.strftime('%H:%M:%S')
            st.caption(f"⏱️ Última: {ultima}")
        st.caption(f"📍 {len(dados)} bairros monitorados")

        st.markdown("---")

        # Área de login admin (protegida por senha)
        with st.expander("🔐 Área Administrativa", expanded=False):
            # Verifica se já está autenticado
            if "admin_autenticado" not in st.session_state:
                st.session_state.admin_autenticado = False

            if not st.session_state.admin_autenticado:
                # Campo de senha
                senha_digitada = st.text_input(
                    "Senha de administrador:",
                    type="password",
                    key="senha_admin"
                )

                if st.button("🔓 Entrar", use_container_width=True):
                    # Verifica a senha (armazenada nos secrets)
                    senha_correta = st.secrets.get("ADMIN_PASSWORD", "admin123")
                    if senha_digitada == senha_correta:
                        st.session_state.admin_autenticado = True
                        st.toast("✅ Acesso liberado!", icon="🔓")
                        st.rerun()
                    else:
                        st.error("❌ Senha incorreta!")
            else:
                # Usuário autenticado - mostra controles admin
                st.success("✅ Logado como Admin")

                if st.button("🚪 Sair", use_container_width=True):
                    st.session_state.admin_autenticado = False
                    st.rerun()

                st.markdown("---")

                # Botão para atualização manual dos dados meteorológicos
                if st.button("🔄 Atualizar Clima (API)", use_container_width=True):
                    with st.spinner("Consultando API Open-Meteo..."):
                        # Limpa todos os caches para forçar dados frescos
                        buscar_clima_api.clear()
                        buscar_previsao_horaria.clear()
                        invalidar_cache_dados()
                        dados = atualizar_clima_todos_bairros(dados)
                        salvar_dados(dados)
                        st.session_state.ultima_atualizacao_auto = agora_brasilia()
                    st.toast("✅ Dados meteorológicos atualizados!", icon="🌤️")
                    st.rerun()

                # Botão para resetar todos os votos
                if st.button("🗑️ Resetar Votos", use_container_width=True):
                    for bairro in dados:
                        # Registra normalização se estava alagado
                        if bairro["status"] == "ALAGADO CONFIRMADO":
                            registrar_evento_historico(
                                bairro,
                                "NORMALIZADO",
                                "Status resetado pelo administrador"
                            )
                        bairro["votos"] = 0
                        bairro["status"] = "Normal"
                        bairro["risco"] = "Baixo"
                    salvar_dados(dados)
                    st.toast("✅ Votos resetados!", icon="🔄")
                    st.rerun()

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
    # MÉTRICAS EXPANDIDAS (2 LINHAS)
    # =========================================================================
    # Linha 1: Métricas principais
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)

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

    with col_m4:
        umidade = bairro_atual.get('umidade', 0)
        st.metric(
            label="💧 Umidade",
            value=f"{umidade}%"
        )

    # Linha 2: Métricas detalhadas de precipitação
    col_m5, col_m6, col_m7, col_m8 = st.columns(4)

    with col_m5:
        # Mostra condição climática atual com emoji
        weather_code = bairro_atual.get('weather_code', 0)
        info_clima = obter_info_weather_code(weather_code)
        st.metric(
            label="🌤️ Condição",
            value=f"{info_clima['emoji']} {info_clima['descricao'][:12]}"
        )

    with col_m6:
        # Pancadas de chuva (mais intensas)
        showers = bairro_atual.get('showers', 0.0)
        st.metric(
            label="⛈️ Pancadas",
            value=f"{showers:.1f} mm"
        )

    with col_m7:
        # Total previsto para o dia
        precip_total = bairro_atual.get('precip_total_dia', 0.0)
        st.metric(
            label="📊 Total Dia",
            value=f"{precip_total:.1f} mm"
        )

    with col_m8:
        # Pontuação de risco calculada
        pontuacao = bairro_atual.get('pontuacao_risco', 0)
        cor_pontuacao = "🔴" if pontuacao >= 60 else "🟠" if pontuacao >= 40 else "🟡" if pontuacao >= 20 else "🟢"
        st.metric(
            label=f"{cor_pontuacao} Índice Risco",
            value=f"{pontuacao}/100"
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
            # Registra o evento no histórico
            registrar_evento_historico(
                bairro_atual,
                "ALAGAMENTO_CONFIRMADO",
                f"Confirmado por {LIMITE_VOTOS_ALAGAMENTO} votos da comunidade"
            )
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

    tab_previsao, tab_mapa, tab_todos, tab_historico = st.tabs(["📈 Previsão 24h", "🗺️ Mapa", "📋 Todos os Bairros", "📜 Histórico"])

    # ----- ABA 1: PREVISÃO HORÁRIA -----
    with tab_previsao:
        previsao = buscar_previsao_horaria(bairro_atual["lat"], bairro_atual["lon"])

        if previsao["horarios"]:
            # Limita a 24 horas para visualização mais limpa
            limite_horas = 24
            df_previsao = pd.DataFrame({
                "Horário": previsao["horarios"][:limite_horas],
                "Precipitação (mm)": previsao["precipitacao"][:limite_horas],
                "Probabilidade (%)": previsao["probabilidade"][:limite_horas],
                "Chuva (mm)": previsao["rain"][:limite_horas] if previsao["rain"] else [0]*limite_horas,
                "Pancadas (mm)": previsao["showers"][:limite_horas] if previsao["showers"] else [0]*limite_horas,
                "Código Clima": previsao["weather_code"][:limite_horas] if previsao["weather_code"] else [0]*limite_horas
            })

            # Hora atual (Brasília) para destacar no gráfico
            hora_atual = agora_brasilia().hour
            hora_atual_str = f"{hora_atual:02d}:00"

            # Cria o gráfico interativo com Plotly
            fig = go.Figure()

            # Barras empilhadas para Chuva e Pancadas (mais informativo)
            fig.add_trace(go.Bar(
                x=df_previsao["Horário"],
                y=df_previsao["Chuva (mm)"],
                name='Chuva Contínua',
                marker_color='#1E90FF',
                hovertemplate='<b>%{x}</b><br>Chuva: %{y:.1f} mm<extra></extra>'
            ))

            fig.add_trace(go.Bar(
                x=df_previsao["Horário"],
                y=df_previsao["Pancadas (mm)"],
                name='Pancadas',
                marker_color='#FF4500',
                hovertemplate='<b>%{x}</b><br>Pancadas: %{y:.1f} mm<extra></extra>'
            ))

            # Linha para precipitação total (soma)
            fig.add_trace(go.Scatter(
                x=df_previsao["Horário"],
                y=df_previsao["Precipitação (mm)"],
                mode='lines',
                name='Total',
                line=dict(color='#4B0082', width=2),
                hovertemplate='<b>%{x}</b><br>Total: %{y:.1f} mm<extra></extra>'
            ))

            # Linha para probabilidade de chuva (eixo Y secundário)
            fig.add_trace(go.Scatter(
                x=df_previsao["Horário"],
                y=df_previsao["Probabilidade (%)"],
                mode='lines+markers',
                name='Probabilidade',
                line=dict(color='#32CD32', width=2, dash='dot'),
                marker=dict(size=5),
                yaxis='y2',
                hovertemplate='<b>%{x}</b><br>Probabilidade: %{y}%<extra></extra>'
            ))

            # Linha vertical indicando a hora atual
            # Usando add_shape ao invés de add_vline para evitar erro com eixo categórico
            if hora_atual_str in df_previsao["Horário"].values:
                idx_hora_atual = df_previsao[df_previsao["Horário"] == hora_atual_str].index[0]
                fig.add_shape(
                    type="line",
                    x0=hora_atual_str,
                    x1=hora_atual_str,
                    y0=0,
                    y1=1,
                    yref="paper",
                    line=dict(color="#00FF00", width=2, dash="dash")
                )
                # Anotação separada para "Agora"
                fig.add_annotation(
                    x=hora_atual_str,
                    y=1.05,
                    yref="paper",
                    text="Agora",
                    showarrow=False,
                    font=dict(color="#00FF00", size=12)
                )

            # Faixa de risco (precipitação acima de 10mm)
            fig.add_hrect(
                y0=LIMITE_CHUVA_RISCO,
                y1=max(df_previsao["Precipitação (mm)"].max() + 5, LIMITE_CHUVA_RISCO + 5),
                fillcolor="rgba(220, 53, 69, 0.15)",
                line_width=0,
                annotation_text="Zona de Risco",
                annotation_position="top right",
                annotation_font_color="#dc3545"
            )

            # Layout do gráfico
            fig.update_layout(
                title=dict(
                    text=f"🌧️ Previsão de Chuva - {bairro_atual['nome']}",
                    font=dict(size=18)
                ),
                barmode='stack',  # Barras empilhadas para chuva + pancadas
                xaxis=dict(
                    title="Horário",
                    tickangle=45,
                    showgrid=True,
                    gridcolor='rgba(128,128,128,0.2)'
                ),
                yaxis=dict(
                    title=dict(text="Precipitação (mm)", font=dict(color='#1E90FF')),
                    tickfont=dict(color='#1E90FF'),
                    showgrid=True,
                    gridcolor='rgba(128,128,128,0.2)',
                    rangemode='tozero'
                ),
                yaxis2=dict(
                    title=dict(text="Probabilidade (%)", font=dict(color='#32CD32')),
                    tickfont=dict(color='#32CD32'),
                    overlaying='y',
                    side='right',
                    range=[0, 100],
                    showgrid=False
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5
                ),
                hovermode='x unified',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                height=400,
                margin=dict(l=50, r=50, t=80, b=60)
            )

            # Renderiza o gráfico no Streamlit
            st.plotly_chart(fig, use_container_width=True)

            # Resumo rápido da previsão
            max_precip = df_previsao["Precipitação (mm)"].max()
            max_prob = df_previsao["Probabilidade (%)"].max()
            hora_max_precip = df_previsao.loc[df_previsao["Precipitação (mm)"].idxmax(), "Horário"]

            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                cor_max = "#dc3545" if max_precip >= LIMITE_CHUVA_RISCO else "#28a745"
                st.markdown(f"""
                    <div style="text-align: center; padding: 10px; background: rgba(0,0,0,0.1); border-radius: 8px;">
                        <p style="margin: 0; color: gray; font-size: 12px;">Pico de Chuva</p>
                        <h3 style="margin: 5px 0; color: {cor_max};">{max_precip:.1f} mm</h3>
                        <small>às {hora_max_precip}</small>
                    </div>
                """, unsafe_allow_html=True)
            with col_info2:
                cor_prob = "#dc3545" if max_prob >= 80 else ("#ffc107" if max_prob >= 50 else "#28a745")
                st.markdown(f"""
                    <div style="text-align: center; padding: 10px; background: rgba(0,0,0,0.1); border-radius: 8px;">
                        <p style="margin: 0; color: gray; font-size: 12px;">Máx. Probabilidade</p>
                        <h3 style="margin: 5px 0; color: {cor_prob};">{max_prob}%</h3>
                        <small>de chance</small>
                    </div>
                """, unsafe_allow_html=True)
            with col_info3:
                total_precip = df_previsao["Precipitação (mm)"].sum()
                st.markdown(f"""
                    <div style="text-align: center; padding: 10px; background: rgba(0,0,0,0.1); border-radius: 8px;">
                        <p style="margin: 0; color: gray; font-size: 12px;">Total Acumulado</p>
                        <h3 style="margin: 5px 0; color: #1E90FF;">{total_precip:.1f} mm</h3>
                        <small>nas próximas 24h</small>
                    </div>
                """, unsafe_allow_html=True)

            with st.expander("📊 Ver dados detalhados"):
                # Adiciona descrição do clima para cada hora
                df_previsao["Condição"] = df_previsao["Código Clima"].apply(
                    lambda x: f"{obter_info_weather_code(x)['emoji']} {obter_info_weather_code(x)['descricao']}"
                )
                st.dataframe(
                    df_previsao[["Horário", "Precipitação (mm)", "Chuva (mm)", "Pancadas (mm)", "Probabilidade (%)", "Condição"]],
                    hide_index=True
                )
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
            weather_code = bairro.get("weather_code", 0)
            info_clima = obter_info_weather_code(weather_code)
            pontuacao = bairro.get("pontuacao_risco", 0)

            dados_tabela.append({
                "Bairro": bairro["nome"],
                "Status": f"{emoji} {bairro['status']}",
                "Clima": f"{info_clima['emoji']}",
                "Temp": f"{bairro.get('temperatura', 0):.1f}°C",
                "Chuva": f"{bairro.get('chuva_real', 0):.1f}mm",
                "Pancadas": f"{bairro.get('showers', 0):.1f}mm",
                "Umidade": f"{bairro.get('umidade', 0)}%",
                "Prob": f"{bairro.get('probabilidade_chuva', 0)}%",
                "Risco": f"{pontuacao}/100",
                "Votos": bairro.get("votos", 0)
            })

        df_resumo = pd.DataFrame(dados_tabela)
        st.dataframe(df_resumo, hide_index=True, use_container_width=True)

    # ----- ABA 4: HISTÓRICO DE ALAGAMENTOS -----
    with tab_historico:
        st.markdown("### 📜 Histórico de Alagamentos")
        st.caption("Registro de todos os alagamentos confirmados pela comunidade")

        # Carrega histórico do Supabase
        historico_eventos = carregar_historico()

        # Formata os eventos para exibição
        todos_eventos = []
        for evento in historico_eventos:
            todos_eventos.append({
                "bairro": evento.get("bairro_nome", ""),
                "data": evento.get("data", ""),
                "hora": evento.get("hora", ""),
                "tipo": evento.get("tipo", ""),
                "detalhes": evento.get("detalhes", "")
            })

        if todos_eventos:

            # Estatísticas rápidas
            total_alagamentos = sum(1 for e in todos_eventos if e["tipo"] == "ALAGAMENTO_CONFIRMADO")
            total_normalizacoes = sum(1 for e in todos_eventos if e["tipo"] == "NORMALIZADO")

            col_stat1, col_stat2 = st.columns(2)
            with col_stat1:
                st.metric("🚨 Alagamentos Registrados", total_alagamentos)
            with col_stat2:
                st.metric("✅ Normalizações", total_normalizacoes)

            st.markdown("---")

            # Timeline de eventos
            for evento in todos_eventos:
                # Define ícone e cor baseado no tipo de evento
                if evento["tipo"] == "ALAGAMENTO_CONFIRMADO":
                    icone = "🚨"
                    cor_borda = "#dc3545"
                    titulo = "Alagamento Confirmado"
                elif evento["tipo"] == "NORMALIZADO":
                    icone = "✅"
                    cor_borda = "#28a745"
                    titulo = "Situação Normalizada"
                else:
                    icone = "📝"
                    cor_borda = "#6c757d"
                    titulo = evento["tipo"]

                # Card do evento
                st.markdown(f"""
                    <div style="
                        border-left: 4px solid {cor_borda};
                        padding: 10px 15px;
                        margin-bottom: 10px;
                        background: rgba(0,0,0,0.05);
                        border-radius: 0 8px 8px 0;
                    ">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: bold;">{icone} {titulo}</span>
                            <small style="color: gray;">{evento["data"]} às {evento["hora"]}</small>
                        </div>
                        <div style="margin-top: 5px;">
                            <strong>📍 {evento["bairro"]}</strong>
                        </div>
                        <small style="color: gray;">{evento["detalhes"]}</small>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📭 Nenhum evento registrado ainda. O histórico será preenchido quando alagamentos forem confirmados pela comunidade.")

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
