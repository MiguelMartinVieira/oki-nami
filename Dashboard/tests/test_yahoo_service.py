"""Tests para data/yahoo.py — precios e historial de Yahoo Finance con mocks."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from data.yahoo import get_yahoo_history, get_yahoo_price


class TestYahooService:
    @patch("requests.get")
    def test_get_yahoo_price_success(self, mock_get):
        # Mock de respuesta válida de Yahoo
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "chart": {"result": [{"meta": {"regularMarketPrice": 420.69}}]}
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        get_yahoo_price.clear()  # Limpiar cache de streamlit
        price = get_yahoo_price("AAPL")
        assert price == 420.69

    @patch("requests.get")
    def test_get_yahoo_price_failure(self, mock_get):
        # Mock de error (e.g. 404 o timeout) sin archivo de caché
        mock_get.side_effect = Exception("Network error")

        get_yahoo_price.clear()
        price = get_yahoo_price("NONEXISTENT_TICKER_FAIL")
        assert price is None

    @patch("data.yahoo._get_cached_price", return_value=541.50)
    @patch("requests.get")
    def test_get_yahoo_price_fallback_to_cache(self, mock_get, mock_cached):
        # Si Yahoo falla pero existe caché local, devuelve el precio en caché
        mock_get.side_effect = Exception("Network timeout")

        get_yahoo_price.clear()
        price = get_yahoo_price("BRK-B")
        assert price == 541.50

    @patch("requests.get")
    def test_get_yahoo_history_success(self, mock_get):
        # Remove stale cache file to avoid pollution
        import os

        cache_path = os.path.join(".cache", "yahoo_AAPL.csv")
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
            except Exception:
                pass

        mock_response = MagicMock()
        # Mock de historial con 2 puntos usando marcas de tiempo dinámicas
        today_ts = int(pd.Timestamp.today().timestamp())
        yesterday_ts = today_ts - 86400
        mock_response.json.return_value = {
            "chart": {
                "result": [
                    {
                        "timestamp": [yesterday_ts, today_ts],
                        "indicators": {"quote": [{"close": [100.0, 105.0]}]},
                    }
                ]
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        get_yahoo_history.clear()
        df = get_yahoo_history("AAPL", days=2)
        assert len(df) == 2
        assert df.iloc[0]["Price"] == 100.0
        assert df.iloc[1]["Price"] == 105.0
        assert isinstance(df.iloc[0]["Date"], (pd.Timestamp, object))

    @patch("requests.get")
    def test_get_yahoo_history_failure(self, mock_get):
        mock_get.side_effect = Exception("API Down")

        get_yahoo_history.clear()
        df = get_yahoo_history("FAIL")
        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert list(df.columns) == ["Date", "Price"]
