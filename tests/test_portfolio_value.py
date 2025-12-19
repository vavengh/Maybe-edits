from decimal import Decimal

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response

from app.main import app

client = TestClient(app)


# ----------------------------
# Helpers
# ----------------------------
def buda_tickers_payload(tickers: list[dict]) -> dict:
    return {"tickers": tickers}


def mock_buda_tickers(tickers: list[dict]):
    """
    Helper: mockea el endpoint /api/v2/tickers de Buda con una lista de tickers controlada.
    """
    return respx.get("https://www.buda.com/api/v2/tickers").mock(
        return_value=Response(200, json=buda_tickers_payload(tickers))
    )


# ============================================================
# SECTION 1: Valuaciones válidas (sin hops / con hops / portafolios simples y múltiples)
# ============================================================

# -----
# Sin hops (conversión directa)
# -----

@respx.mock
def test_direct_conversion_single_asset_btc_to_clp():
    # Evalúa: Conversión directa BTC -> CLP
    mock_buda_tickers([
        {"market_id": "BTC-CLP", "last_price": ["80000000", "CLP"]},
    ])

    resp = client.post("/portfolio/value", json={"portfolio": {"BTC": 0.5}, "fiat_currency": "CLP"})
    assert resp.status_code == 200
    data = resp.json()

    assert Decimal(data["total"]) == Decimal("40000000")
    assert Decimal(data["breakdown"]["BTC"]) == Decimal("40000000")
    assert data["unpriced"] == []


@respx.mock
def test_direct_conversion_single_asset_usdt_to_clp():
    # Evalúa: Conversión directa USDT -> CLP
    mock_buda_tickers([
        {"market_id": "USDT-CLP", "last_price": ["912.01", "CLP"]},
    ])

    resp = client.post("/portfolio/value", json={"portfolio": {"USDT": 1000}, "fiat_currency": "CLP"})
    assert resp.status_code == 200
    data = resp.json()

    assert Decimal(data["total"]) == Decimal("912010")
    assert Decimal(data["breakdown"]["USDT"]) == Decimal("912010")
    assert data["unpriced"] == []


# -----
# Portafolio múltiple (varios activos directos)
# -----

@respx.mock
def test_multi_asset_direct_conversion_btc_and_eth_to_clp():
    # Evalúa: Portafolio múltiple con mercados directos (BTC, ETH -> CLP)
    mock_buda_tickers([
        {"market_id": "BTC-CLP", "last_price": ["80000000", "CLP"]},
        {"market_id": "ETH-CLP", "last_price": ["2700000", "CLP"]},
    ])

    resp = client.post("/portfolio/value", json={"portfolio": {"BTC": 0.5, "ETH": 2}, "fiat_currency": "CLP"})
    assert resp.status_code == 200
    data = resp.json()

    # BTC: 0.5 * 80,000,000 = 40,000,000
    # ETH: 2 * 2,700,000 = 5,400,000
    assert Decimal(data["total"]) == Decimal("45400000")
    assert Decimal(data["breakdown"]["BTC"]) == Decimal("40000000")
    assert Decimal(data["breakdown"]["ETH"]) == Decimal("5400000")
    assert data["unpriced"] == []


@respx.mock
def test_multi_asset_direct_conversion_usdc_and_usdt_to_pen():
    # Evalúa: Portafolio múltiple con mercados directos (USDC, USDT -> PEN)
    mock_buda_tickers([
        {"market_id": "USDC-PEN", "last_price": ["3.3644", "PEN"]},
        {"market_id": "USDT-PEN", "last_price": ["3.3401", "PEN"]},
    ])

    resp = client.post("/portfolio/value", json={"portfolio": {"USDC": 100, "USDT": 50}, "fiat_currency": "PEN"})
    assert resp.status_code == 200
    data = resp.json()

    # USDC: 100 * 3.3644 = 336.44
    # USDT: 50 * 3.3401 = 167.005
    assert Decimal(data["total"]) == Decimal("503.445")
    assert Decimal(data["breakdown"]["USDC"]) == Decimal("336.44")
    assert Decimal(data["breakdown"]["USDT"]) == Decimal("167.005")
    assert data["unpriced"] == []


# -----
# Con hops (2 saltos máximo)
# -----

@respx.mock
def test_two_hops_eth_to_clp_via_btc():
    # Evalúa: 2 hops ETH -> BTC -> CLP
    mock_buda_tickers([
        {"market_id": "ETH-BTC", "last_price": ["0.033", "BTC"]},
        {"market_id": "BTC-CLP", "last_price": ["80000000", "CLP"]},
    ])

    resp = client.post("/portfolio/value", json={"portfolio": {"ETH": 2}, "fiat_currency": "CLP"})
    assert resp.status_code == 200
    data = resp.json()

    # 1 ETH = 0.033 BTC; 1 BTC = 80,000,000 CLP
    # 1 ETH = 2,640,000 CLP; 2 ETH = 5,280,000
    assert Decimal(data["total"]) == Decimal("5280000")
    assert Decimal(data["breakdown"]["ETH"]) == Decimal("5280000")
    assert data["unpriced"] == []


@respx.mock
def test_two_hops_usdt_to_clp_via_usdc():
    # Evalúa: 2 hops USDT -> USDC -> CLP (sin mercado directo USDT-CLP)
    mock_buda_tickers([
        {"market_id": "USDT-USDC", "last_price": ["0.9991", "USDC"]},
        {"market_id": "USDC-CLP", "last_price": ["916.45", "CLP"]},
    ])

    resp = client.post("/portfolio/value", json={"portfolio": {"USDT": 1000}, "fiat_currency": "CLP"})
    assert resp.status_code == 200
    data = resp.json()

    # 1000 USDT -> 999.1 USDC -> 999.1 * 916.45 CLP
    expected = Decimal("1000") * Decimal("0.9991") * Decimal("916.45")
    assert Decimal(data["total"]) == expected
    assert Decimal(data["breakdown"]["USDT"]) == expected
    assert data["unpriced"] == []


# -----
# Normalización de símbolos (mayúsculas/minúsculas)
# -----

@respx.mock
def test_symbol_case_insensitive_btc_lowercase_key():
    # Evalúa: El símbolo "btc" (minúsculas) se normaliza y funciona
    mock_buda_tickers([
        {"market_id": "BTC-CLP", "last_price": ["80000000", "CLP"]},
    ])

    resp = client.post("/portfolio/value", json={"portfolio": {"btc": 1}, "fiat_currency": "CLP"})
    assert resp.status_code == 200
    data = resp.json()

    assert Decimal(data["total"]) == Decimal("80000000")
    # OJO: breakdown usa la key normalizada (BTC) porque nosotros hacemos sym = symbol.upper()
    assert Decimal(data["breakdown"]["BTC"]) == Decimal("80000000")
    assert data["unpriced"] == []


@respx.mock
def test_symbol_case_insensitive_mixed_keys():
    # Evalúa: Mezcla de símbolos en minúscula/mayúscula en portafolio múltiple
    mock_buda_tickers([
        {"market_id": "BTC-CLP", "last_price": ["80000000", "CLP"]},
        {"market_id": "ETH-CLP", "last_price": ["2700000", "CLP"]},
    ])

    resp = client.post("/portfolio/value", json={"portfolio": {"btc": 0.5, "ETH": 2}, "fiat_currency": "CLP"})
    assert resp.status_code == 200
    data = resp.json()

    assert Decimal(data["total"]) == Decimal("45400000")
    assert Decimal(data["breakdown"]["BTC"]) == Decimal("40000000")
    assert Decimal(data["breakdown"]["ETH"]) == Decimal("5400000")
    assert data["unpriced"] == []


# ============================================================
# SECTION 2: Valuaciones inválidas / edge cases (validaciones, unpriced, errores upstream)
# ============================================================

# -----
# Validaciones Pydantic (antes de llamar a Buda)
# -----

def test_validation_rejects_negative_amount():
    # Evalúa: Cantidad negativa -> 422 (validación Pydantic)
    resp = client.post("/portfolio/value", json={"portfolio": {"BTC": -1}, "fiat_currency": "CLP"})
    assert resp.status_code == 422


def test_validation_rejects_empty_portfolio():
    # Evalúa: Portafolio vacío -> 422 (min_length=1)
    resp = client.post("/portfolio/value", json={"portfolio": {}, "fiat_currency": "CLP"})
    assert resp.status_code == 422


def test_validation_rejects_invalid_fiat_currency():
    # Evalúa: fiat fuera del set permitido -> 422
    resp = client.post("/portfolio/value", json={"portfolio": {"BTC": 1}, "fiat_currency": "USD"})
    assert resp.status_code == 422


def test_validation_rejects_lowercase_fiat_currency():
    # Evalúa: fiat en minúsculas -> 422 (porque Literal exige "CLP", "PEN", "COP")
    resp = client.post("/portfolio/value", json={"portfolio": {"BTC": 1}, "fiat_currency": "clp"})
    assert resp.status_code == 422


# -----
# Unpriced (no hay ruta)
# -----

@respx.mock
def test_unpriced_single_asset_when_no_route():
    # Evalúa: Activo sin mercado/ruta posible -> unpriced contiene la moneda
    mock_buda_tickers([
        {"market_id": "BTC-CLP", "last_price": ["80000000", "CLP"]},
    ])

    resp = client.post("/portfolio/value", json={"portfolio": {"DOGE": 10}, "fiat_currency": "CLP"})
    assert resp.status_code == 200
    data = resp.json()

    assert Decimal(data["total"]) == Decimal("0")
    assert data["breakdown"] == {}
    assert data["unpriced"] == ["DOGE"]


@respx.mock
def test_unpriced_mixed_portfolio_some_priced_some_not():
    # Evalúa: Portafolio mixto: BTC valorizable, DOGE no -> breakdown parcial + unpriced
    mock_buda_tickers([
        {"market_id": "BTC-CLP", "last_price": ["80000000", "CLP"]},
    ])

    resp = client.post("/portfolio/value", json={"portfolio": {"BTC": 1, "DOGE": 10}, "fiat_currency": "CLP"})
    assert resp.status_code == 200
    data = resp.json()

    assert Decimal(data["total"]) == Decimal("80000000")
    assert Decimal(data["breakdown"]["BTC"]) == Decimal("80000000")
    assert data["unpriced"] == ["DOGE"]


# -----
# Errores upstream (Buda falla)
# -----

@respx.mock
def test_returns_502_when_buda_returns_500():
    # Evalúa: Buda responde 500 -> nuestra API responde 502
    respx.get("https://www.buda.com/api/v2/tickers").mock(
        return_value=Response(500, json={"error": "oops"})
    )

    resp = client.post("/portfolio/value", json={"portfolio": {"BTC": 1}, "fiat_currency": "CLP"})
    assert resp.status_code == 502
    assert "detail" in resp.json()


@respx.mock
def test_returns_502_when_buda_times_out():
    # Evalúa: Timeout hacia Buda -> 502
    respx.get("https://www.buda.com/api/v2/tickers").mock(
        side_effect=httpx.TimeoutException("timeout")
    )

    resp = client.post("/portfolio/value", json={"portfolio": {"BTC": 1}, "fiat_currency": "CLP"})
    assert resp.status_code == 502
    assert "detail" in resp.json()


@respx.mock
def test_returns_502_when_buda_returns_malformed_payload():
    # Evalúa: Respuesta malformada (tickers no es lista) -> 502
    respx.get("https://www.buda.com/api/v2/tickers").mock(
        return_value=Response(200, json={"tickers": "not-a-list"})
    )

    resp = client.post("/portfolio/value", json={"portfolio": {"BTC": 1}, "fiat_currency": "CLP"})
    assert resp.status_code == 502
    assert "detail" in resp.json()
