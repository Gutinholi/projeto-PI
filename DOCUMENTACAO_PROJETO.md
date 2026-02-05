# Sistema de Monitoramento de Alagamentos - Guarujá/SP

## Projeto Integrador - Tecnologia da Informação

---

## 1. Visão Geral do Projeto

### 1.1 Objetivo
Desenvolver um **MVP (Minimum Viable Product)** de um sistema colaborativo para monitoramento de alagamentos em tempo real na cidade de Guarujá/SP, utilizando a abordagem de **Crowdsourcing** combinada com dados meteorológicos reais.

### 1.2 Problema Abordado
Guarujá, cidade litorânea do estado de São Paulo, enfrenta frequentes problemas de alagamentos durante períodos de chuva intensa. A população muitas vezes não tem acesso a informações em tempo real sobre quais áreas estão alagadas, dificultando a locomoção e colocando vidas em risco.

### 1.3 Solução Proposta
Um sistema web que combina duas fontes de dados:
1. **Dados Meteorológicos em Tempo Real**: Obtidos através da API Open-Meteo
2. **Reportes da Comunidade (Crowdsourcing)**: Cidadãos podem reportar alagamentos em seus bairros

---

## 2. Tecnologias Utilizadas

### 2.1 Linguagem de Programação
| Tecnologia | Versão | Justificativa |
|------------|--------|---------------|
| Python | 3.12+ | Linguagem versátil, ampla comunidade, ideal para prototipagem rápida |

### 2.2 Framework Web
| Tecnologia | Versão | Justificativa |
|------------|--------|---------------|
| Streamlit | 1.54.0 | Framework Python para criação de aplicações web interativas sem necessidade de conhecimento em HTML/CSS/JavaScript |

### 2.3 Bibliotecas Auxiliares
| Biblioteca | Função |
|------------|--------|
| `requests` | Consumo de APIs REST (Open-Meteo) |
| `pandas` | Manipulação de dados tabulares e integração com componentes Streamlit |
| `json` | Serialização/deserialização de dados para persistência local |
| `datetime` | Manipulação de datas e timestamps |
| `concurrent.futures` | Execução paralela de requisições à API (otimização de performance) |

### 2.4 API Externa
| Serviço | URL | Função |
|---------|-----|--------|
| Open-Meteo | https://api.open-meteo.com | Fornece dados meteorológicos gratuitos em tempo real (precipitação, temperatura, etc.) |

### 2.5 Persistência de Dados
| Formato | Arquivo | Justificativa |
|---------|---------|---------------|
| JSON | `dados.json` | Formato leve, legível, fácil manipulação em Python, não requer servidor de banco de dados |

---

## 3. Arquitetura do Sistema

### 3.1 Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        USUÁRIO (NAVEGADOR)                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CAMADA DE APRESENTAÇÃO                        │
│                       (Streamlit - app.py)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Sidebar   │  │   Painel    │  │     Mapa Interativo     │  │
│  │   (Menu)    │  │  do Bairro  │  │    (Visualização)       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CAMADA DE SERVIÇO                            │
│  ┌─────────────────────────┐  ┌───────────────────────────────┐ │
│  │  Regras de Automação    │  │   Integração API Open-Meteo   │ │
│  │  (Crowdsourcing + API)  │  │   (buscar_clima_api)          │ │
│  └─────────────────────────┘  └───────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CAMADA DE DADOS                             │
│  ┌─────────────────────────┐  ┌───────────────────────────────┐ │
│  │    carregar_dados()     │  │       salvar_dados()          │ │
│  └─────────────────────────┘  └───────────────────────────────┘ │
│                         │                                        │
│                         ▼                                        │
│                 ┌───────────────┐                                │
│                 │  dados.json   │                                │
│                 └───────────────┘                                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API EXTERNA                                 │
│                     (Open-Meteo)                                 │
│         https://api.open-meteo.com/v1/forecast                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Padrão Arquitetural
O sistema segue o padrão de **Arquitetura em Camadas**, separando responsabilidades:

- **Camada de Apresentação**: Interface do usuário (Streamlit)
- **Camada de Serviço**: Lógica de negócio e integrações
- **Camada de Dados**: Persistência em arquivo JSON

---

## 4. Estrutura de Arquivos

```
/home/yuri/
├── app.py                  # Aplicação principal Streamlit
├── resetar_bairros.py      # Script de setup/reset dos dados
├── dados.json              # Arquivo de persistência (gerado)
├── venv/                   # Ambiente virtual Python
│   ├── bin/
│   ├── lib/
│   └── ...
└── DOCUMENTACAO_PROJETO.md # Esta documentação
```

---

## 5. Detalhamento dos Arquivos

### 5.1 Arquivo: `resetar_bairros.py`

#### Propósito
Script de inicialização que cria o arquivo `dados.json` com os dados dos 15 principais bairros do Guarujá.

#### Estrutura de Dados de Cada Bairro

```python
{
    "id": 1,                         # Identificador único
    "nome": "Pitangueiras",          # Nome do bairro
    "lat": -23.9930,                 # Latitude (coordenada geográfica)
    "lon": -46.2564,                 # Longitude (coordenada geográfica)
    "status": "Normal",              # Estado atual do bairro
    "risco": "Baixo",                # Nível de risco
    "votos": 0,                      # Contador de reportes (crowdsourcing)
    "chuva_real": 0.0,               # Última leitura de precipitação (mm)
    "temperatura": 0.0,              # Temperatura atual em °C
    "probabilidade_chuva": 0,        # Probabilidade de chuva na hora atual (%)
    "precipitacao_proxima_hora": 0.0 # Precipitação esperada na próxima hora (mm)
}
```

#### Bairros Cadastrados

| ID | Bairro | Latitude | Longitude |
|----|--------|----------|-----------|
| 1 | Pitangueiras | -23.9930 | -46.2564 |
| 2 | Enseada | -23.9785 | -46.2289 |
| 3 | Vicente de Carvalho | -23.9372 | -46.3178 |
| 4 | Santo Antônio | -23.9890 | -46.2680 |
| 5 | Astúrias | -23.9988 | -46.2478 |
| 6 | Tombo | -24.0085 | -46.2612 |
| 7 | Morrinhos | -23.9520 | -46.2450 |
| 8 | Santa Cruz dos Navegantes | -23.9650 | -46.2520 |
| 9 | Perequê | -23.9580 | -46.2150 |
| 10 | Jardim Boa Esperança | -23.9420 | -46.3050 |
| 11 | Jardim Progresso | -23.9350 | -46.3100 |
| 12 | Pae Cará | -23.9280 | -46.2980 |
| 13 | Jardim Las Palmas | -23.9680 | -46.2380 |
| 14 | Jardim Virgínia | -23.9480 | -46.2650 |
| 15 | Praia do Guaiúba | -24.0150 | -46.2750 |

#### Como Executar
```bash
python3 resetar_bairros.py
```

---

### 5.2 Arquivo: `app.py`

#### Propósito
Aplicação principal que implementa toda a interface web e lógica do sistema.

#### Estrutura do Código

##### A) Importações e Configurações
```python
import streamlit as st      # Framework web
import requests             # Consumo de API
import json                 # Manipulação de JSON
import pandas as pd         # Manipulação de dados
from datetime import datetime
```

##### B) Constantes Globais
```python
ARQUIVO_DADOS = "dados.json"      # Arquivo de persistência
LIMITE_VOTOS_ALAGAMENTO = 5       # Votos para confirmar alagamento
LIMITE_CHUVA_RISCO = 10.0         # mm de chuva para alerta automático
INTERVALO_ATUALIZACAO = 10        # Minutos entre atualizações automáticas
MAX_WORKERS_API = 5               # Requisições paralelas à API
CACHE_TTL_SEGUNDOS = 120          # Tempo de vida do cache (2 minutos)
```

##### C) Funções da Camada de Dados

| Função | Descrição |
|--------|-----------|
| `carregar_dados()` | Lê o arquivo JSON e retorna lista de bairros |
| `salvar_dados(dados)` | Persiste alterações no arquivo JSON e atualiza cache |
| `obter_dados_otimizado()` | Retorna dados do session_state (evita releitura do JSON) |
| `forcar_recarregamento_dados()` | Força releitura do arquivo JSON |

##### D) Funções da Camada de Serviço

| Função | Descrição |
|--------|-----------|
| `buscar_clima_api(lat, lon)` | Consulta API Open-Meteo com cache de 2 minutos |
| `_buscar_clima_bairro(bairro)` | Função auxiliar para paralelização |
| `atualizar_clima_todos_bairros(dados)` | Atualiza todos os bairros em paralelo (ThreadPoolExecutor) |
| `atualizar_clima_automatico()` | Fragmento que executa a cada 10 minutos |

##### E) Funções Auxiliares de UI

| Função | Descrição |
|--------|-----------|
| `obter_cor_status(status)` | Retorna cor CSS baseada no status |
| `obter_emoji_status(status)` | Retorna emoji representativo do status |

---

## 6. Regras de Automação

### 6.1 Regra 1: Alerta por Dados Meteorológicos (API)

```
SE chuva_real > 10mm ENTÃO
    status = "Risco Meteorológico"
    risco = "Alto"
FIM SE
```

**Justificativa**: Precipitações acima de 10mm/hora são consideradas chuvas fortes e têm alto potencial de causar alagamentos em áreas vulneráveis.

**Código Correspondente**:
```python
if chuva > LIMITE_CHUVA_RISCO:
    bairro["status"] = "Risco Meteorológico"
    bairro["risco"] = "Alto"
```

### 6.2 Regra 2: Alerta por Alta Probabilidade de Chuva

```
SE probabilidade_chuva >= 80% E status = "Normal" ENTÃO
    status = "Atenção"
    risco = "Médio"
FIM SE
```

**Justificativa**: Probabilidades de chuva acima de 80% indicam alta chance de precipitação iminente, permitindo alertar a população preventivamente.

**Código Correspondente**:
```python
elif clima.get("probabilidade_chuva", 0) >= 80 and bairro["status"] == "Normal":
    bairro["status"] = "Atenção"
    bairro["risco"] = "Médio"
```

### 6.3 Regra 3: Confirmação por Crowdsourcing

```
SE votos >= 5 ENTÃO
    status = "ALAGADO CONFIRMADO"
    risco = "Crítico"
SENÃO SE votos >= 1 ENTÃO
    status = "Atenção"
    risco = "Médio"
FIM SE
```

**Justificativa**: O limiar de 5 votos evita falsos positivos causados por reportes isolados ou mal-intencionados. Múltiplas confirmações independentes aumentam a confiabilidade da informação.

**Código Correspondente**:
```python
if bairro_atual["votos"] >= LIMITE_VOTOS_ALAGAMENTO:
    bairro_atual["status"] = "ALAGADO CONFIRMADO"
    bairro_atual["risco"] = "Crítico"
else:
    if bairro_atual["status"] == "Normal":
        bairro_atual["status"] = "Atenção"
        bairro_atual["risco"] = "Médio"
```

---

## 7. Integração com API Open-Meteo

### 7.1 Sobre a API
A **Open-Meteo** é uma API gratuita e open-source que fornece dados meteorológicos em tempo real para qualquer localização do mundo.

### 7.2 Endpoint Utilizado
```
GET https://api.open-meteo.com/v1/forecast
```

### 7.3 Parâmetros da Requisição

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| `latitude` | -23.99 | Coordenada do bairro |
| `longitude` | -46.25 | Coordenada do bairro |
| `current` | precipitation,temperature_2m | Precipitação total e temperatura atual |
| `hourly` | precipitation,precipitation_probability | Dados horários para previsão |
| `timezone` | America/Sao_Paulo | Fuso horário local |
| `forecast_days` | 1 | Apenas dados do dia atual |

> **Nota**: Utilizamos `precipitation` em vez de `rain` pois inclui todos os tipos de precipitação (chuva, garoa, chuvisco), fornecendo dados mais precisos.

### 7.4 Exemplo de Resposta da API

```json
{
  "latitude": -23.99,
  "longitude": -46.25,
  "current": {
    "time": "2026-02-05T14:00",
    "precipitation": 1.2,
    "temperature_2m": 26.5
  },
  "hourly": {
    "time": ["2026-02-05T00:00", "2026-02-05T01:00", ...],
    "precipitation": [0.0, 0.1, 0.5, 1.2, ...],
    "precipitation_probability": [10, 25, 60, 90, ...]
  }
}
```

### 7.5 Código de Consumo da API

```python
@st.cache_data(ttl=CACHE_TTL_SEGUNDOS, show_spinner=False)
def buscar_clima_api(lat, lon):
    parametros = {
        "latitude": lat,
        "longitude": lon,
        "current": "precipitation,temperature_2m",
        "hourly": "precipitation,precipitation_probability",
        "timezone": "America/Sao_Paulo",
        "forecast_days": 1
    }

    resposta = requests.get(API_OPEN_METEO_URL, params=parametros, timeout=10)
    resposta.raise_for_status()

    dados_json = resposta.json()
    current = dados_json.get("current", {})
    hourly = dados_json.get("hourly", {})

    # Extrai dados atuais
    precipitacao = current.get("precipitation", 0.0)
    temperatura = current.get("temperature_2m", 0.0)

    # Extrai probabilidade da hora atual
    hora_atual = datetime.now().hour
    probabilidades = hourly.get("precipitation_probability", [])
    probabilidade = probabilidades[hora_atual] if hora_atual < len(probabilidades) else 0

    return {
        "chuva": precipitacao,
        "temperatura": temperatura,
        "probabilidade_chuva": probabilidade,
        "precipitacao_proxima_hora": precipitacao
    }
```

---

## 8. Interface do Usuário

### 8.1 Layout Geral

```
┌──────────────────┬─────────────────────────────────────────────────┐
│                  │                                                 │
│     SIDEBAR      │              ÁREA PRINCIPAL                     │
│                  │                                                 │
│  ┌────────────┐  │  ┌─────────────────┐  ┌─────────────────────┐  │
│  │ Seletor de │  │  │                 │  │                     │  │
│  │   Bairro   │  │  │  PAINEL DO      │  │   MAPA DE GUARUJÁ   │  │
│  └────────────┘  │  │  BAIRRO         │  │                     │  │
│                  │  │                 │  │   (Visualização     │  │
│  ┌────────────┐  │  │  - Status       │  │    geográfica)      │  │
│  │ Atualizar  │  │  │  - Métricas     │  │                     │  │
│  │   Clima    │  │  │  - Botão        │  │                     │  │
│  └────────────┘  │  │    Reportar     │  │                     │  │
│                  │  │                 │  │                     │  │
│  ┌────────────┐  │  └─────────────────┘  └─────────────────────┘  │
│  │  Resetar   │  │                                                 │
│  │   Votos    │  │  ┌───────────────────────────────────────────┐  │
│  └────────────┘  │  │           TABELA RESUMO                    │  │
│                  │  │         (Todos os bairros)                 │  │
│                  │  └───────────────────────────────────────────┘  │
└──────────────────┴─────────────────────────────────────────────────┘
```

### 8.2 Métricas Exibidas no Painel do Bairro

| Métrica | Ícone | Descrição |
|---------|-------|-----------|
| Temperatura | 🌡️ | Temperatura atual em °C |
| Chuva Agora | 🌧️ | Precipitação atual em mm |
| Chance Chuva | 🎲 | Probabilidade de chuva (%) |
| Reportes | 📢 | Número de votos da comunidade |
| Risco | ⚡ | Nível de risco atual |

### 8.3 Componentes Streamlit Utilizados

| Componente | Função no Sistema |
|------------|-------------------|
| `st.title()` | Título principal da aplicação |
| `st.sidebar` | Menu lateral com controles |
| `st.selectbox()` | Seleção de bairro |
| `st.button()` | Botões de ação (Reportar, Atualizar) |
| `st.metric()` | Exibição de métricas (5 métricas no painel) |
| `st.map()` | Mapa interativo com marcadores |
| `st.dataframe()` | Tabela de dados com coluna de probabilidade |
| `st.toast()` | Notificações temporárias |
| `st.progress()` | Barra de progresso |
| `st.columns()` | Layout em colunas |
| `st.markdown()` | Textos formatados e HTML |
| `st.fragment()` | Atualização automática a cada 10 minutos |
| `st.cache_data()` | Cache de requisições à API |

### 8.4 Sistema de Cores (UX)

| Status | Cor | Significado |
|--------|-----|-------------|
| Normal | 🟢 Verde | Situação segura |
| Atenção | 🟡 Amarelo/Laranja | Requer monitoramento |
| Risco Meteorológico | 🟠 Laranja | Alerta da API |
| ALAGADO CONFIRMADO | 🔴 Vermelho | Situação crítica |

---

## 9. Otimizações de Performance

### 9.1 Visão Geral
O sistema implementa diversas otimizações para garantir uma experiência fluida mesmo com múltiplas requisições à API.

### 9.2 Chamadas Paralelas à API (ThreadPoolExecutor)

**Problema**: Com 15 bairros e requisições sequenciais, a atualização poderia levar até 15 segundos.

**Solução**: Utilização de `ThreadPoolExecutor` para fazer requisições em paralelo.

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=MAX_WORKERS_API) as executor:
    futures = {executor.submit(_buscar_clima_bairro, bairro): bairro for bairro in dados}
    for future in as_completed(futures):
        bairro_id, clima = future.result()
        resultados_clima[bairro_id] = clima
```

**Resultado**: Tempo reduzido de ~15 segundos para ~1-2 segundos.

### 9.3 Cache de Requisições (@st.cache_data)

**Problema**: Requisições repetidas à API desperdiçam recursos e aumentam latência.

**Solução**: Decorator `@st.cache_data` com TTL de 2 minutos.

```python
@st.cache_data(ttl=CACHE_TTL_SEGUNDOS, show_spinner=False)
def buscar_clima_api(lat, lon):
    # Requisição cacheada por 2 minutos
    ...
```

**Resultado**: Requisições idênticas dentro de 2 minutos retornam instantaneamente.

### 9.4 Session State para Dados

**Problema**: Releitura constante do arquivo JSON a cada interação.

**Solução**: Manter dados em memória no `st.session_state`.

```python
def obter_dados_otimizado():
    if "dados_bairros" not in st.session_state:
        st.session_state.dados_bairros = carregar_dados()
    return st.session_state.dados_bairros
```

**Resultado**: Arquivo JSON lido apenas uma vez por sessão.

### 9.5 Atualização Automática com Fragmentos

**Problema**: Atualização manual constante é inconveniente.

**Solução**: `@st.fragment` com `run_every` para atualização automática.

```python
@st.fragment(run_every=timedelta(minutes=INTERVALO_ATUALIZACAO))
def atualizar_clima_automatico():
    dados = obter_dados_otimizado()
    dados = atualizar_clima_todos_bairros(dados)
    salvar_dados(dados)
```

**Resultado**: Dados atualizados automaticamente a cada 10 minutos sem recarregar a página.

### 9.6 Tabela de Impacto das Otimizações

| Otimização | Antes | Depois | Melhoria |
|------------|-------|--------|----------|
| Atualização de clima | ~15s | ~1-2s | ~90% |
| Requisições repetidas | Nova requisição | Cache | ~100% |
| Leitura de dados | A cada interação | Uma vez | ~95% |
| Atualização manual | Necessária | Automática | UX melhorada |

---

## 10. Fluxo de Funcionamento

### 10.1 Fluxo de Reporte (Crowdsourcing)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Usuário   │────▶│   Clica em  │────▶│  votos += 1 │────▶│   Salva no  │
│ seleciona   │     │  "REPORTAR  │     │             │     │    JSON     │
│   bairro    │     │ ALAGAMENTO" │     │             │     │             │
└─────────────┘     └─────────────┘     └──────┬──────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │ votos >= 5? │
                                        └──────┬──────┘
                                               │
                              ┌────────────────┼────────────────┐
                              │ SIM            │                │ NÃO
                              ▼                │                ▼
                    ┌─────────────────┐        │      ┌─────────────────┐
                    │     Status =    │        │      │    Status =     │
                    │    "ALAGADO     │        │      │    "Atenção"    │
                    │   CONFIRMADO"   │        │      │                 │
                    └─────────────────┘        │      └─────────────────┘
```

### 10.2 Fluxo de Atualização Meteorológica

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Admin     │────▶│  Para cada  │────▶│  Consulta   │────▶│  Atualiza   │
│   clica em  │     │   bairro    │     │  API Open-  │     │ chuva_real  │
│  "Atualizar │     │             │     │    Meteo    │     │             │
│    Clima"   │     │             │     │             │     │             │
└─────────────┘     └─────────────┘     └──────┬──────┘     └──────┬──────┘
                                               │                    │
                                               ▼                    ▼
                                        ┌─────────────┐     ┌─────────────┐
                                        │ chuva>10mm? │────▶│   Salva no  │
                                        └──────┬──────┘     │    JSON     │
                                               │            └─────────────┘
                              ┌────────────────┼────────────────┐
                              │ SIM            │                │ NÃO
                              ▼                │                ▼
                    ┌─────────────────┐        │      ┌─────────────────┐
                    │     Status =    │        │      │   Mantém status │
                    │     "Risco      │        │      │     atual       │
                    │  Meteorológico" │        │      │                 │
                    └─────────────────┘        │      └─────────────────┘
```

---

## 11. Processo de Instalação e Execução

### 11.1 Pré-requisitos
- Sistema Operacional: Linux (Ubuntu 22.04+)
- Python 3.12 ou superior
- Acesso à internet (para API)

### 11.2 Passo a Passo da Instalação

#### Passo 1: Instalar pacote venv (se necessário)
```bash
sudo apt install python3.12-venv
```

#### Passo 2: Criar ambiente virtual
```bash
python3 -m venv venv
```

#### Passo 3: Ativar ambiente virtual
```bash
source venv/bin/activate
```

#### Passo 4: Instalar dependências
```bash
pip install streamlit requests pandas
```

#### Passo 5: Criar arquivo de dados inicial
```bash
python3 resetar_bairros.py
```

#### Passo 6: Executar a aplicação
```bash
streamlit run app.py
```

### 11.3 Acessando a Aplicação
Após executar, acesse no navegador:
- **Local**: http://localhost:8501
- **Rede**: http://[SEU-IP]:8501

---

## 12. Conceitos Acadêmicos Aplicados

### 12.1 Crowdsourcing
**Definição**: Modelo de produção que utiliza a inteligência coletiva e conhecimentos voluntários espalhados pela internet para resolver problemas ou criar conteúdo.

**Aplicação no Projeto**: Os cidadãos de Guarujá atuam como "sensores humanos", reportando alagamentos em tempo real, validando coletivamente a situação de cada bairro.

### 12.2 API REST
**Definição**: Arquitetura de software que define um conjunto de restrições para criação de serviços web, utilizando o protocolo HTTP.

**Aplicação no Projeto**: Consumo da API Open-Meteo para obtenção de dados meteorológicos em tempo real.

### 12.3 Persistência de Dados
**Definição**: Característica de dados que continuam a existir mesmo após o término do processo que os criou.

**Aplicação no Projeto**: Utilização de arquivo JSON para armazenar estado dos bairros entre sessões.

### 12.4 MVP (Minimum Viable Product)
**Definição**: Versão de um produto com funcionalidades mínimas suficientes para validar a proposta de valor junto aos usuários.

**Aplicação no Projeto**: Sistema implementado com funcionalidades essenciais (reporte, visualização, integração API) sem recursos avançados.

---

## 13. Possíveis Evoluções Futuras

| Evolução | Descrição | Complexidade |
|----------|-----------|--------------|
| Banco de Dados SQL | Migrar de JSON para PostgreSQL/MySQL | Média |
| Autenticação | Login de usuários para evitar múltiplos votos | Média |
| Notificações Push | Alertas automáticos via WhatsApp/Telegram | Alta |
| Machine Learning | Previsão de alagamentos com base em histórico | Alta |
| App Mobile | Versão para Android/iOS | Alta |
| Dashboard Administrativo | Painel com analytics e relatórios | Média |

---

## 14. Conclusão

O Sistema de Monitoramento de Alagamentos desenvolvido demonstra a viabilidade de soluções tecnológicas de baixo custo para problemas urbanos reais. A combinação de dados oficiais (API meteorológica) com inteligência coletiva (crowdsourcing) cria um sistema robusto e confiável.

O uso de tecnologias modernas como Python, Streamlit e APIs REST permite desenvolvimento ágil e manutenção simplificada, tornando o projeto escalável e adaptável a outras cidades com problemas similares.

---

## 15. Referências

1. **Streamlit Documentation** - https://docs.streamlit.io/
2. **Open-Meteo API** - https://open-meteo.com/en/docs
3. **Python Requests Library** - https://requests.readthedocs.io/
4. **Pandas Documentation** - https://pandas.pydata.org/docs/
5. **PEP 668 - Externally Managed Environments** - https://peps.python.org/pep-0668/

---

*Documento atualizado em: Fevereiro de 2026*
*Projeto Integrador - Tecnologia da Informação*

---

## Histórico de Atualizações

| Data | Versão | Alterações |
|------|--------|------------|
| Fev/2024 | 1.0 | Versão inicial do documento |
| Fev/2026 | 2.0 | Adicionadas otimizações de performance (chamadas paralelas, cache, session_state), nova métrica de probabilidade de chuva, regra de automação por probabilidade, atualização da integração com API Open-Meteo |
