import streamlit as st
from data_loader import fetch_data
from mapreduce_utils import map_reduce_stats
import pandas as pd
import plotly.graph_objects as go
from multiprocessing import freeze_support

# Necessário para multiprocessing no Windows
def main():
    """Função principal da aplicação Streamlit."""
    st.set_page_config(page_title="Cotacoes Insight", layout="wide")

    st.title("📈 Cotacoes Insight")
    st.markdown("Aplicação para análise de cotações usando MapReduce")

    # Sidebar
    with st.sidebar:
        st.header("🔎 Controle")
        ticker = st.text_input("Ticker (ex: AAPL, PETR4.SA)", value="AAPL")
        period = st.selectbox("Período", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)
        interval = st.selectbox("Intervalo", ["1d", "1wk", "1h"], index=0)
        show_table = st.checkbox("Mostrar tabela de dados", value=False)
        metrics = st.multiselect(
            "Métricas a calcular",
            ["mean", "min", "max", "std", "returns", "moving_average", "volatility", "cumulative_return", "max_drawdown"],
            default=["mean", "min", "max", "returns", "volatility", "cumulative_return"],
        )
        days_ma = st.number_input("Janela (dias) para média móvel", min_value=2, max_value=200, value=10)

        if st.button("🔁 Atualizar dados"):
            st.session_state["reload"] = True

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

    # --- Caso não hover ---
    if df is None or df.empty:
        st.error(
            f"❌ Não foi possível carregar dados para o ticker '{ticker}' com o período '{period}' e intervalo '{interval}'.\n\n"
            "📌 Dicas:\n"
            "- Verifique se o ticker está correto (para ações brasileiras use sufixo `.SA`, ex: PETR4.SA).\n"
            "- Tente outro período ou intervalo.\n"
            "- Pode haver instabilidade temporária na API do Yahoo Finance."
        )
        st.stop()

    # Processar com MapReduce
    with st.spinner("Processando (MapReduce)..."):
        results = map_reduce_stats(df.copy(), metrics=metrics, moving_average_days=int(days_ma))

    # Layout
    col1, col2 = st.columns([2, 1])

    # --- COLUNA PRINCIPAL ---
    with col1:
        st.subheader(f"📊 Gráfico de preços — {ticker}")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["Close"], mode="lines", name="Fechamento"))

        # Média móvel
        if "moving_average" in metrics and f"ma_{days_ma}" in results:
            fig.add_trace(
                go.Scatter(x=df.index, y=results[f"ma_{days_ma}"], mode="lines", name=f"Média móvel {days_ma}d")
            )

        fig.update_layout(
            xaxis_title="Data",
            yaxis_title="Preço",
            template="plotly_white",
            height=450,
            showlegend=True,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Retornos
        if "returns" in metrics and "returns" in results:
            st.subheader("📈 Retornos Diários (últimos 30 dias)")
            st.line_chart(results["returns"].tail(30))

        # Botão de exportação
        csv = df.to_csv(index=True).encode("utf-8")
        st.download_button(
            label="💾 Exportar dados em CSV",
            data=csv,
            file_name=f"{ticker}_cotacoes.csv",
            mime="text/csv",
        )

    # --- COLUNA SECUNDÁRIA ---
    with col2:
        st.subheader("📋 Indicadores")
        for k, v in results.items():
            if isinstance(v, (int, float)):
                st.metric(label=k, value=round(v, 4))

    # Tabela de dados
    if show_table:
        st.subheader("📄 Tabela de Dados")
        st.dataframe(df)


if __name__ == "__main__":
    freeze_support()  # Necessário para multiprocessing no Windows
    main()
