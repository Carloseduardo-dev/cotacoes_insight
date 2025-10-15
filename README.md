# 📈 Cotacoes Insight

Uma aplicação web minimalista construída com Streamlit para análise de cotações de ativos financeiros. O projeto demonstra o uso de um padrão **MapReduce** local para processamento de dados em paralelo, busca de dados em tempo real via API e visualização interativa de gráficos com Plotly.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.27+-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 📜 Índice

- [Funcionalidades](#-funcionalidades)
- [Tecnologias Utilizadas](#-tecnologias-utilizadas)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Como Executar](#-como-executar)
  - [Pré-requisitos](#pré-requisitos)
  - [Instalação e Execução](#instalação-e-execução)
- [Explicação dos Módulos](#-explicação-dos-módulos)

## ✨ Funcionalidades

- **Busca de Dados Dinâmica**: Obtém dados históricos de ações da API do Yahoo Finance.
- **Processamento Paralelo**: Utiliza um padrão **MapReduce** com o módulo `multiprocessing` do Python para calcular estatísticas básicas (média, mínimo, máximo, desvio padrão) de forma eficiente.
- **Cálculo de Métricas Financeiras**:
  - Retornos diários
  - Volatilidade anualizada
  - Retorno acumulado
  - Drawdown máximo
  - Média móvel customizável
- **Dashboard Interativo**: Visualização de preços e médias móveis com gráficos interativos gerados pela biblioteca **Plotly**.
- **Exportação de Dados**: Permite o download dos dados brutos em formato **CSV**.

## 🛠️ Tecnologias Utilizadas

- **Linguagem**: Python 3
- **Interface Web**: Streamlit
- **Manipulação de Dados**: Pandas
- **Cálculos Numéricos**: NumPy
- **Visualização de Dados**: Plotly
- **API de Dados Financeiros**: yfinance
- **Processamento Paralelo**: Módulo nativo `multiprocessing` do Python.

## 📁 Estrutura do Projeto

A estrutura de arquivos foi organizada para separar as responsabilidades:

```
cotacoes-insight/
├── .venv/                  # Pasta do ambiente virtual
├── app.py                  # Arquivo principal da aplicação Streamlit (UI e orquestração)
├── data_loader.py          # Módulo para buscar dados da API do Yahoo Finance
├── mapreduce_utils.py      # Módulo com a lógica de MapReduce e cálculos estatísticos
├── requirements.txt        # Lista de dependências do projeto
└── README.md               # Este arquivo
```

## ▶️ Como Executar

### Pré-requisitos

- **Python 3.9** ou superior.

### Instalação e Execução

Siga os passos abaixo para executar a aplicação em sua máquina local.

1. **Clone o repositório (opcional):**

   ```bash
   git clone https://github.com/Carloseduardo-dev/cotacoes_insight.git
   cd cotacoes-insight
   ```

2. **Crie e ative um ambiente virtual:**

   ```bash
   # Criar o ambiente
   python -m venv .venv

   # Ativar no Windows
   .venv\Scripts\activate

   # Ativar no Linux / macOS
   source .venv/bin/activate
   ```

3. **Instale as dependências:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Execute a aplicação Streamlit:**

```bash
streamlit run app.py
```
