"""
=============================================================================
SCRIPT DE SETUP - SISTEMA DE MONITORAMENTO DE ALAGAMENTOS GUARUJÁ/SP
=============================================================================
Projeto Integrador - Tecnologia da Informação

Descrição:
    Este script é responsável por criar/resetar o arquivo de dados (dados.json)
    que serve como base de persistência para o sistema de monitoramento.

Tecnologias Utilizadas:
    - Python 3.10+
    - Módulo json (nativo): Para serialização de dados em formato JSON

Autor: [Seu Nome]
Data: 2024
=============================================================================
"""

# =============================================================================
# IMPORTAÇÃO DE BIBLIOTECAS
# =============================================================================
# O módulo 'json' é uma biblioteca nativa do Python que permite converter
# estruturas de dados Python (dicionários, listas) para o formato JSON
# (JavaScript Object Notation), amplamente usado para troca de dados na web.
import json

# =============================================================================
# DEFINIÇÃO DOS DADOS DOS BAIRROS
# =============================================================================
# Aqui definimos uma lista de dicionários contendo os 15 principais bairros
# do município de Guarujá/SP. Cada bairro possui:
#   - id: Identificador único numérico
#   - nome: Nome oficial do bairro
#   - lat/lon: Coordenadas geográficas aproximadas (latitude e longitude)
#   - status: Estado atual do bairro (Normal, Atenção, Alagado, etc.)
#   - risco: Nível de risco (Baixo, Médio, Alto, Crítico)
#   - votos: Contador de reportes da comunidade (Crowdsourcing)
#   - chuva_real: Última leitura de precipitação da API meteorológica (mm)
#   - temperatura: Temperatura atual em graus Celsius
#   - probabilidade_chuva: Probabilidade de precipitação na hora atual (%)
#   - precipitacao_proxima_hora: Precipitação esperada na próxima hora (mm)

bairros_guaruja = [
    {
        "id": 1,
        "nome": "Pitangueiras",
        "lat": -23.9930,
        "lon": -46.2564,
        "status": "Normal",
        "risco": "Baixo",
        "votos": 0,
        "chuva_real": 0.0,
        "temperatura": 0.0,
        "probabilidade_chuva": 0,
        "precipitacao_proxima_hora": 0.0
    },
    {
        "id": 2,
        "nome": "Enseada",
        "lat": -23.9785,
        "lon": -46.2289,
        "status": "Normal",
        "risco": "Baixo",
        "votos": 0,
        "chuva_real": 0.0,
        "temperatura": 0.0,
        "probabilidade_chuva": 0,
        "precipitacao_proxima_hora": 0.0
    },
    {
        "id": 3,
        "nome": "Vicente de Carvalho",
        "lat": -23.9372,
        "lon": -46.3178,
        "status": "Normal",
        "risco": "Baixo",
        "votos": 0,
        "chuva_real": 0.0,
        "temperatura": 0.0,
        "probabilidade_chuva": 0,
        "precipitacao_proxima_hora": 0.0
    },
    {
        "id": 4,
        "nome": "Santo Antônio",
        "lat": -23.9890,
        "lon": -46.2680,
        "status": "Normal",
        "risco": "Baixo",
        "votos": 0,
        "chuva_real": 0.0,
        "temperatura": 0.0,
        "probabilidade_chuva": 0,
        "precipitacao_proxima_hora": 0.0
    },
    {
        "id": 5,
        "nome": "Astúrias",
        "lat": -23.9988,
        "lon": -46.2478,
        "status": "Normal",
        "risco": "Baixo",
        "votos": 0,
        "chuva_real": 0.0,
        "temperatura": 0.0,
        "probabilidade_chuva": 0,
        "precipitacao_proxima_hora": 0.0
    },
    {
        "id": 6,
        "nome": "Tombo",
        "lat": -24.0085,
        "lon": -46.2612,
        "status": "Normal",
        "risco": "Baixo",
        "votos": 0,
        "chuva_real": 0.0,
        "temperatura": 0.0,
        "probabilidade_chuva": 0,
        "precipitacao_proxima_hora": 0.0
    },
    {
        "id": 7,
        "nome": "Morrinhos",
        "lat": -23.9520,
        "lon": -46.2450,
        "status": "Normal",
        "risco": "Baixo",
        "votos": 0,
        "chuva_real": 0.0,
        "temperatura": 0.0,
        "probabilidade_chuva": 0,
        "precipitacao_proxima_hora": 0.0
    },
    {
        "id": 8,
        "nome": "Santa Cruz dos Navegantes",
        "lat": -23.9650,
        "lon": -46.2520,
        "status": "Normal",
        "risco": "Baixo",
        "votos": 0,
        "chuva_real": 0.0,
        "temperatura": 0.0,
        "probabilidade_chuva": 0,
        "precipitacao_proxima_hora": 0.0
    },
    {
        "id": 9,
        "nome": "Perequê",
        "lat": -23.9580,
        "lon": -46.2150,
        "status": "Normal",
        "risco": "Baixo",
        "votos": 0,
        "chuva_real": 0.0,
        "temperatura": 0.0,
        "probabilidade_chuva": 0,
        "precipitacao_proxima_hora": 0.0
    },
    {
        "id": 10,
        "nome": "Jardim Boa Esperança",
        "lat": -23.9420,
        "lon": -46.3050,
        "status": "Normal",
        "risco": "Baixo",
        "votos": 0,
        "chuva_real": 0.0,
        "temperatura": 0.0,
        "probabilidade_chuva": 0,
        "precipitacao_proxima_hora": 0.0
    },
    {
        "id": 11,
        "nome": "Jardim Progresso",
        "lat": -23.9350,
        "lon": -46.3100,
        "status": "Normal",
        "risco": "Baixo",
        "votos": 0,
        "chuva_real": 0.0,
        "temperatura": 0.0,
        "probabilidade_chuva": 0,
        "precipitacao_proxima_hora": 0.0
    },
    {
        "id": 12,
        "nome": "Pae Cará",
        "lat": -23.9280,
        "lon": -46.2980,
        "status": "Normal",
        "risco": "Baixo",
        "votos": 0,
        "chuva_real": 0.0,
        "temperatura": 0.0,
        "probabilidade_chuva": 0,
        "precipitacao_proxima_hora": 0.0
    },
    {
        "id": 13,
        "nome": "Jardim Las Palmas",
        "lat": -23.9680,
        "lon": -46.2380,
        "status": "Normal",
        "risco": "Baixo",
        "votos": 0,
        "chuva_real": 0.0,
        "temperatura": 0.0,
        "probabilidade_chuva": 0,
        "precipitacao_proxima_hora": 0.0
    },
    {
        "id": 14,
        "nome": "Jardim Virgínia",
        "lat": -23.9480,
        "lon": -46.2650,
        "status": "Normal",
        "risco": "Baixo",
        "votos": 0,
        "chuva_real": 0.0,
        "temperatura": 0.0,
        "probabilidade_chuva": 0,
        "precipitacao_proxima_hora": 0.0
    },
    {
        "id": 15,
        "nome": "Praia do Guaiúba",
        "lat": -24.0150,
        "lon": -46.2750,
        "status": "Normal",
        "risco": "Baixo",
        "votos": 0,
        "chuva_real": 0.0,
        "temperatura": 0.0,
        "probabilidade_chuva": 0,
        "precipitacao_proxima_hora": 0.0
    }
]

# =============================================================================
# FUNÇÃO PRINCIPAL DE CRIAÇÃO DO ARQUIVO
# =============================================================================
def criar_arquivo_dados():
    """
    Função responsável por criar o arquivo dados.json com os dados iniciais.

    Utiliza o método json.dump() para serializar a lista de bairros em formato
    JSON e salvá-la em um arquivo no disco local.

    Parâmetros do json.dump():
        - indent=4: Formata o JSON com indentação de 4 espaços (legibilidade)
        - ensure_ascii=False: Permite caracteres especiais (acentos em português)
    """
    # Nome do arquivo de saída
    nome_arquivo = "dados.json"

    # Abrindo arquivo para escrita com encoding UTF-8
    # O 'with' garante que o arquivo será fechado corretamente após o uso
    with open(nome_arquivo, "w", encoding="utf-8") as arquivo:
        # Serializa e escreve os dados no arquivo JSON
        json.dump(bairros_guaruja, arquivo, indent=4, ensure_ascii=False)

    # Feedback para o usuário
    print("=" * 60)
    print("SISTEMA DE MONITORAMENTO DE ALAGAMENTOS - GUARUJÁ/SP")
    print("=" * 60)
    print(f"\n[OK] Arquivo '{nome_arquivo}' criado com sucesso!")
    print(f"[OK] Total de bairros cadastrados: {len(bairros_guaruja)}")
    print("\nBairros incluídos:")
    print("-" * 40)

    # Lista todos os bairros cadastrados
    for bairro in bairros_guaruja:
        print(f"  {bairro['id']:2d}. {bairro['nome']}")

    print("-" * 40)
    print("\n[INFO] Execute 'streamlit run app.py' para iniciar o sistema.")
    print("=" * 60)

# =============================================================================
# PONTO DE ENTRADA DO SCRIPT
# =============================================================================
# O bloco abaixo garante que a função criar_arquivo_dados() só será executada
# quando este script for rodado diretamente (não quando importado como módulo).
if __name__ == "__main__":
    criar_arquivo_dados()
