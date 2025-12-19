from __future__ import annotations

from decimal import Decimal
from typing import Dict, Literal

from pydantic import BaseModel, Field, condecimal


FiatCurrency = Literal["CLP", "PEN", "COP", "BTC", "ETH"]

# Cantidad no negativa, con decimales (ej: 0.5 BTC)
NonNegativeDecimal = condecimal(ge=0)  # type: ignore[valid-type]


class PortfolioRequest(BaseModel):
    portfolio: Dict[str, NonNegativeDecimal] = Field(
        ...,
        description="Mapa de símbolo cripto a cantidad. Ej: {'BTC': 0.5, 'ETH': 2}",
        min_length=1,
    )
    fiat_currency: FiatCurrency = Field(..., description="Moneda fiat de referencia")


class PortfolioValueResponse(BaseModel):
    fiat_currency: FiatCurrency
    total: Decimal = Field(..., description="Valor total del portafolio en la fiat solicitada")
    breakdown: Dict[str, Decimal] = Field(
        ..., description="Detalle por cripto del valor en fiat"
    )
    unpriced: list[str] = Field(
        default_factory=list,
        description="Criptos que no pudieron valorizarse (por falta de mercado, etc.)",
    )