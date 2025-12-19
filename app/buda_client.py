from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional

import httpx

from app.settings import settings


class BudaUpstreamError(RuntimeError):
    """Error genérico al consumir la API pública de Buda."""


@dataclass(frozen=True)
class Ticker:
    market_id: str          # e.g. "BTC-CLP"
    base: str               # e.g. "BTC"
    quote: str              # e.g. "CLP"
    last_price: Decimal     # precio último


def _parse_decimal(value: object, field_name: str) -> Decimal:
    # Buda suele devolver precios como strings dentro de arrays (ej: ["123.4", "CLP"])
    if not isinstance(value, str):
        raise BudaUpstreamError(f"Invalid '{field_name}' type from Buda: expected str")
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise BudaUpstreamError(f"Invalid '{field_name}' value from Buda: {value}") from exc


def _split_market_id(market_id: str) -> tuple[str, str]:
    if "-" not in market_id:
        raise BudaUpstreamError(f"Invalid market_id format from Buda: {market_id}")
    base, quote = market_id.split("-", 1)
    return base.upper(), quote.upper()


class BudaPublicClient:
    def __init__(self, base_url: str | None = None, timeout_seconds: float | None = None):
        self.base_url = base_url or settings.buda_base_url
        self.timeout = timeout_seconds or settings.buda_timeout_seconds

    def get_tickers(self) -> Dict[str, Ticker]:
        """
        Retorna tickers indexados por market_id.
        Usa /api/v2/tickers (una sola llamada para todos los mercados).
        """
        url = f"{self.base_url}/api/v2/tickers"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.TimeoutException,) as exc:
            raise BudaUpstreamError("Timeout calling Buda public API") from exc
        except (httpx.HTTPStatusError,) as exc:
            raise BudaUpstreamError(f"Buda public API returned {exc.response.status_code}") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise BudaUpstreamError("Failed to call/parse Buda public API response") from exc

        tickers_raw = data.get("tickers")
        if not isinstance(tickers_raw, list):
            raise BudaUpstreamError("Unexpected Buda response: 'tickers' is not a list")

        out: Dict[str, Ticker] = {}
        for item in tickers_raw:
            if not isinstance(item, dict):
                continue

            market_id = item.get("market_id")
            if not isinstance(market_id, str):
                continue

            # last_price viene como array ["<price>", "<currency>"]
            last_price = item.get("last_price")
            if not (isinstance(last_price, list) and len(last_price) >= 1):
                continue

            base, quote = _split_market_id(market_id)
            price = _parse_decimal(last_price[0], "last_price")

            out[market_id.upper()] = Ticker(
                market_id=market_id.upper(),
                base=base,
                quote=quote,
                last_price=price,
            )

        return out
