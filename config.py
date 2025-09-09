
# -*- coding: utf-8 -*-
from dataclasses import dataclass

@dataclass(frozen=True)
class Thresholds:
    critico_mm: float = 2.0
    alerta_mm: float = 4.0

@dataclass(frozen=True)
class Colors:
    ok: str = "#6BCB77"
    alerta: str = "#FFD93D"
    critico: str = "#FF6B6B"
    neutro: str = "#e6e6e6"
    azul: str = "#1E88E5"
    cinza_bg: str = "#f9f9f9"

THRESHOLDS = Thresholds()
COLORS = Colors()

APP_TITLE = "Gestão de Pneus"
REQUIRED_SHEETS = {"pneus", "posição", "sulco"}
