from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Dict, Literal
import os
import httpx
from fastapi import FastAPI, HTTPException, Query

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# The cache will be refreshed every 5 minutes.
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # seconds (default: 5 min)

# This is the site we'll get the data from:
BINANCE = "https://api.binance.com/api/v3/ticker/price"

# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------
app = FastAPI(title="Currency Converter", version="1.0")

# Use Decimal for financial precision
getcontext().prec = 28

# Simple in-memory cache
_cache: Dict[str, Decimal] = {}
_cache_expiry: datetime | None = None

# -----------------------------------------------------------------------------
# Fetch prices from Binance
# -----------------------------------------------------------------------------
async def _fetch_rates() -> Dict[str, Decimal]:
    """Fetch BTC/fiat prices from Binance."""
    symbols = ["BTCUSDT", "BTCEUR", "BTCGBP"]

    rates: Dict[str, Decimal] = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for sym in symbols:
            r = await client.get(BINANCE, params={"symbol": sym})
            if r.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Binance error for {sym}")
            price = r.json().get("price")
            if price is None:
                raise HTTPException(status_code=502, detail=f"Malformed Binance response for {sym}")
            rates[sym] = Decimal(price)
    return rates


async def _get_rates_cached() -> Dict[str, Decimal]:
    """
    Return cached symbols + cross rates cache if valid;
    otherwise refresh and rebuild once.
    """
    global _cache, _cache_expiry
    if _cache and _cache_expiry and datetime.utcnow() < _cache_expiry:
        # The cache has not expired yet. Let's use the current cache.
        return _cache

    # Let's refresh the cache with fresh values. We can calculate all the rates in one go
    # because there are only three currencies in the system. If there were more currencies,
    # it would be better to implement another system using lazy initialisation.
    prices = await _fetch_rates()                       # {'BTCUSDT': ..., 'BTCEUR': ..., 'BTCGBP': ...}
    cross_rates = _build_cross_rates(prices)        # {'EURUSD': ..., 'USDGBP': ..., 'EURGBP': ..., ...}
    _cache = {**prices, **cross_rates}                  # flat dict with both layers

    _cache_expiry = datetime.utcnow() + timedelta(seconds=CACHE_TTL)
    return _cache


# -----------------------------------------------------------------------------
# Build USD/EUR/GBP cross rates
# -----------------------------------------------------------------------------
def _build_cross_rates(prices: Dict[str, Decimal]) -> Dict[str, Decimal]:
    """Derive direct USD/EUR/GBP cross rates using BTC as bridge."""
    if "BTCUSDT" not in prices:
        raise HTTPException(status_code=502, detail="BTCUSDT price missing")

    btc_usd = prices["BTCUSDT"]
    cross_rates: Dict[str, Decimal] = {}

    for symbol, price in prices.items():
        if symbol == "BTCUSDT" or not symbol.startswith("BTC"):
            continue
        fiat = symbol[3:]
        btc_fiat = price
        # 1 FIAT = (BTCUSD / BTCFIAT) USD
        cross_rates[f"{fiat}USD"] = btc_usd / btc_fiat
        cross_rates[f"USD{fiat}"] = btc_fiat / btc_usd

    # Derive EUR/GBP cross directly. We can do this because there are only 3 currencies.
    # If there were more currencies, we would have to implement a function that computes all
    # the possible pairs.
    cross_rates["EURGBP"] = cross_rates["EURUSD"] * cross_rates["USDGBP"]
    cross_rates["GBPEUR"] = Decimal(1) / cross_rates["EURGBP"]

    return cross_rates


def round_number(x: Decimal) -> Decimal:
    """Round to 2 decimal places."""
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# -----------------------------------------------------------------------------
# REST Endpoint
# -----------------------------------------------------------------------------
@app.get("/convert")
async def convert(
    ccy_from: Literal["USD", "EUR", "GBP"] = Query(..., description="Source currency"),
    ccy_to:   Literal["USD", "EUR", "GBP"] = Query(..., description="Target currency"),
    quantity: Decimal = Query(..., gt=Decimal("0"), description="Amount to convert"),
):
    """Convert between USD, EUR, and GBP using cached, precomputed cross rates."""
    try:
        cache = await _get_rates_cached()         # flat dict

        pair = f"{ccy_from}{ccy_to}"

        if ccy_from == ccy_to:
            # Special case where the two currencies are the same.
            rate = Decimal(1)
        elif pair in cache:
            # direct cross rate already computed
            rate = cache[pair]
        else:
            # Check if the reciprocal cross rate exists and use it.
            reverse = f"{ccy_to}{ccy_from}"
            if reverse in cache:
                # use reciprocal if we only have reverse
                rate = Decimal(1) / cache[reverse]
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported pair {pair}")

        converted = round_number(quantity * rate)
        return {"quantity": float(converted), "ccy": ccy_to}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.get("/rates")
async def rates():
    """
    For debugging purposes.
    """
    cache = await _get_rates_cached()
    raw = {k: float(v) for k, v in cache.items() if k.startswith("BTC")}
    xrs = {k: float(v) for k, v in cache.items() if not k.startswith("BTC")}
    return {"binance_prices": raw, "derived_cross_rates": xrs}