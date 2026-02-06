# 🌊 Sistema de Monitoramento de Alagamentos - Guarujá/SP

![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.54.0-FF4B4B)
![Status](https://img.shields.io/badge/status-MVP-success)
![License](https://img.shields.io/badge/license-MIT-green)

> **Projeto Integrador - Univesp (Tecnologia da Informação)**

Um sistema de monitoramento em tempo real focado na cidade de Guarujá/SP, combinando dados meteorológicos oficiais com inteligência coletiva (*crowdsourcing*) para prevenção de desastres e auxílio à mobilidade urbana.

![Dashboard Preview](assets/dashboard-preview.png)
*Exemplo da interface v2.0 com mapa interativo e métricas em tempo real.*

---

## 🎯 Objetivo

Desenvolver um **MVP (Minimum Viable Product)** que resolva a falta de centralização de informações sobre alagamentos. A solução propõe uma arquitetura híbrida:
1.  **Dados Oficiais:** Integração com API Open-Meteo para precipitação e probabilidade de chuva.
2.  **Colaboração Cidadã:** Usuários reportam a situação local, validando o estado real das vias.

## 🛠️ Stack Tecnológica

O projeto foi construído utilizando **Python** como linguagem base, priorizando desenvolvimento rápido e código limpo.

| Componente | Tecnologia | Função |
|------------|------------|--------|
| **Frontend/Backend** | [Streamlit](https://streamlit.io/) | Framework para Web Apps de Data Science. |
| **Integração API** | `requests` | Consumo da API Open-Meteo. |
| **Visualização** | [Pydeck](https://pydeck.gl/) | Renderização de mapas interativos baseados em camadas. |
| **Gráficos** | [Plotly](https://plotly.com/) | Gráficos dinâmicos de previsão meteorológica. |
| **Concorrência** | `concurrent.futures` | Paralelismo para otimização de requisições HTTP. |
| **Persistência** | JSON | Armazenamento leve de estado (NoSQL approach para MVP). |
