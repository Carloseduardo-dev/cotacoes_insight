import streamlit as st
from data_loader import fetch_data
from mapreduce_utils import map_reduce_stats
import pandas as pd
import plotly.graph_objects as go
from multiprocessing import freeze_support
from datetime import datetime, timedelta
import calendar


def pagina_cotacoes():
    """Página de análise de cotações."""
    st.title("📊 Análise de Cotações")
    st.markdown("Análise simples e rápida de ações")

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
    
    # Seção de busca centralizada na tela principal
    st.markdown("## 🔍 Buscar Ação")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        ticker_nome = st.selectbox("Selecione a ação", list(tickers_disponiveis.keys()), label_visibility="visible", key="ticker_select")
        ticker = tickers_disponiveis[ticker_nome]
    with col2:
        period = st.selectbox("Período", ["1mo", "3mo", "6mo", "1y", "2y"], index=2, label_visibility="visible", key="period_select")
    with col3:
        interval = st.selectbox("Intervalo", ["1d", "1wk", "1h"], index=0, label_visibility="visible", key="interval_select")
    
    st.divider()
    
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
            "Máximo Drawdown": "max_drawdown"
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
        if st.button("🔍 Buscar", use_container_width=True, key="search_button"):
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

    # SEÇÃO 1: Informações Principais
    st.markdown(f"## {ticker_nome} ({ticker}) • {period} • {interval}")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if "mean" in results:
            st.metric(label="Preço Médio", value=f"${results['mean']:.2f}")
    
    with col2:
        if "min" in results:
            st.metric(label="Preço Mínimo", value=f"${results['min']:.2f}")
    
    with col3:
        if "max" in results:
            st.metric(label="Preço Máximo", value=f"${results['max']:.2f}")
    
    with col4:
        if "volatility" in results:
            vol = results["volatility"] * 100
            st.metric(label="Volatilidade", value=f"{vol:.1f}%")
    
    with col5:
        if "cumulative_return" in results:
            ret = results["cumulative_return"] * 100
            st.metric(label="Retorno Acum.", value=f"{ret:.1f}%", delta=f"{ret:+.1f}%" if ret != 0 else None)

    # SEÇÃO 2: Gráficos
    st.markdown("## 📈 Visualizações")
    
    col1, col2 = st.columns(2)
    
    # Gráfico de preços
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["Close"], mode="lines", name="Preço", line=dict(color="#3b82f6", width=2)))
        
        if "moving_average" in metrics and f"ma_{days_ma}" in results:
            fig.add_trace(
                go.Scatter(x=df.index, y=results[f"ma_{days_ma}"], mode="lines", 
                          name=f"Média {days_ma}d", line=dict(color="#ef4444", width=2, dash="dash"))
            )
        
        fig.update_layout(
            title="Histórico de Preços",
            xaxis_title="Data",
            yaxis_title="Preço (USD)",
            template="plotly_white",
            height=400,
            hovermode="x unified",
            margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Gráfico de volume
    with col2:
        if "Volume" in df.columns:
            fig_vol = go.Figure()
            fig_vol.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume", marker=dict(color="#10b981")))
            
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

    # SEÇÃO 3: Retornos Diários
    if "returns" in metrics and "returns" in results:
        st.markdown("## 📊 Retornos Diários")
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
            margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig_ret, use_container_width=True)

    # SEÇÃO 4: Tabela de dados
    if show_table:
        st.markdown("## 📋 Dados Brutos")
        st.dataframe(df, use_container_width=True)

    # SEÇÃO 5: Exportação
    st.markdown("## 📥 Exportar Dados")
    csv = df.to_csv(index=True).encode("utf-8")
    st.download_button(
        label="📥 Baixar CSV",
        data=csv,
        file_name=f"{ticker}_cotacoes.csv",
        mime="text/csv",
    )


def pagina_financeiro():
    """Página de controle financeiro com visualização em calendário."""
    st.title("💰 Meu Financeiro")
    st.markdown("Controle suas transações e acompanhe seu patrimônio")

    # Inicializar session state para notas
    if "notas_financeiras" not in st.session_state:
        st.session_state.notas_financeiras = []

    # Saldo Total - Grande e Centralizado
    st.markdown("---")
    col_saldo = st.columns([1, 3, 1])
    with col_saldo[1]:
        total = sum([nota["valor"] if nota["tipo"] == "Ganho" else -nota["valor"] for nota in st.session_state.notas_financeiras])
        cor_saldo = "#10b981" if total >= 0 else "#ef4444"
        st.markdown(f"""
        <div style="text-align: center; padding: 30px; background-color: {cor_saldo}20; border-radius: 10px; margin: 20px 0; border: 2px solid {cor_saldo};">
            <h2 style="color: #666; margin: 0;">Saldo Total</h2>
            <h1 style="color: {cor_saldo}; margin: 10px 0; font-size: 3.5em;">R$ {total:,.2f}</h1>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("---")

    # Botão de adicionar transação e controles
    col1, col2, col3 = st.columns([2, 1, 1])
    with col2:
        if st.button("➕ Nova Transação", use_container_width=True, key="btn_nova_transacao"):
            st.session_state.show_modal = True
    
    with col3:
        visualizacao = st.selectbox("Visualização", ["Mês", "Semana", "Lista"], label_visibility="collapsed")

    st.divider()

    # Modal para adicionar transação
    if st.session_state.get("show_modal", False):
        st.markdown("## 📝 Nova Transação")
        
        with st.form("form_transacao"):
            descricao = st.text_input("Descrição", placeholder="Ex: Venda de AAPL, Dividendo recebido...")
            
            col1, col2 = st.columns(2)
            with col1:
                tipo = st.selectbox("Tipo", ["Ganho", "Perda"])
            with col2:
                valor = st.number_input("Valor (R$)", min_value=0.01, step=0.01)
            
            data = st.date_input("Data", value=datetime.now())
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("✅ Salvar", use_container_width=True):
                    st.session_state.notas_financeiras.append({
                        "descricao": descricao,
                        "tipo": tipo,
                        "valor": valor,
                        "data": data
                    })
                    st.session_state.show_modal = False
                    st.rerun()
            
            with col2:
                if st.form_submit_button("❌ Cancelar", use_container_width=True):
                    st.session_state.show_modal = False
                    st.rerun()
        
        st.divider()

    # Visualização em Calendário (Mês)
    if visualizacao == "Mês":
        if st.session_state.notas_financeiras:
            df_transacoes = pd.DataFrame(st.session_state.notas_financeiras)
            df_transacoes["data"] = pd.to_datetime(df_transacoes["data"])
            
            # Seletores de mês e ano
            col1, col2 = st.columns(2)
            with col1:
                mes_selecionado = st.selectbox("Mês", range(1, 13), index=datetime.now().month - 1, key="mes_cal")
            with col2:
                ano_selecionado = st.number_input("Ano", value=datetime.now().year, min_value=2020, key="ano_cal")
            
            # Criar calendário visual
            st.markdown(f"### 📅 Calendário")
            
            # Gerar calendário
            cal = calendar.monthcalendar(ano_selecionado, mes_selecionado)
            meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
            dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
            
            # Header do calendário
            st.markdown(f"<h4 style='text-align: center;'>{meses[mes_selecionado-1]} de {ano_selecionado}</h4>", unsafe_allow_html=True)
            
            # Dias da semana (header)
            cols = st.columns(7)
            for i, dia in enumerate(dias_semana):
                with cols[i]:
                    st.markdown(f"<p style='text-align: center; font-weight: bold; color: #3b82f6; font-size: 12px;'>{dia[:3].upper()}</p>", unsafe_allow_html=True)
            
            # Dias do mês
            for semana in cal:
                cols = st.columns(7)
                for i, dia in enumerate(semana):
                    with cols[i]:
                        if dia == 0:
                            st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)
                        else:
                            # Verificar se há transações neste dia
                            data_atual = datetime(ano_selecionado, mes_selecionado, dia).date()
                            transacoes_dia = df_transacoes[df_transacoes["data"].dt.date == data_atual]
                            
                            if len(transacoes_dia) > 0:
                                total_dia = sum([t["valor"] if t["tipo"] == "Ganho" else -t["valor"] 
                                               for _, t in transacoes_dia.iterrows()])
                                cor = "#10b981" if total_dia >= 0 else "#ef4444"
                                
                                # Card do dia com transações
                                transacoes_html = ""
                                for _, t in transacoes_dia.iterrows():
                                    emoji = "🟢" if t["tipo"] == "Ganho" else "🔴"
                                    transacoes_html += f"{emoji} {t['descricao'][:15]}... R${t['valor']:.0f}<br>"
                                
                                st.markdown(f"""
                                <div style="background-color: {cor}20; border: 2px solid {cor}; border-radius: 6px; padding: 8px; min-height: 100px; font-size: 10px; overflow: hidden;">
                                    <strong style="color: {cor}; font-size: 14px;">{dia}</strong><br>
                                    <span style="font-size: 9px;">{transacoes_html}</span>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                # Card vazio
                                st.markdown(f"""
                                <div style="background-color: #f5f5f5; border: 1px solid #ddd; border-radius: 6px; padding: 8px; min-height: 100px; text-align: center; color: #999; display: flex; align-items: center; justify-content: center;">
                                    <strong style="font-size: 18px;">{dia}</strong>
                                </div>
                                """, unsafe_allow_html=True)
            
            st.divider()
            
            # Filtrar transações do mês
            df_mes = df_transacoes[(df_transacoes["data"].dt.month == mes_selecionado) & 
                                   (df_transacoes["data"].dt.year == ano_selecionado)]
            
            st.markdown(f"### 📋 Detalhes das Transações")
            
            if not df_mes.empty:
                for _, row in df_mes.sort_values("data").iterrows():
                    cor = "#10b98140" if row["tipo"] == "Ganho" else "#ef444440"
                    emoji = "🟢" if row["tipo"] == "Ganho" else "🔴"
                    
                    st.markdown(f"""
                    <div style="background-color: {cor}; padding: 12px; border-radius: 6px; margin: 8px 0; border-left: 4px solid {'#10b981' if row['tipo'] == 'Ganho' else '#ef4444'};">
                        <strong>{row['descricao']}</strong> • {row['data'].strftime('%d/%m/%Y')}<br>
                        {emoji} <strong>R$ {row['valor']:.2f}</strong>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Nenhuma transação neste mês")
        else:
            st.info("Nenhuma transação registrada. Clique em 'Nova Transação' para começar!")
    
    # Visualização em Lista
    elif visualizacao == "Lista":
        if st.session_state.notas_financeiras:
            df_transacoes = pd.DataFrame(st.session_state.notas_financeiras)
            df_transacoes["data"] = pd.to_datetime(df_transacoes["data"])
            df_transacoes = df_transacoes.sort_values("data", ascending=False)
            
            st.markdown("### 📋 Histórico de Transações")
            
            for _, row in df_transacoes.iterrows():
                cor = "#10b98140" if row["tipo"] == "Ganho" else "#ef444440"
                emoji = "🟢" if row["tipo"] == "Ganho" else "🔴"
                
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                with col1:
                    st.write(f"**{row['descricao']}**")
                with col2:
                    st.write(f"{emoji} {row['tipo']}")
                with col3:
                    st.write(f"R$ {row['valor']:.2f}")
                with col4:
                    st.write(row['data'].strftime('%d/%m/%Y'))
                st.divider()
        else:
            st.info("Nenhuma transação registrada")
    
    # Visualização em Semana
    elif visualizacao == "Semana":
        if st.session_state.notas_financeiras:
            df_transacoes = pd.DataFrame(st.session_state.notas_financeiras)
            df_transacoes["data"] = pd.to_datetime(df_transacoes["data"])
            
            data_inicio = st.date_input("Início da semana", value=datetime.now(), key="data_semana")
            data_fim = pd.Timestamp(data_inicio) + pd.Timedelta(days=6)
            
            df_semana = df_transacoes[(df_transacoes["data"].dt.date >= data_inicio) & 
                                      (df_transacoes["data"].dt.date <= data_fim.date())]
            
            st.markdown(f"### Semana de {data_inicio.strftime('%d/%m')} a {data_fim.strftime('%d/%m/%Y')}")
            
            if not df_semana.empty:
                for _, row in df_semana.sort_values("data").iterrows():
                    cor = "#10b98140" if row["tipo"] == "Ganho" else "#ef444440"
                    emoji = "🟢" if row["tipo"] == "Ganho" else "🔴"
                    
                    st.markdown(f"""
                    <div style="background-color: {cor}; padding: 12px; border-radius: 6px; margin: 8px 0; border-left: 4px solid {'#10b981' if row['tipo'] == 'Ganho' else '#ef4444'};">
                        <strong>{row['data'].strftime('%A, %d de %B')}</strong><br>
                        {row['descricao']} • {emoji} <strong>R$ {row['valor']:.2f}</strong>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Nenhuma transação nesta semana")
        else:
            st.info("Nenhuma transação registrada")


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

    # Sidebar com navegação
    with st.sidebar:
        st.markdown("# 📱 Menu")
        st.divider()
        
        pagina = st.radio(
            "Selecione a página",
            ["📊 Cotações", "💰 Meu Financeiro"],
            label_visibility="collapsed"
        )

    # Renderizar página selecionada
    if pagina == "📊 Cotações":
        pagina_cotacoes()
    elif pagina == "💰 Meu Financeiro":
        pagina_financeiro()


if __name__ == "__main__":
    freeze_support()
    main()