# Atualização Automática de Temperatura e Precipitação

## Resumo da Implementação

Implementação de atualização automática de dados meteorológicos (temperatura e precipitação) utilizando a API Open-Meteo no Sistema de Monitoramento de Alagamentos de Guarujá/SP.

---

## Alterações Realizadas

### 1. Importação de `timedelta`
**Arquivo:** `app.py` (linha 56)

Adicionada importação do módulo `timedelta` para definir intervalos de tempo na atualização automática.

```python
from datetime import datetime, timedelta
```

### 2. Nova Constante de Configuração
**Arquivo:** `app.py` (linha 84)

Adicionada constante para configurar o intervalo de atualização automática.

```python
INTERVALO_ATUALIZACAO = 5  # Intervalo em minutos para atualização automática do clima
```

### 3. Função `buscar_clima_api()` Atualizada
**Arquivo:** `app.py` (linhas 145-200)

A função agora retorna tanto a precipitação quanto a temperatura:

- **Antes:** Retornava apenas `float` (precipitação em mm)
- **Depois:** Retorna `dict` com `{"chuva": float, "temperatura": float}`

Parâmetro da API alterado:
```python
"current": "rain,temperature_2m"  # Solicita chuva e temperatura atual
```

### 4. Função `atualizar_clima_todos_bairros()` Atualizada
**Arquivo:** `app.py` (linhas 203-234)

Adaptada para processar o novo formato de retorno da API, salvando tanto a precipitação quanto a temperatura em cada bairro.

```python
clima = buscar_clima_api(bairro["lat"], bairro["lon"])
bairro["chuva_real"] = clima["chuva"]
bairro["temperatura"] = clima["temperatura"]
```

### 5. Novo Fragmento de Atualização Automática
**Arquivo:** `app.py` (linhas 237-265)

Criada função com decorator `@st.fragment(run_every=...)` que executa automaticamente a cada X minutos:

```python
@st.fragment(run_every=timedelta(minutes=INTERVALO_ATUALIZACAO))
def atualizar_clima_automatico():
    dados = carregar_dados()
    if dados:
        dados = atualizar_clima_todos_bairros(dados)
        salvar_dados(dados)
        st.session_state.ultima_atualizacao_auto = datetime.now()
```

### 6. Interface Atualizada

#### Painel do Bairro (4 métricas)
- 🌡️ Temperatura (nova)
- 🌧️ Chuva Agora
- 📢 Reportes
- ⚡ Nível de Risco

#### Sidebar - Informações do Sistema
- Exibe intervalo de atualização automática
- Mostra timestamp da última atualização automática

#### Tabela de Resumo Geral
- Nova coluna: `Temp (°C)`

### 7. Estrutura de Dados Atualizada
**Arquivo:** `resetar_bairros.py`

Adicionado campo `temperatura` em cada bairro:

```python
{
    "id": 1,
    "nome": "Pitangueiras",
    "lat": -23.9930,
    "lon": -46.2564,
    "status": "Normal",
    "risco": "Baixo",
    "votos": 0,
    "chuva_real": 0.0,
    "temperatura": 0.0  # NOVO CAMPO
}
```

---

## Arquivos Modificados

| Arquivo | Descrição |
|---------|-----------|
| `app.py` | Lógica principal com atualização automática e exibição de temperatura |
| `resetar_bairros.py` | Estrutura de dados com novo campo `temperatura` |

---

## Como Funciona

1. Ao iniciar a aplicação, o fragmento `atualizar_clima_automatico()` é chamado
2. A cada 5 minutos (configurável), o fragmento executa automaticamente
3. Para cada bairro, a API Open-Meteo é consultada
4. Temperatura e precipitação são atualizadas no arquivo `dados.json`
5. A interface reflete os novos dados sem necessidade de recarregar a página

---

## Configuração

Para alterar o intervalo de atualização, modifique a constante no `app.py`:

```python
INTERVALO_ATUALIZACAO = 5  # Altere para o valor desejado em minutos
```

---

## API Utilizada

**Open-Meteo API** (https://open-meteo.com/)

Endpoint: `https://api.open-meteo.com/v1/forecast`

Parâmetros:
- `latitude`: Coordenada do bairro
- `longitude`: Coordenada do bairro
- `current`: `rain,temperature_2m`
- `timezone`: `America/Sao_Paulo`

---

## Data da Implementação

**Fevereiro de 2026**
