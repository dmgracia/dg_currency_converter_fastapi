import unittest
from decimal import Decimal
from unittest.mock import patch
from fastapi.testclient import TestClient

import app

# Deterministic BTC quotes (hardcoded values):
# BTCUSDT = 100,000  (USD per 1 BTC)
# BTCEUR  =  90,000  (EUR per 1 BTC)
# BTCGBP  =  80,000  (GBP per 1 BTC)
#
# => EURUSD = 100000 / 90000  = 1.111111...
#    USDEUR = 0.9
#    GBPUSD = 100000 / 80000  = 1.25
#    USDGBP = 0.8
#    EURGBP = 1.111111... * 0.8 = 0.888888...
#    GBPEUR = 1 / 0.888888...   = 1.125
PRICES = {
    "BTCUSDT": Decimal("100000"),
    "BTCEUR":  Decimal("90000"),
    "BTCGBP":  Decimal("80000"),
}
CROSS_RATES = app._build_cross_rates(PRICES)
FLAT_CACHE = {**PRICES, **CROSS_RATES}


class CurrencyConverterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app.app)  # FastAPI app instance

    def setUp(self):
        # Patch the async cache getter to return our flat cache
        async def _fake_get_rates_cached():
            return FLAT_CACHE
        self.patcher = patch("app._get_rates_cached", new=_fake_get_rates_cached)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    # ----- Pure math tests on _build_cross_rates -----

    def test_build_cross_rates_basic(self):
        crosses = app._build_cross_rates(PRICES)
        self.assertAlmostEqual(float(crosses["EURUSD"]), 100000/90000, places=12)
        self.assertAlmostEqual(float(crosses["GBPUSD"]), 100000/80000, places=12)
        self.assertAlmostEqual(float(crosses["USDEUR"]), 0.9, places=12)
        self.assertAlmostEqual(float(crosses["USDGBP"]), 0.8, places=12)

    def test_cross_consistency(self):
        cross_rates = app._build_cross_rates(PRICES)
        self.assertAlmostEqual(
            float(cross_rates["EURGBP"]),
            float(cross_rates["EURUSD"]) * float(cross_rates["USDGBP"]),
            places=12,
        )
        self.assertAlmostEqual(
            float(cross_rates["GBPEUR"]),
            1.0 / float(cross_rates["EURGBP"]),
            places=12,
        )

    # ----- API tests on /convert -----

    def test_convert_usd_to_gbp(self):
        r = self.client.get("/convert", params={"ccy_from": "USD", "ccy_to": "GBP", "quantity": "100"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["ccy"], "GBP")
        self.assertEqual(data["quantity"], 80.0)  # 100 * USDGBP(=0.8)

    def test_convert_usd_to_eur(self):
        r = self.client.get("/convert", params={"ccy_from": "USD", "ccy_to": "EUR", "quantity": "100"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["ccy"], "EUR")
        self.assertEqual(data["quantity"], 90.0)  # 100 * USDEUR(=0.9)

    def test_convert_eur_to_gbp(self):
        r = self.client.get("/convert", params={"ccy_from": "EUR", "ccy_to": "GBP", "quantity": "100"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["ccy"], "GBP")
        self.assertEqual(data["quantity"], 88.89)  # 100 * 0.888888... rounded

    def test_convert_same_currency(self):
        r = self.client.get("/convert", params={"ccy_from": "GBP", "ccy_to": "GBP", "quantity": "123.45"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["ccy"], "GBP")
        self.assertEqual(data["quantity"], 123.45)

    # ----- Optional: /rates shape -----

    def test_rates_endpoint_shape(self):
        r = self.client.get("/rates")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("binance_prices", data)
        self.assertIn("derived_cross_rates", data)
        # Ensure both raw BTC* and cross keys are present
        self.assertIn("BTCUSDT", data["binance_prices"])
        self.assertIn("EURUSD", data["derived_cross_rates"])
        self.assertIn("USDGBP", data["derived_cross_rates"])


if __name__ == "__main__":
    unittest.main()
