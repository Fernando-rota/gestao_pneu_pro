
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from etl import read_excel_to_frames, transform_frames
from logic import calcular_metricas, kpis, estimar_custos
from visuals import hist_sulco, box_sulco_por_tipo, barras_condicao, scatter_km_restante, heatmap_posicao
from config import APP_TITLE, COLORS, THRESHOLDS

st.set_page_config(page_title=APP_TITLE, layout="wide")
st.markdown(f"""
<style>
body {{ background-color: {COLORS.cinza_bg}; }}
div[data-testid="metric-container"] {{
    background: white; border: 1px solid #e6e6e6; border-radius: 12px;
    padding: 16px; box-shadow: 0 1px 6px rgba(0,0,0,0.1);
}}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h1 style='text-align:center; color:{COLORS.azul};'>📊 {APP_TITLE}</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align:center; color:gray;'>Visão integrada: Dev + BI + UX/UI</h3>", unsafe_allow_html=True)
st.markdown("---")

with st.sidebar:
    st.header("⚙️ Configurações")
    custo_pneu = st.number_input("Custo unitário do pneu (R$)", min_value=0.0, value=1200.0, step=50.0)
    custo_parada_hora = st.number_input("Custo da hora parada (R$)", min_value=0.0, value=300.0, step=10.0)
    critico = st.number_input("Limite crítico (mm)", min_value=0.5, value=float(THRESHOLDS.critico_mm), step=0.5)
    alerta = st.number_input("Limite alerta (mm)", min_value=critico+0.5, value=float(THRESHOLDS.alerta_mm), step=0.5)
    st.info("Ajuste os limites para ver o impacto nas métricas.")

arquivo = st.file_uploader("📂 Carregue a planilha de pneus (.xlsx)", type=["xlsx","xls"])

@st.cache_data(show_spinner=True)
def load_data(_file):
    sheets = read_excel_to_frames(_file)
    return transform_frames(sheets)

if not arquivo:
    st.info("Aguardando upload do arquivo Excel…")
    st.stop()

try:
    df_pneus, df_posicao, df_sulco = load_data(arquivo)
except Exception as e:
    st.error(str(e))
    st.stop()

# Recalcular métricas (com thresholds da sidebar aplicados apenas visualmente)
df_calc = calcular_metricas(df_pneus)

# =================== FILTROS ===================
st.subheader("🔎 Filtros")
cols = st.columns(5)
def multisel(col, label, series):
    opts = sorted([x for x in series.dropna().unique()])
    return col.multiselect(label, opts, default=[])

status_sel = multisel(cols[0], "Status", df_calc["Status"]) if "Status" in df_calc.columns else []
placa_sel  = multisel(cols[1], "Placa", df_calc["Veículo - Placa"]) if "Veículo - Placa" in df_calc.columns else []
tipo_sel   = multisel(cols[2], "Tipo Veículo", df_calc["Tipo Veículo"])
marca_sel  = multisel(cols[3], "Marca (Atual)", df_calc["Marca (Atual)"]) if "Marca (Atual)" in df_calc.columns else []
vida_sel   = multisel(cols[4], "Vida", df_calc["Vida"]) if "Vida" in df_calc.columns else []

df_show = df_calc.copy()
if status_sel: df_show = df_show[df_show["Status"].isin(status_sel)]
if placa_sel:  df_show = df_show[df_show["Veículo - Placa"].isin(placa_sel)]
if tipo_sel:   df_show = df_show[df_show["Tipo Veículo"].isin(tipo_sel)]
if marca_sel:  df_show = df_show[df_show["Marca (Atual)"].isin(marca_sel)]
if vida_sel:   df_show = df_show[df_show["Vida"].isin(vida_sel)]

# =================== KPIs ===================
m = kpis(df_show)
c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("🛞 Total de Pneus", m["total"])
c2.metric("🔴 Críticos", f'{m["criticos"]} ({m["pct_crit"]}%)')
c3.metric("🟡 Alerta", f'{m["alerta"]} ({m["pct_alt"]}%)')
c4.metric("🟢 Ok", m["ok"])
c5.metric("📦 Estoque", m["estoque"])
c6.metric("♻️ Sucata", m["sucata"])

orc = estimar_custos(df_show, custo_pneu=custo_pneu, custo_parada_hora=custo_parada_hora)
st.info(f'💰 Orçamento imediato: {int(orc["qtd_criticos"])} pneus críticos → '
        f'R$ {orc["custo_troca"]:,.2f} (troca) + R$ {orc["custo_parada"]:,.2f} (parada).')

# =================== ABAS ===================
aba1, aba2, aba3, aba4 = st.tabs(["📈 Indicadores","📏 Medidas de Sulco","🗺️ Posições no Veículo","📝 Conclusão"])

with aba1:
    st.markdown("### 📊 Visão Geral")
    colg1,colg2 = st.columns(2)
    with colg1:
        st.plotly_chart(barras_condicao(df_show), use_container_width=True)
    with colg2:
        st.plotly_chart(hist_sulco(df_show), use_container_width=True)

    st.markdown("### 📦 Eficiência por Tipo de Veículo")
    st.plotly_chart(box_sulco_por_tipo(df_show), use_container_width=True)

    st.markdown("### 🔮 Projeção de Vida (heurística)")
    st.plotly_chart(scatter_km_restante(df_show), use_container_width=True)

with aba2:
    st.subheader("📏 Medidas de Sulco (Detalhado)")
    cols_show = [c for c in ["Referência","Veículo - Placa","Veículo - Descrição","Marca (Atual)","Modelo (Atual)",
                             "Vida","Sulco Inicial","Aferição - Sulco","% Sulco Restante","Condição","Sulco Consumido",
                             "Km Rodado até Aferição","Desgaste (mm/km)","Km Restante (estimado)","Posição","Sigla da Posição","X","Y"]
                 if c in df_show.columns]
    st.dataframe(df_show[cols_show], use_container_width=True)

    risco = df_show[df_show["Condição"].isin(["🔴 Crítico","🟡 Alerta"])]
    st.download_button("📥 Exportar Pneus em Risco (CSV)", risco.to_csv(index=False).encode("utf-8"),
                       "pneus_risco.csv", "text/csv")
    st.download_button("📥 Exportar Tabela Completa (CSV)", df_show[cols_show].to_csv(index=False).encode("utf-8"),
                       "pneus_completo.csv", "text/csv")

with aba3:
    st.subheader("🗺️ Heatmap de Posições")
    st.caption("Exibe a pior condição por posição (se houver sobreposição). Para funcionar, a aba 'posição' deve ter colunas X e Y.")
    st.plotly_chart(heatmap_posicao(df_show), use_container_width=True)

with aba4:
    st.subheader("📝 Conclusão e Insights")
    st.write(f"""
    - 🚨 **{m['criticos']} pneus críticos** (sulco < {THRESHOLDS.critico_mm:.1f} mm) → substituição imediata  
    - ⚠️ **{m['alerta']} pneus em alerta** ({THRESHOLDS.critico_mm:.1f}–{THRESHOLDS.alerta_mm:.1f} mm) → monitorar e planejar troca  
    - 📦 Estoque atual de **{m['estoque']} pneus** disponível para reposição  
    - 💰 Orçamento estimado para críticos: **R$ {orc['custo_troca']:,.2f}** (+ parada **R$ {orc['custo_parada']:,.2f}**)  
    - 🔎 Use os filtros acima para identificar **marcas/modelos** com maior desgaste e **veículos** com risco concentrado.  
    """)
