
# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from typing import Dict, Any
from config import THRESHOLDS

def calcular_metricas(df_pneus: pd.DataFrame) -> pd.DataFrame:
    df = df_pneus.copy()
    df["Sulco Consumido"] = df["Sulco Inicial"] - df["Aferição - Sulco"]
    df["Desgaste (mm/km)"] = np.where(
        df["Km Rodado até Aferição"].notna() & (df["Km Rodado até Aferição"]>0),
        df["Sulco Consumido"] / df["Km Rodado até Aferição"],
        np.nan
    )
    # Condição e % restante
    df["% Sulco Restante"] = (df["Aferição - Sulco"]/df["Sulco Inicial"]*100).round(1)
    df["Condição"] = pd.cut(
        df["Aferição - Sulco"],
        bins=[-1, THRESHOLDS.critico_mm, THRESHOLDS.alerta_mm, 99],
        labels=["🔴 Crítico","🟡 Alerta","🟢 Ok"]
    )
    # Km restante até limite crítico
    df["Km Restante (estimado)"] = np.where(
        (df["Desgaste (mm/km)"]>0) & df["Desgaste (mm/km)"].notna(),
        ((df["Aferição - Sulco"]-THRESHOLDS.critico_mm)/df["Desgaste (mm/km)"]).round(0),
        np.nan
    )
    return df

def kpis(df_calc: pd.DataFrame) -> Dict[str, Any]:
    total = df_calc["Referência"].nunique() if "Referência" in df_calc.columns else len(df_calc)
    by_cond = df_calc["Condição"].value_counts(dropna=False)
    crit = int(by_cond.get("🔴 Crítico", 0))
    alt  = int(by_cond.get("🟡 Alerta", 0))
    ok   = int(by_cond.get("🟢 Ok", 0))
    estoque = int((df_calc["Status"]=="Estoque").sum()) if "Status" in df_calc.columns else 0
    sucata  = int((df_calc["Status"]=="Sucata").sum()) if "Status" in df_calc.columns else 0
    caminhao= int((df_calc["Status"]=="Caminhão").sum()) if "Status" in df_calc.columns else 0
    pct_crit = round(100*crit/max(total,1),1)
    pct_alt  = round(100*alt/max(total,1),1)
    return dict(total=total, estoque=estoque, sucata=sucata, caminhao=caminhao,
                criticos=crit, alerta=alt, ok=ok, pct_crit=pct_crit, pct_alt=pct_alt)

def estimar_custos(df_calc: pd.DataFrame, custo_pneu: float = 1200.0, custo_parada_hora: float = 300.0) -> Dict[str, float]:
    # Heurística simples para orçamento de troca imediata dos críticos
    crit = df_calc[df_calc["Condição"]=="🔴 Crítico"]
    qtd = len(crit)
    custo_troca = qtd * max(custo_pneu, 0.0)
    # Supor 1h de parada por pneu crítico como proxy
    custo_parada = qtd * max(custo_parada_hora, 0.0)
    return {"qtd_criticos": float(qtd), "custo_troca": float(custo_troca), "custo_parada": float(custo_parada)}
