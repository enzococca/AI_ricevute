import unittest
import sys
import os
# Aggiungi il percorso root del progetto al PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.agents.date_formatter import DateFormatterAgent

class TestDateFormatterAgent(unittest.TestCase):
    def setUp(self):
        self.agent = DateFormatterAgent()

    def test_standard_date_formats(self):
        test_cases = [
            ("01/12/2024", "2024-12-01"),
            ("01-12-2024", "2024-12-01"),
            ("2024/12/01", "2024-12-01"),
            ("2024-12-01", "2024-12-01"),
        ]
        for input_date, expected in test_cases:
            with self.subTest(input_date=input_date):
                result = self.agent.format_date(input_date)
                self.assertEqual(result, expected)

    def test_short_year_formats(self):
        test_cases = [
            ("01/12/24", "2024-12-01"),
            ("01-12-24", "2024-12-01"),
            ("24/12/01", "2024-12-01"),
        ]
        for input_date, expected in test_cases:
            with self.subTest(input_date=input_date):
                result = self.agent.format_date(input_date)
                self.assertEqual(result, expected)

    def test_english_month_formats(self):
        test_cases = [
            ("16-Dec-24", "2024-12-16"),
            ("16 December 2024", "2024-12-16"),
            ("Dec 16 2024", "2024-12-16"),
            ("December 16 24", "2024-12-16"),
        ]
        for input_date, expected in test_cases:
            with self.subTest(input_date=input_date):
                result = self.agent.format_date(input_date)
                self.assertEqual(result, expected)

    def test_invalid_dates(self):
        invalid_dates = [
            "invalid",
            "32/13/2024",  # giorno/mese invalido
            "2024/13/32",  # mese/giorno invalido
            "",            # stringa vuota
        ]
        for invalid_date in invalid_dates:
            with self.subTest(invalid_date=invalid_date):
                result = self.agent.format_date(invalid_date)
                self.assertEqual(result, str(invalid_date))

if __name__ == '__main__':
    unittest.main()