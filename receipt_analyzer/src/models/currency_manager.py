"""
Automatically generated file from migration script.
"""


import os

from PyQt5.QtWidgets import (
     QInputDialog, QMessageBox, QLineEdit
)


import requests
import time
from forex_python.converter import CurrencyRates


class CurrencyConversionManager:
    """Gestisce le conversioni di valuta usando multiple fonti."""

    def __init__(self, processor):

        self.conversion_rates = {}
        self.sources = [
            self.try_exchangerate_api,
            self.try_forex_python,
            self.try_fixer_io,
            self.get_fallback_rate
        ]
        self.last_update = {}
        self.update_interval = 3600  # 1 ora
        self.logger = processor
        #self.logger.log_action("dajie")
        try:
            self.exchange_api_key = self.load_or_get_exchange_api_key(processor, allow_skip=True)
            if self.exchange_api_key is None:
                self.logger.log_action("Exchange Rate API key non configurata. Verranno usati i tassi di fallback.")
            else:
                self.logger.log_action("Exchange Rate API key configurata con successo.")
        except Exception as e:
            self.logger.log_action(f"Errore nel caricamento dell'API key di Exchange: {str(e)}")
            self.exchange_api_key = None

    def load_or_get_exchange_api_key(self,parent_widget,allow_skip=True):
        """
        Carica l'API key per Exchange Rate da file o chiede all'utente di inserirla.

        Args:
            parent_widget: Widget genitore per il dialogo di input
            allow_skip: Permette di saltare l'inserimento della chiave

        Returns:
            str: API key valida o None se saltato
        """
        api_key_file = "exchange_api_key.txt"

        def is_valid_api_key(key):
            """Verifica se l'API key ha il formato corretto"""
            return len(key) >= 24

        def save_api_key(key):
            try:
                with open(api_key_file, "w") as f:
                    f.write(key.strip())
                return True
            except Exception as e:
                print(f"Errore nel salvare l'API key di Exchange: {str(e)}")
                return False

        try:
            if os.path.exists(api_key_file):
                with open(api_key_file, "r") as f:
                    api_key = f.read().strip()
                    if is_valid_api_key(api_key):
                        return api_key
        except Exception as e:
            print(f"Errore nella lettura dell'API key di Exchange: {str(e)}")

        # Messaggio per chiedere se si vuole inserire la chiave
        if allow_skip:
            reply = QMessageBox.question(
                parent_widget,
                'Exchange Rate API Key',
                'Vuoi configurare l\'API key di Exchange Rate?\nSe non la configuri, verranno usati i tassi di fallback.',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.No:
                return None

        while True:
            api_key, ok = QInputDialog.getText(
                parent_widget,
                "Inserisci Exchange Rate API Key",
                "Inserisci la tua Exchange Rate API key:\n(o premi Annulla per usare i tassi di fallback)",
                QLineEdit.Password
            )

            if not ok:
                if allow_skip:
                    return None
                else:
                    raise ValueError("È necessaria una API key valida per Exchange Rate per continuare")

            if is_valid_api_key(api_key):
                if save_api_key(api_key):
                    return api_key
            else:
                msg = QMessageBox.warning(
                    parent_widget,
                    "API Key non valida",
                    "L'API key di Exchange Rate non sembra valida.\nVuoi riprovare?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if msg == QMessageBox.No and allow_skip:
                    return None


    def get_fallback_rate(self, from_currency, to_currency):
        """Ottiene un tasso di fallback in caso di fallimento della richiesta online."""
        fallback_rates = {
            ('USD', 'EUR'): 0.85,
            ('EUR', 'USD'): 1.18,
            # Medio Oriente
            ('USD', 'AED'): 3.67,  # Dirham degli Emirati Arabi Uniti
            ('AED', 'USD'): 0.27,
            ('USD', 'SAR'): 3.75,  # Riyal Saudita
            ('SAR', 'USD'): 0.27,
            ('USD', 'OMR'): 0.38,  # Rial omanita
            ('OMR', 'USD'): 2.60,
            # Indonesia
            ('USD', 'IDR'): 14300.00,  # Rupia indonesiana
            ('IDR', 'USD'): 0.000070,
            # Asia Centrale
            ('USD', 'KZT'): 425.50,  # Tenge kazaco
            ('KZT', 'USD'): 0.0024,
            ('USD', 'UZS'): 10500.00,  # Sum uzbeko
            ('UZS', 'USD'): 0.000095,
            # Altre conversioni utili
            ('EUR', 'AED'): 4.32,
            ('AED', 'EUR'): 0.23,
            ('EUR', 'IDR'): 16900.00,
            ('IDR', 'EUR'): 0.000059,
            ('EUR', 'OMR'): 0.44,
            ('OMR', 'EUR'): 2.27,
        }

        rate = fallback_rates.get((from_currency, to_currency))
        if rate is not None:
            self.logger.log_action(f"Usato tasso di fallback: {rate} per {from_currency} a {to_currency}.")
        else:
            self.logger.log_action(f"Tasso di fallback non disponibile per la coppia {from_currency} a {to_currency}.")
        return rate


    def try_fixer_io(self, from_currency, to_currency):
        """Tenta di ottenere il tasso di cambio da fixer.io."""
        api_key = "api_key_fixer"  # Sostituisci con la tua chiave API
        url = f"http://data.fixer.io/api/latest?access_key={api_key}&base={from_currency}&symbols={to_currency}"

        try:
            response = requests.get(url)
            response.raise_for_status()  # Solleva un errore per risposte HTTP errate
            data = response.json()

            if data.get("success"):
                rate = data['rates'][to_currency]
                self.logger.log_action(f"Tasso ottenuto da fixer.io: {rate} per {from_currency} a {to_currency}.")
                return rate
            else:
                self.logger.log_action("Errore nella risposta di fixer.io.")
        except Exception as e:
            self.logger.log_action(f"Errore durante la richiesta a fixer.io: {str(e)}")
        return None  # Ritorna None in caso di errore

    def convert_currency(self, amount, from_currency, to_currency):
        """Converte la valuta usando il tasso appropriato."""
        try:
            rate = self.try_fixer_io(from_currency, to_currency)
            if rate is None:
                rate = self.get_fallback_rate(from_currency, to_currency)
                self.logger.log_action(f"Usando tasso di fallback per {from_currency} a {to_currency}: {rate}")
            else:
                self.logger.log_action(f"Usando tasso da fixer.io per {from_currency} a {to_currency}: {rate}")

            if rate is None:
                self.logger.log_action(f"Nessun tasso di conversione disponibile per {from_currency} a {to_currency}")
                return amount

            converted_amount = amount * rate
            self.logger.log_action(
                f"Conversione completata: {amount} {from_currency} = {converted_amount} {to_currency}")
            return converted_amount

        except Exception as e:
            self.logger.log_action(f"Errore nella conversione: {str(e)}")
            return amount

    async def get_conversion_rate(self, from_currency: str, to_currency: str = "EUR") -> tuple:
        """Ottiene il tasso di conversione dalla fonte più affidabile disponibile."""
        try:
            key = f"{from_currency}_{to_currency}"
            current_time = time.time()

            # Controlla se abbiamo un tasso recente
            if (key in self.conversion_rates and
                    current_time - self.last_update.get(key, 0) < self.update_interval):
                return self.conversion_rates[key]

            # Prova ogni fonte in ordine
            for source in self.sources:
                try:
                    rate, source_name = await source(from_currency, to_currency)
                    if rate:
                        self.conversion_rates[key] = {
                            "rate": rate,
                            "source": source_name,
                            "timestamp": current_time
                        }
                        self.last_update[key] = current_time
                        return self.conversion_rates[key]
                except:
                    continue

            raise ValueError(f"Nessuna fonte disponibile per la conversione {from_currency} -> {to_currency}")

        except Exception as e:
            print(f"Errore nella conversione valuta: {str(e)}")
            return None

    async def try_exchangerate_api(self, from_currency: str, to_currency: str) -> tuple:
        """Prova a usare ExchangeRate-API."""
        if not self.exchange_api_key:
            self.logger.log_action("Exchange Rate API non configurata, salto questo metodo.")
            return None, None

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = f"https://v6.exchangerate-api.com/v6/{self.exchange_api_key}/pair/{from_currency}/{to_currency}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'conversion_rate' in data:
                            rate = data['conversion_rate']
                            self.logger.log_action(
                                f"ExchangeRate API: trovato tasso {rate} per {from_currency} a {to_currency}")
                            return rate, "ExchangeRate-API"
                    else:
                        self.logger.log_action(f"ExchangeRate API: errore {response.status}")
        except Exception as e:
            self.logger.log_action(f"Errore ExchangeRate API: {str(e)}")
        return None, None

    async def try_forex_python(self, from_currency: str, to_currency: str) -> tuple:
        """Prova a usare Forex-Python."""
        try:

            c = CurrencyRates()
            rate = c.get_rate(from_currency, to_currency)
            return rate, "Forex-Pythonfrom langchain.prompts import PromptTemplate"
        except:
            return None, None

