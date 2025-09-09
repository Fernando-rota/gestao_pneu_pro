
# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import re
import unicodedata

from typing import Dict, Tuple
from config import REQUIRED_SHEETS

# ----------------- HELPERS -----------------
def to_float(x):
    if pd.isna(x):
        return np.nan
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    s = str(x).strip()
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except:
        return np.nan

def extrair_km_observacao(texto):
    if pd.isna(texto):
        return np.nan
    m = re.search(r"(\d[\d\.]*)\s*km", str(texto), flags=re.IGNORECASE)
    if not m:
        return np.nan
    s = m.group(1).replace(".", "")
    try:
        return float(s)
    except:
        return np.nan

def normalize_text(s):
    if pd.isna(s):
        return ""
    s = str(s).strip().lower()
    s = " ".join(s.split())
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.upper()

def classificar_veiculo(desc: str) -> str:
    if pd.isna(desc):
        return "Outro"
    d = str(desc).lower()
    # mapa simples (pode evoluir para dicionário externo)
    if "saveiro" in d:
        return "Leve"
    if "renault" in d:
        return "Utilitário (Renault)"
    if any(k in d for k in ["iveco", "daily", "dayli", "scudo"]):
        return "Utilitário (Iveco/Scudo)"
    if any(k in d for k in ["3/4", "3-4"]):
        return "3/4"
    if "toco" in d:
        return "Toco"
    if "truck" in d:
        return "Truck"
    if any(k in d for k in ["cavalo", "carreta"]):
        return "Carreta"
    return "Outro"

# ----------------- ETL -----------------
def read_excel_to_frames(file) -> Dict[str, pd.DataFrame]:
    sheets = pd.read_excel(file, engine="openpyxl", sheet_name=None)
    if not REQUIRED_SHEETS.issubset(set(sheets.keys())):
        raise ValueError(f"O arquivo precisa conter as abas: {', '.join(sorted(REQUIRED_SHEETS))}.")
    for k, df in sheets.items():
        sheets[k] = df.copy()
        sheets[k].columns = sheets[k].columns.str.strip()
    return sheets

def transform_frames(sheets: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df_pneus = sheets["pneus"].copy()
    df_posicao = sheets["posição"].copy()
    df_sulco = sheets["sulco"].copy()

    renames = {"Modelo": "Modelo (Atual)", "SULCO": "Sulco",
               "Sigla": "Sigla da Posição", "SIGLA": "Sigla da Posição",
               "POSIÇÃO": "Posição"}
    df_pneus = df_pneus.rename(columns=renames)
    df_posicao = df_posicao.rename(columns=renames)
    df_sulco = df_sulco.rename(columns=renames)

    # Normalizações numéricas
    if "Aferição - Sulco" in df_pneus.columns:
        df_pneus["Aferição - Sulco"] = df_pneus["Aferição - Sulco"].apply(to_float)
    if "Sulco" in df_sulco.columns:
        df_sulco["Sulco"] = df_sulco["Sulco"].apply(to_float)

    if "Hodômetro Inicial" in df_pneus.columns:
        df_pneus["Hodômetro Inicial"] = df_pneus["Hodômetro Inicial"].apply(to_float)
    if "Vida do Pneu - Km. Rodado" in df_pneus.columns:
        df_pneus["Vida do Pneu - Km. Rodado"] = df_pneus["Vida do Pneu - Km. Rodado"].apply(to_float)
    else:
        df_pneus["Vida do Pneu - Km. Rodado"] = np.nan

    if "Observação" in df_pneus.columns:
        df_pneus["Observação - Km"] = df_pneus["Observação"].apply(extrair_km_observacao)
    else:
        df_pneus["Observação - Km"] = np.nan

    # Km rodado até aferição
    df_pneus["Km Rodado até Aferição"] = df_pneus["Vida do Pneu - Km. Rodado"]
    mask_km_vazio = df_pneus["Km Rodado até Aferição"].isna() | (df_pneus["Km Rodado até Aferição"] <= 0)
    if "Observação - Km" in df_pneus.columns and "Hodômetro Inicial" in df_pneus.columns:
        df_pneus.loc[mask_km_vazio, "Km Rodado até Aferição"] = (
            df_pneus.loc[mask_km_vazio, "Observação - Km"] - df_pneus.loc[mask_km_vazio, "Hodômetro Inicial"]
        )
    df_pneus.loc[df_pneus["Km Rodado até Aferição"] <= 0, "Km Rodado até Aferição"] = np.nan

    # Mapa posição
    if "Sigla da Posição" in df_pneus.columns and "Sigla da Posição" in df_posicao.columns:
        df_pneus = df_pneus.merge(df_posicao, on="Sigla da Posição", how="left")

    # Sulco inicial por (vida, modelo)
    for df in (df_pneus, df_sulco):
        if "Vida" in df.columns:
            df["_VIDA"] = df["Vida"].apply(normalize_text)
        if "Modelo (Atual)" in df.columns:
            df["_MODELO"] = df["Modelo (Atual)"].apply(normalize_text)

    base = (
        df_sulco[["_VIDA","_MODELO","Sulco"]]
        .dropna(subset=["Sulco"])
        .drop_duplicates(subset=["_VIDA","_MODELO"])
    )
    df_pneus = df_pneus.merge(base.rename(columns={"Sulco":"Sulco Inicial"}),
                              on=["_VIDA","_MODELO"], how="left")

    # Preenchimento do sulco inicial com diferentes estratégias
    map_model_novo = (
        df_sulco[df_sulco["_VIDA"]=="NOVO"]
        .dropna(subset=["Sulco"])
        .drop_duplicates("_MODELO")
        .set_index("_MODELO")["Sulco"].to_dict()
    )
    mask = df_pneus["Sulco Inicial"].isna() & (df_pneus["_VIDA"]=="NOVO")
    df_pneus.loc[mask, "Sulco Inicial"] = df_pneus.loc[mask, "_MODELO"].map(map_model_novo)

    map_model_any = df_sulco.dropna(subset=["Sulco"]).groupby("_MODELO")["Sulco"].median().to_dict()
    df_pneus.loc[df_pneus["Sulco Inicial"].isna(), "Sulco Inicial"] = (
        df_pneus.loc[df_pneus["Sulco Inicial"].isna(), "_MODELO"].map(map_model_any)
    )

    mediana_por_vida = df_sulco.dropna(subset=["Sulco"]).groupby("_VIDA")["Sulco"].median()
    df_pneus.loc[df_pneus["Sulco Inicial"].isna(), "Sulco Inicial"] = (
        df_pneus.loc[df_pneus["Sulco Inicial"].isna(), "_VIDA"].map(mediana_por_vida)
    )
    if df_sulco["Sulco"].dropna().shape[0]:
        df_pneus["Sulco Inicial"] = df_pneus["Sulco Inicial"].fillna(df_sulco["Sulco"].dropna().median())

    # Tipificação
    if "Veículo - Descrição" in df_pneus.columns:
        df_pneus["Tipo Veículo"] = df_pneus["Veículo - Descrição"].apply(classificar_veiculo)
    else:
        df_pneus["Tipo Veículo"] = "Outro"

    return df_pneus, df_posicao, df_sulco
