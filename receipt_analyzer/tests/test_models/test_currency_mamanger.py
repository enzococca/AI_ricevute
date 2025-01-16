# tests/test_models/test_currency_manager.py
import time
import unittest
from unittest.mock import Mock, patch
import sys
import os
# Aggiungi il percorso root del progetto al PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.models.currency_manager import CurrencyConversionManager


class TestCurrencyConversionManager(unittest.TestCase):
    def setUp(self):
        self.mock_processor = Mock()
        self.mock_processor.log_action = Mock()
        self.manager = CurrencyConversionManager(self.mock_processor)

    def test_fallback_rates(self):
        """Test i tassi di conversione di fallback."""
        test_cases = [
            ('USD', 'EUR', 0.85),
            ('EUR', 'USD', 1.18),
            ('EUR', 'OMR', 0.44),
            ('OMR', 'EUR', 2.27),
        ]

        for from_curr, to_curr, expected_rate in test_cases:
            with self.subTest(f"{from_curr} to {to_curr}"):
                rate = self.manager.get_fallback_rate(from_curr, to_curr)
                self.assertEqual(rate, expected_rate)

    def test_invalid_currency_pair(self):
        """Test la gestione di coppie di valute non valide."""
        rate = self.manager.get_fallback_rate('XXX', 'YYY')
        self.assertIsNone(rate)
        self.mock_processor.log_action.assert_called()

    @patch('requests.get')
    def test_fixer_io_success(self, mock_get):
        """Test la conversione tramite Fixer.io con successo."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'success': True,
            'rates': {'EUR': 0.85}
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        rate = self.manager.try_fixer_io('USD', 'EUR')
        self.assertEqual(rate, 0.85)

    @patch('requests.get')
    def test_fixer_io_failure(self, mock_get):
        """Test la gestione degli errori di Fixer.io."""
        mock_get.side_effect = Exception('API Error')

        rate = self.manager.try_fixer_io('USD', 'EUR')
        self.assertIsNone(rate)
        self.mock_processor.log_action.assert_called()

    async def test_conversion_rate_caching(self):
        """Test il caching dei tassi di conversione."""
        # Prima chiamata
        rate1 = await self.manager.get_conversion_rate('USD', 'EUR')

        # Modifica il timestamp per simulare una cache valida
        self.manager.last_update['USD_EUR'] = time.time()

        # Seconda chiamata - dovrebbe usare la cache
        rate2 = await self.manager.get_conversion_rate('USD', 'EUR')

        self.assertEqual(rate1, rate2)

    def test_convert_currency(self):
        """Test la conversione di valuta."""
        test_amount = 100
        test_cases = [
            ('USD', 'EUR', 85),  # 100 USD = 85 EUR con tasso 0.85
            ('EUR', 'USD', 118),  # 100 EUR = 118 USD con tasso 1.18
        ]

        for from_curr, to_curr, expected in test_cases:
            with self.subTest(f"{from_curr} to {to_curr}"):
                result = self.manager.convert_currency(test_amount, from_curr, to_curr)
                self.assertAlmostEqual(result, expected, places=2)


if __name__ == '__main__':
    unittest.main()

