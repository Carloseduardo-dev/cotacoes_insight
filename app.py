import streamlit as st
from data_loader import fetch_data
from mapreduce_utils import map_reduce_stats
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from multiprocessing import freeze_support
import numpy as np


def calcular_rsi(df, periodo=14):
    """Calcula o Índice de Força Relativa (RSI)."""
    delta = df['Close'].diff()
    ganho = (delta.where(delta > 0, 0)).rolling(window=periodo).mean()
    perda = (-delta.where(delta < 0, 0)).rolling(window=periodo).mean()
    rs = ganho / perda
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calcular_bandas_bollinger(df, periodo=20, num_std=2):
    """Calcula as Bandas de Bollinger."""
    sma = df['Close'].rolling(window=periodo).mean()
    std = df['Close'].rolling(window=periodo).std()
    banda_superior = sma + (std * num_std)
    banda_inferior = sma - (std * num_std)
    return sma, banda_superior, banda_inferior


def calcular_macd(df, rapido=12, lento=26, sinal=9):
    """Calcula o MACD (Moving Average Convergence Divergence)."""
    ema_rapida = df['Close'].ewm(span=rapido, adjust=False).mean()
    ema_lenta = df['Close'].ewm(span=lento, adjust=False).mean()
    macd = ema_rapida - ema_lenta
    linha_sinal = macd.ewm(span=sinal, adjust=False).mean()
    histograma = macd - linha_sinal
    return macd, linha_sinal, histograma


def calcular_score_performance(retorno_acumulado, volatilidade):
    """Calcula um score de 0-10 baseado em retorno e volatilidade."""
    # Normalizar retorno (-50% a +50% -> 0 a 10)
    score_retorno = min(max((retorno_acumulado * 100 + 50) / 10, 0), 10)
    
    # Penalizar alta volatilidade (0-100% volatilidade -> penalidade de 0-5 pontos)
    penalidade_volatilidade = min((volatilidade * 100) / 20, 5)
    
    score_final = max(score_retorno - penalidade_volatilidade, 0)
    return round(score_final, 1)


def obter_cor_semaforo(volatilidade):
    """Retorna cor e texto do semáforo de risco baseado na volatilidade."""
    vol_pct = volatilidade * 100
    if vol_pct < 20:
        return "#10b981", "Baixo Risco", "🟢"
    elif vol_pct < 40:
        return "#f59e0b", "Risco Moderado", "🟡"
    else:
        return "#ef4444", "Alto Risco", "🔴"


def mostrar_glossario():
    """Exibe o glossário de termos financeiros."""
    glossario = {
        "Volatilidade": "Mede o quanto o preço da ação sobe e desce. Alta volatilidade = maior risco, mas também maiores oportunidades de ganho.",
        "Retorno Acumulado": "O ganho ou perda total que você teria se tivesse comprado a ação no início do período e vendido no final. Exemplo: 15% = ganhou R$ 15 para cada R$ 100 investidos.",
        "RSI": "Índice de Força Relativa. Indica se a ação está sobrecomprada (muito cara, pode cair) ou sobrevendida (muito barata, pode subir). Valores: acima de 70 = sobrecomprada, abaixo de 30 = sobrevendida.",
        "Bandas de Bollinger": "Mostram a 'zona de conforto' do preço da ação. Quando o preço sai das bandas, pode indicar uma reversão (mudança de direção).",
        "MACD": "Mostra a força e direção da tendência. Quando a linha azul cruza acima da vermelha = sinal de compra. Quando cruza abaixo = sinal de venda.",
        "Média Móvel": "Preço médio da ação nos últimos X dias. Ajuda a suavizar as oscilações e identificar tendências.",
        "Candlestick": "Gráfico de velas que mostra abertura, fechamento, máxima e mínima do preço em cada período. Verde = fechou em alta, Vermelho = fechou em baixa.",
        "Volume": "Quantidade de ações negociadas. Alto volume = muita gente comprando/vendendo (maior confiança no movimento).",
        "Rebaixamento Máximo": "A maior queda que o preço teve do pico até o vale. Exemplo: -20% = em algum momento, a ação caiu 20% do valor mais alto.",
        "Score de Performance": "Nota de 0 a 10 que combina retorno e risco. Quanto maior, melhor foi o desempenho considerando o risco assumido.",
        "Semáforo de Risco": "Verde = baixo risco (ação estável), Amarelo = risco moderado, Vermelho = alto risco (ação muito volátil)."
    }
    
    with st.expander("📚 GLOSSÁRIO - Clique para ver explicações dos termos", expanded=False):
        st.markdown("### Entenda os termos financeiros de forma simples:")
        for termo, explicacao in glossario.items():
            st.markdown(f"""
            <div style="background-color: #f0f9ff; border-left: 4px solid #3b82f6; padding: 15px; margin: 10px 0; border-radius: 5px;">
                <strong style="color: #1e40af; font-size: 1.1em;">❓ {termo}</strong><br>
                <span style="color: #374151; margin-top: 5px; display: inline-block;">{explicacao}</span>
            </div>
            """, unsafe_allow_html=True)


def comparar_acoes(tickers_dict, tickers_selecionados, period, interval):
    """Compara múltiplas ações lado a lado."""
    st.markdown("## 🔄 Comparação entre Ações")
    
    if len(tickers_selecionados) < 2:
        st.warning("⚠️ Selecione pelo menos 2 ações para comparar")
        return
    
    # Buscar dados de todas as ações
    dados_acoes = {}
    with st.spinner("Buscando dados das ações selecionadas..."):
        for nome in tickers_selecionados:
            ticker = tickers_dict[nome]
            df = fetch_data(ticker, period=period, interval=interval)
            if df is not None and not df.empty:
                dados_acoes[nome] = df
    
    if len(dados_acoes) < 2:
        st.error("❌ Não foi possível carregar dados suficientes para comparação")
        return
    
    # Normalizar preços para comparação (base 100)
    st.markdown("### 📈 Desempenho Comparativo (Base 100)")
    st.info("💡 **Como ler este gráfico:** Todas as ações começam em 100. Se uma linha está em 120, significa que valorizou 20% no período.")
    
    fig_comp = go.Figure()
    
    cores = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6']
    
    for idx, (nome, df) in enumerate(dados_acoes.items()):
        # Normalizar para base 100
        preco_inicial = df['Close'].iloc[0]
        preco_normalizado = (df['Close'] / preco_inicial) * 100
        
        fig_comp.add_trace(go.Scatter(
            x=df.index,
            y=preco_normalizado,
            mode='lines',
            name=nome,
            line=dict(color=cores[idx % len(cores)], width=3)
        ))
    
    fig_comp.update_layout(
        xaxis_title="Data",
        yaxis_title="Desempenho (Base 100)",
        template="plotly_white",
        height=500,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig_comp, use_container_width=True)
    
    # Tabela comparativa de métricas
    st.markdown("### 📊 Tabela Comparativa de Métricas")
    
    metricas_comparacao = []
    
    for nome, df in dados_acoes.items():
        results = map_reduce_stats(df.copy(), 
                                   metrics=["mean", "min", "max", "volatility", "cumulative_return"],
                                   moving_average_days=10)
        
        retorno_pct = results.get("cumulative_return", 0) * 100
        volatilidade_pct = results.get("volatility", 0) * 100
        
        metricas_comparacao.append({
            "Ação": nome,
            "Preço Atual (R$)": f"{df['Close'].iloc[-1]:.2f}",
            "Retorno (%)": f"{retorno_pct:+.2f}%",
            "Volatilidade (%)": f"{volatilidade_pct:.2f}%",
            "Mínimo (R$)": f"{results.get('min', 0):.2f}",
            "Máximo (R$)": f"{results.get('max', 0):.2f}",
            "Preço Médio (R$)": f"{results.get('mean', 0):.2f}"
        })
    
    df_comparacao = pd.DataFrame(metricas_comparacao)
    
    # Destacar melhor retorno e menor volatilidade
    st.dataframe(df_comparacao, use_container_width=True, hide_index=True)
    
    # Análise automatizada
    st.markdown("### 🎯 Análise Rápida")
    
    # Encontrar melhor e pior desempenho
    retornos = {m["Ação"]: float(m["Retorno (%)"].replace("%", "").replace("+", "")) 
                for m in metricas_comparacao}
    melhor_acao = max(retornos, key=retornos.get)
    pior_acao = min(retornos, key=retornos.get)
    
    volatilidades = {m["Ação"]: float(m["Volatilidade (%)"].replace("%", "")) 
                     for m in metricas_comparacao}
    mais_estavel = min(volatilidades, key=volatilidades.get)
    mais_volatil = max(volatilidades, key=volatilidades.get)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div style="background-color: #10b98120; border-left: 4px solid #10b981; padding: 15px; border-radius: 5px;">
            <strong style="color: #10b981;">🏆 Melhor Desempenho</strong><br>
            <span style="font-size: 1.3em;">{melhor_acao}</span><br>
            <span style="color: #059669;">Retorno: {retornos[melhor_acao]:+.2f}%</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="background-color: #3b82f620; border-left: 4px solid #3b82f6; padding: 15px; border-radius: 5px; margin-top: 15px;">
            <strong style="color: #3b82f6;">🛡️ Mais Estável</strong><br>
            <span style="font-size: 1.3em;">{mais_estavel}</span><br>
            <span style="color: #2563eb;">Volatilidade: {volatilidades[mais_estavel]:.2f}%</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="background-color: #ef444420; border-left: 4px solid #ef4444; padding: 15px; border-radius: 5px;">
            <strong style="color: #ef4444;">📉 Pior Desempenho</strong><br>
            <span style="font-size: 1.3em;">{pior_acao}</span><br>
            <span style="color: #dc2626;">Retorno: {retornos[pior_acao]:+.2f}%</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="background-color: #f59e0b20; border-left: 4px solid #f59e0b; padding: 15px; border-radius: 5px; margin-top: 15px;">
            <strong style="color: #f59e0b;">⚡ Mais Volátil</strong><br>
            <span style="font-size: 1.3em;">{mais_volatil}</span><br>
            <span style="color: #d97706;">Volatilidade: {volatilidades[mais_volatil]:.2f}%</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")


def pagina_cotacoes():
    """Página de análise de cotações."""
    st.title("📊 Análise de Cotações")
    st.markdown("Análise simples e rápida de ações")
    
    # Glossário no topo
    mostrar_glossario()
    
    st.divider()

    # Lista de ações disponíveis
    tickers_disponiveis = {
        "Apple": "AAPL",
        "Microsoft": "MSFT",
        "Google": "GOOGL",
        "Amazon": "AMZN",
        "Tesla": "TSLA",
        "Meta": "META",
        "Nvidia": "NVDA",
        "Petrobras": "PETR4.SA",
        "Vale": "VALE3.SA",
        "Bradesco": "BBDC4.SA",
        "Itaú": "ITUB4.SA",
        "B3": "B3SA3.SA",
    }
    
    # Modo de análise: Individual ou Comparação
    st.markdown("## 🎯 Modo de Análise")
    modo = st.radio("Escolha o modo", ["📊 Análise Individual", "🔄 Comparar Ações"], horizontal=True, label_visibility="collapsed")
    
    st.divider()
    
    # Seção de busca centralizada na tela principal
    st.markdown("## 🔍 Buscar Ação")
    
    if modo == "📊 Análise Individual":
        col1, col2, col3 = st.columns(3)
        with col1:
            ticker_nome = st.selectbox("Selecione a ação", list(tickers_disponiveis.keys()), label_visibility="visible", key="ticker_select")
            ticker = tickers_disponiveis[ticker_nome]
        with col2:
            opcoes_periodo = {
                "1 mês": "1mo",
                "3 meses": "3mo",
                "6 meses": "6mo",
                "1 ano": "1y",
                "2 anos": "2y"
            }
            period_nome = st.selectbox("Período", list(opcoes_periodo.keys()), index=2, label_visibility="visible", key="period_select")
            period = opcoes_periodo[period_nome]
        with col3:
            opcoes_intervalo = {
                "Diário": "1d",
                "Semanal": "1wk",
                "Horário": "1h"
            }
            interval_nome = st.selectbox("Intervalo", list(opcoes_intervalo.keys()), index=0, label_visibility="visible", key="interval_select")
            interval = opcoes_intervalo[interval_nome]
    else:
        # Modo comparação
        col1, col2, col3 = st.columns(3)
        with col1:
            acoes_comparar = st.multiselect(
                "Selecione as ações (2-5)",
                list(tickers_disponiveis.keys()),
                default=["Apple", "Microsoft"],
                max_selections=5,
                key="acoes_comparar"
            )
        with col2:
            opcoes_periodo = {
                "1 mês": "1mo",
                "3 meses": "3mo",
                "6 meses": "6mo",
                "1 ano": "1y",
                "2 anos": "2y"
            }
            period_nome = st.selectbox("Período", list(opcoes_periodo.keys()), index=2, label_visibility="visible", key="period_select_comp")
            period = opcoes_periodo[period_nome]
        with col3:
            opcoes_intervalo = {
                "Diário": "1d",
                "Semanal": "1wk",
                "Horário": "1h"
            }
            interval_nome = st.selectbox("Intervalo", list(opcoes_intervalo.keys()), index=0, label_visibility="visible", key="interval_select_comp")
            interval = opcoes_intervalo[interval_nome]
    
    st.divider()
    
    # Se for modo comparação, executar a comparação e parar
    if modo == "🔄 Comparar Ações":
        comparar_acoes(tickers_disponiveis, acoes_comparar, period, interval)
        return
    
    # Configurações de métricas
    st.markdown("## ⚙️ Configurações")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        opcoes_metricas = {
            "Média": "mean",
            "Mínimo": "min",
            "Máximo": "max",
            "Desvio Padrão": "std",
            "Retornos": "returns",
            "Média Móvel": "moving_average",
            "Volatilidade": "volatility",
            "Retorno Acumulado": "cumulative_return",
            "Rebaixamento Máximo": "max_drawdown"
        }
        metrics_selecionadas = st.multiselect(
            "Métricas a calcular",
            list(opcoes_metricas.keys()),
            default=["Média", "Mínimo", "Máximo", "Retornos", "Volatilidade", "Retorno Acumulado"],
            key="metrics_select"
        )
        metrics = [opcoes_metricas[m] for m in metrics_selecionadas]
    
    with col2:
        days_ma = st.number_input("Dias (média móvel)", min_value=2, max_value=200, value=10, key="days_ma_input")
    
    with col3:
        show_table = st.checkbox("Mostrar tabela de dados", value=False, key="show_table_checkbox")
    
    st.divider()
    
    # Botão de busca centralizado
    col_center = st.columns([1, 2, 1])
    with col_center[1]:
        if st.button("🔎 Buscar", use_container_width=True, key="search_button"):
            st.session_state["reload"] = True
    
    st.divider()

    # Fetch dados
    if "reload" not in st.session_state:
        st.session_state["reload"] = True

    if st.session_state["reload"]:
        with st.spinner("Buscando dados..."):
            df = fetch_data(ticker, period=period, interval=interval)
        st.session_state["df"] = df
        st.session_state["reload"] = False
    else:
        df = st.session_state.get("df")

    # Caso não houver dados
    if df is None or df.empty:
        st.error(f"❌ Não foi possível carregar dados para {ticker}")
        st.info("💡 Verifique o ticker (ex: PETR4.SA para ações brasileiras)")
        st.stop()

    # Processar com MapReduce
    with st.spinner("Processando dados..."):
        results = map_reduce_stats(df.copy(), metrics=metrics, moving_average_days=int(days_ma))

    # Calcular indicadores técnicos
    rsi = calcular_rsi(df)
    sma_bb, banda_superior, banda_inferior = calcular_bandas_bollinger(df)
    macd, linha_sinal, histograma = calcular_macd(df)

    # SEÇÃO 1: Informações Principais com Score e Semáforo
    st.markdown(f"## {ticker_nome} ({ticker}) • {period_nome} • {interval_nome}")
    
    # Primeira linha: Semáforo e Score
    if "volatility" in results and "cumulative_return" in results:
        col_sem, col_score = st.columns(2)
        
        with col_sem:
            cor_semaforo, texto_risco, emoji_risco = obter_cor_semaforo(results["volatility"])
            st.markdown(f"""
            <div style="background-color: {cor_semaforo}20; border: 3px solid {cor_semaforo}; border-radius: 10px; padding: 20px; text-align: center;">
                <h3 style="margin: 0; color: #666;">Semáforo de Risco</h3>
                <h1 style="margin: 10px 0; color: {cor_semaforo}; font-size: 3em;">{emoji_risco}</h1>
                <h2 style="margin: 0; color: {cor_semaforo};">{texto_risco}</h2>
                <p style="margin: 5px 0; color: #666;">Volatilidade: {results["volatility"]*100:.1f}%</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col_score:
            score = calcular_score_performance(results["cumulative_return"], results["volatility"])
            cor_score = "#10b981" if score >= 7 else "#f59e0b" if score >= 5 else "#ef4444"
            st.markdown(f"""
            <div style="background-color: {cor_score}20; border: 3px solid {cor_score}; border-radius: 10px; padding: 20px; text-align: center;">
                <h3 style="margin: 0; color: #666;">Score de Performance</h3>
                <h1 style="margin: 10px 0; color: {cor_score}; font-size: 4em;">{score}</h1>
                <p style="margin: 0; color: #666;">de 10 pontos</p>
                <p style="margin: 5px 0; color: #666; font-size: 0.9em;">Baseado em retorno e risco</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Segunda linha: Métricas tradicionais
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if "mean" in results:
            st.metric(label="Preço Médio", value=f"R$ {results['mean']:.2f}")
    
    with col2:
        if "min" in results:
            st.metric(label="Preço Mínimo", value=f"R$ {results['min']:.2f}")
    
    with col3:
        if "max" in results:
            st.metric(label="Preço Máximo", value=f"R$ {results['max']:.2f}")
    
    with col4:
        if "volatility" in results:
            vol = results["volatility"] * 100
            st.metric(label="Volatilidade", value=f"{vol:.1f}%")
    
    with col5:
        if "cumulative_return" in results:
            ret = results["cumulative_return"] * 100
            st.metric(label="Retorno Acum.", value=f"{ret:.1f}%", delta=f"{ret:+.1f}%" if ret != 0 else None)

    # SEÇÃO 2: Gráfico de Candlestick
    st.markdown("## 📈 Gráfico de Velas (Candlestick)")
    
    fig_candle = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Preço'
    )])
    
    # Adicionar média móvel se selecionada
    if "moving_average" in metrics and f"ma_{days_ma}" in results:
        fig_candle.add_trace(
            go.Scatter(x=df.index, y=results[f"ma_{days_ma}"], 
                      mode="lines", name=f"Média Móvel {days_ma}d",
                      line=dict(color="#ff6b6b", width=2))
        )
    
    fig_candle.update_layout(
        xaxis_title="Data",
        yaxis_title="Preço (R$)",
        template="plotly_white",
        height=500,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        margin=dict(l=0, r=0, t=10, b=0)
    )
    
    st.plotly_chart(fig_candle, use_container_width=True)

    # SEÇÃO 3: Distribuição de Retornos (Pizza)
    if "returns" in results:
        st.markdown("## 🥧 Distribuição de Retornos Diários")
        
        returns_series = results["returns"].dropna()
        dias_positivos = (returns_series > 0).sum()
        dias_negativos = (returns_series < 0).sum()
        dias_neutros = (returns_series == 0).sum()
        
        col_pizza, col_stats = st.columns([1, 1])
        
        with col_pizza:
            fig_pizza = go.Figure(data=[go.Pie(
                labels=['Dias Positivos', 'Dias Negativos', 'Dias Neutros'],
                values=[dias_positivos, dias_negativos, dias_neutros],
                hole=0.4,
                marker=dict(colors=['#10b981', '#ef4444', '#9ca3af']),
                textinfo='label+percent',
                textfont=dict(size=14)
            )])
            
            fig_pizza.update_layout(
                height=350,
                showlegend=True,
                margin=dict(l=0, r=0, t=0, b=0)
            )
            
            st.plotly_chart(fig_pizza, use_container_width=True)
        
        with col_stats:
            total_dias = len(returns_series)
            st.markdown(f"""
            <div style="padding: 20px;">
                <h3>📊 Estatísticas de Retornos</h3>
                <div style="margin: 15px 0; padding: 15px; background-color: #10b98120; border-radius: 8px;">
                    <strong style="color: #10b981; font-size: 1.2em;">🟢 Dias Positivos</strong><br>
                    <span style="font-size: 1.5em;">{dias_positivos}</span> dias ({dias_positivos/total_dias*100:.1f}%)
                </div>
                <div style="margin: 15px 0; padding: 15px; background-color: #ef444420; border-radius: 8px;">
                    <strong style="color: #ef4444; font-size: 1.2em;">🔴 Dias Negativos</strong><br>
                    <span style="font-size: 1.5em;">{dias_negativos}</span> dias ({dias_negativos/total_dias*100:.1f}%)
                </div>
                <div style="margin: 15px 0; padding: 15px; background-color: #9ca3af20; border-radius: 8px;">
                    <strong style="color: #9ca3af; font-size: 1.2em;">⚪ Dias Neutros</strong><br>
                    <span style="font-size: 1.5em;">{dias_neutros}</span> dias ({dias_neutros/total_dias*100:.1f}%)
                </div>
            </div>
            """, unsafe_allow_html=True)

    # SEÇÃO 4: Gráficos de Linha do Tempo e Volume
    st.markdown("## 📊 Visualizações Complementares")
    
    col1, col2 = st.columns(2)
    
    # Gráfico de preços com eventos marcados
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["Close"], mode="lines", name="Preço", line=dict(color="#3b82f6", width=2)))
        
        # Marcar maior alta e maior queda
        idx_max = df["Close"].idxmax()
        idx_min = df["Close"].idxmin()
        
        fig.add_trace(go.Scatter(
            x=[idx_max], y=[df.loc[idx_max, "Close"]],
            mode="markers+text", name="Maior Alta",
            marker=dict(size=15, color="#10b981", symbol="star"),
            text=["📈 Maior Alta"], textposition="top center",
            textfont=dict(size=10)
        ))
        
        fig.add_trace(go.Scatter(
            x=[idx_min], y=[df.loc[idx_min, "Close"]],
            mode="markers+text", name="Maior Queda",
            marker=dict(size=15, color="#ef4444", symbol="star"),
            text=["📉 Maior Queda"], textposition="bottom center",
            textfont=dict(size=10)
        ))
        
        fig.update_layout(
            title="Histórico com Eventos Marcados",
            xaxis_title="Data",
            yaxis_title="Preço (R$)",
            template="plotly_white",
            height=400,
            hovermode="x unified",
            margin=dict(l=0, r=0, t=40, b=0),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Gráfico de volume
    with col2:
        if "Volume" in df.columns:
            fig_vol = go.Figure()
            cores_volume = ['#10b981' if df.loc[i, 'Close'] >= df.loc[i, 'Open'] else '#ef4444' 
                           for i in df.index]
            
            fig_vol.add_trace(go.Bar(
                x=df.index, 
                y=df["Volume"], 
                name="Volume",
                marker=dict(color=cores_volume)
            ))
            
            fig_vol.update_layout(
                title="Volume de Negociação",
                xaxis_title="Data",
                yaxis_title="Volume",
                template="plotly_white",
                height=400,
                showlegend=False,
                margin=dict(l=0, r=0, t=40, b=0),
            )
            st.plotly_chart(fig_vol, use_container_width=True)

    # SEÇÃO 5: Indicadores Técnicos
    st.markdown("## 🎯 Indicadores Técnicos")
    
    tab1, tab2, tab3 = st.tabs(["📈 RSI", "📊 Bandas de Bollinger", "🔄 MACD"])
    
    with tab1:
        st.markdown("""
        **O que é RSI?** O Índice de Força Relativa mede se uma ação está sobrecomprada (acima de 70) ou sobrevendida (abaixo de 30).
        - **Acima de 70**: Possível sobrecompra (preço pode cair)
        - **Abaixo de 30**: Possível sobrevenda (preço pode subir)
        - **Entre 30-70**: Território neutro
        """)
        
        fig_rsi = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.05, row_heights=[0.7, 0.3])
        
        fig_rsi.add_trace(go.Scatter(x=df.index, y=df['Close'], name='Preço', 
                                     line=dict(color='#3b82f6', width=2)), row=1, col=1)
        
        fig_rsi.add_trace(go.Scatter(x=df.index, y=rsi, name='RSI', 
                                     line=dict(color='#8b5cf6', width=2)), row=2, col=1)
        
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1, 
                         annotation_text="Sobrecompra (70)")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1, 
                         annotation_text="Sobrevenda (30)")
        
        fig_rsi.update_yaxes(title_text="Preço (R$)", row=1, col=1)
        fig_rsi.update_yaxes(title_text="RSI", row=2, col=1)
        fig_rsi.update_xaxes(title_text="Data", row=2, col=1)
        
        fig_rsi.update_layout(height=600, template="plotly_white", hovermode="x unified")
        st.plotly_chart(fig_rsi, use_container_width=True)
        
        # Status atual do RSI
        rsi_atual = rsi.iloc[-1]
        if rsi_atual > 70:
            st.warning(f"⚠️ RSI atual: {rsi_atual:.1f} - Ação pode estar SOBRECOMPRADA")
        elif rsi_atual < 30:
            st.success(f"✅ RSI atual: {rsi_atual:.1f} - Ação pode estar SOBREVENDIDA")
        else:
            st.info(f"ℹ️ RSI atual: {rsi_atual:.1f} - Território neutro")
    
    with tab2:
        st.markdown("""
        **O que são Bandas de Bollinger?** Indicam a volatilidade do preço.
        - **Banda Superior**: Limite superior esperado
        - **Média (centro)**: Preço médio
        - **Banda Inferior**: Limite inferior esperado
        - Quando o preço toca as bandas, pode indicar reversão
        """)
        
        fig_bb = go.Figure()
        
        fig_bb.add_trace(go.Scatter(x=df.index, y=banda_superior, name='Banda Superior',
                                    line=dict(color='#ef4444', width=1, dash='dash')))
        fig_bb.add_trace(go.Scatter(x=df.index, y=sma_bb, name='Média Móvel',
                                    line=dict(color='#3b82f6', width=2)))
        fig_bb.add_trace(go.Scatter(x=df.index, y=banda_inferior, name='Banda Inferior',
                                    line=dict(color='#10b981', width=1, dash='dash')))
        fig_bb.add_trace(go.Scatter(x=df.index, y=df['Close'], name='Preço',
                                    line=dict(color='#000000', width=2)))
        
        fig_bb.update_layout(
            title="Bandas de Bollinger",
            xaxis_title="Data",
            yaxis_title="Preço (R$)",
            template="plotly_white",
            height=500,
            hovermode="x unified"
        )
        st.plotly_chart(fig_bb, use_container_width=True)
        
        # Análise da posição atual
        preco_atual = df['Close'].iloc[-1]
        bb_superior_atual = banda_superior.iloc[-1]
        bb_inferior_atual = banda_inferior.iloc[-1]
        
        if preco_atual >= bb_superior_atual:
            st.warning(f"⚠️ Preço atual (R$ {preco_atual:.2f}) está NA ou ACIMA da banda superior - Possível sobrecompra")
        elif preco_atual <= bb_inferior_atual:
            st.success(f"✅ Preço atual (R$ {preco_atual:.2f}) está NA ou ABAIXO da banda inferior - Possível sobrevenda")
        else:
            st.info(f"ℹ️ Preço atual (R$ {preco_atual:.2f}) está dentro das bandas - Movimento normal")
    
    with tab3:
        st.markdown("""
        **O que é MACD?** Mostra a relação entre duas médias móveis.
        - **Linha MACD acima da Linha de Sinal**: Sinal de compra (tendência de alta)
        - **Linha MACD abaixo da Linha de Sinal**: Sinal de venda (tendência de baixa)
        - **Histograma**: Força da tendência
        """)
        
        fig_macd = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                 vertical_spacing=0.05, row_heights=[0.7, 0.3])
        
        fig_macd.add_trace(go.Scatter(x=df.index, y=df['Close'], name='Preço',
                                      line=dict(color='#3b82f6', width=2)), row=1, col=1)
        
        fig_macd.add_trace(go.Scatter(x=df.index, y=macd, name='MACD',
                                      line=dict(color='#3b82f6', width=2)), row=2, col=1)
        fig_macd.add_trace(go.Scatter(x=df.index, y=linha_sinal, name='Sinal',
                                      line=dict(color='#ef4444', width=2)), row=2, col=1)
        
        cores_hist = ['#10b981' if x >= 0 else '#ef4444' for x in histograma]
        fig_macd.add_trace(go.Bar(x=df.index, y=histograma, name='Histograma',
                                  marker=dict(color=cores_hist)), row=2, col=1)
        
        fig_macd.update_yaxes(title_text="Preço (R$)", row=1, col=1)
        fig_macd.update_yaxes(title_text="MACD", row=2, col=1)
        fig_macd.update_xaxes(title_text="Data", row=2, col=1)
        
        fig_macd.update_layout(height=600, template="plotly_white", hovermode="x unified")
        st.plotly_chart(fig_macd, use_container_width=True)
        
        # Sinal atual
        macd_atual = macd.iloc[-1]
        sinal_atual = linha_sinal.iloc[-1]
        
        if macd_atual > sinal_atual:
            st.success(f"✅ MACD ({macd_atual:.2f}) está ACIMA da linha de sinal ({sinal_atual:.2f}) - Sinal de COMPRA")
        else:
            st.warning(f"⚠️ MACD ({macd_atual:.2f}) está ABAIXO da linha de sinal ({sinal_atual:.2f}) - Sinal de VENDA")

    # SEÇÃO 6: Retornos Diários
    if "returns" in metrics and "returns" in results:
        st.markdown("## 📊 Retornos Diários (Últimos 30 dias)")
        fig_ret = go.Figure()
        fig_ret.add_trace(go.Scatter(
            x=results["returns"].tail(30).index, 
            y=results["returns"].tail(30) * 100,
            mode="lines+markers",
            name="Retorno",
            line=dict(color="#3b82f6", width=2),
            fill="tozeroy"
        ))
        
        fig_ret.update_layout(
            xaxis_title="Data",
            yaxis_title="Retorno (%)",
            template="plotly_white",
            height=300,
            showlegend=False,
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_ret, use_container_width=True)

    # SEÇÃO 7: Tabela de dados
    if show_table:
        st.markdown("## 📋 Dados Brutos")
        st.dataframe(df, use_container_width=True)

    # SEÇÃO 8: Exportação
    st.markdown("## 📥 Exportar Dados")
    csv = df.to_csv(index=True).encode("utf-8")
    st.download_button(
        label="📥 Baixar CSV",
        data=csv,
        file_name=f"{ticker}_cotacoes.csv",
        mime="text/csv",
    )


def main():
    """Função principal da aplicação Streamlit."""
    st.set_page_config(page_title="Análise de Cotações", layout="wide")

    # Tema customizado minimalista
    st.markdown("""
    <style>
        body {
            background-color: #f8f9fa;
        }
        .main {
            background-color: #f8f9fa;
        }
        h1 {
            color: #1f2937;
            margin-bottom: 5px;
        }
        h2 {
            color: #374151;
            margin-top: 20px;
            margin-bottom: 15px;
            border-bottom: 2px solid #3b82f6;
            padding-bottom: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

    # Renderizar página de cotações
    pagina_cotacoes()


if __name__ == "__main__":
    freeze_support()
    main()