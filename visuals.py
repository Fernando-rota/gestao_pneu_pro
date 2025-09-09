
# -*- coding: utf-8 -*-
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional
from config import COLORS, THRESHOLDS

def hist_sulco(df: pd.DataFrame):
    return px.histogram(df, x="Aferição - Sulco", nbins=20, color="Tipo Veículo", title="Distribuição de Sulco")

def box_sulco_por_tipo(df: pd.DataFrame):
    return px.box(df, x="Tipo Veículo", y="Aferição - Sulco", title="Sulco por Tipo de Veículo")

def barras_condicao(df: pd.DataFrame):
    order = ["🔴 Crítico","🟡 Alerta","🟢 Ok"]
    c = df["Condição"].value_counts().reindex(order).fillna(0).astype(int).reset_index()
    c.columns = ["Condição","Quantidade"]
    fig = px.bar(c, x="Condição", y="Quantidade", title="Pneus por Condição", text="Quantidade")
    fig.update_traces(textposition="outside")
    return fig

def scatter_km_restante(df: pd.DataFrame):
    if "Km Restante (estimado)" not in df.columns: return go.Figure()
    return px.scatter(
        df,
        x="Km Rodado até Aferição",
        y="Km Restante (estimado)",
        color="Condição",
        hover_data=[c for c in ["Referência","Veículo - Placa","Modelo (Atual)","Vida"] if c in df.columns],
        title="Km Restante (estimado) vs Km já Rodado"
    )

def heatmap_posicao(df: pd.DataFrame, x_col: str = "X", y_col: str = "Y", label_col: str = "Sigla da Posição"):
    # Requer que df contenha colunas (x_col, y_col) vindas da aba 'posição' (merge realizado no ETL)
    if not set([x_col, y_col, label_col]).issubset(df.columns):
        return go.Figure()
    # Definir cor por condição
    color_map = {"🔴 Crítico": COLORS.critico, "🟡 Alerta": COLORS.alerta, "🟢 Ok": COLORS.ok}
    df_plot = df.copy()
    df_plot["Cor"] = df_plot["Condição"].map(color_map).fillna(COLORS.neutro)
    # Agregar por posição (pegar pior condição da posição)
    ordem = {"🔴 Crítico": 0, "🟡 Alerta": 1, "🟢 Ok": 2}
    df_plot["ordem"] = df_plot["Condição"].map(ordem).fillna(3)
    pos = df_plot.sort_values("ordem").drop_duplicates(label_col)  # pior primeiro
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pos[x_col], y=pos[y_col],
        mode="markers+text",
        marker=dict(size=40, color=pos["Cor"], line=dict(color="#444", width=1)),
        text=pos[label_col],
        textposition="middle center",
        hovertext=[f"{r[label_col]} — {r.get('Condição','?')}" for _, r in pos.iterrows()],
        hoverinfo="text"
    ))
    fig.update_layout(
        title="Mapa de Posições do Veículo (pior condição por posição)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        height=400, margin=dict(l=10,r=10,t=50,b=10)
    )
    return fig
