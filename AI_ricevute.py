"""
Questo script è un'applicazione desktop sviluppata in Python che automatizza il processo di gestione e analisi degli scontrini. Ecco le sue principali funzionalità:

Interfaccia Utente


Utilizza PyQt5 per creare un'interfaccia grafica intuitiva
Mostra una tabella per visualizzare i dati degli scontrini
Include un'area di log per monitorare il processo
Offre pulsanti per caricare scontrini, esportare in PDF e aggiornare Excel


Analisi degli Scontrini


Utilizza GPT-4o per estrarre informazioni dagli scontrini fotografati
Riconosce automaticamente dati come data, importo, valuta ed esercente
Categorizza le spese in base al tipo di acquisto
Gestisce vari formati di data e li standardizza


Gestione Valute


Implementa un sistema di conversione valutaria multilivello:

Prova prima ExchangeRate API
Poi Forex Python
Quindi Fixer.io
Infine usa tassi di fallback predefiniti


Converte automaticamente gli importi in EUR


Archiviazione e Report


Salva i dati in un file Excel con formattazione automatica
Genera report PDF dettagliati con:

Tabella completa delle transazioni
Riepilogo delle spese totali
Analisi per categoria
Dettagli di ogni transazione




Funzionalità Aggiuntive da inserire


Monitoraggio continuo di una cartella per nuovi scontrini
Rilevamento automatico di duplicati
Ottimizzazione delle immagini per miglior riconoscimento
Logging dettagliato delle operazioni

Lo script è particolarmente utile per:

Gestione spese aziendali
Tracciamento spese personali
Organizzazione contabile
Analisi delle tendenze di spesa
Gestione di scontrini in valute diverse
"""
import asyncio
import os

import sys
import time
import json
import base64


import requests

from PyQt5.QtCore import QMetaType,pyqtSlot

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QFileDialog, QLabel, QHeaderView, QWidget, QTextEdit, QInputDialog, QMessageBox, QLineEdit
)

# Registra il tipo in modo alternativo
QMetaType.type("QTextCursor")
from PyQt5.QtCore import QThread, pyqtSignal
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from fpdf import FPDF
import pandas as pd
import openai
# Aggiornamento alla nuova sintassi di LangChain
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
#moduli forex
from forex_python.converter import CurrencyRates
import arabic_reshaper
from bidi.algorithm import get_display
# Directory and file paths
WATCH_DIR = "scontrini"
EXCEL_FILE = "pagamenti.xlsx"
PDF_REPORT = "report_pagamenti.pdf"

# Create receipts directory if it doesn't exist
os.makedirs(WATCH_DIR, exist_ok=True)


class ProcessingWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    log_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_path = None
        self.analysis_chain = None
        try:
            self.api_key_openai = self.load_or_get_api_key(parent)
            self.client = openai.OpenAI(api_key=self.api_key_openai)
        except Exception as e:
            raise ValueError(f"Impossibile inizializzare il client OpenAI: {str(e)}")



    def setup(self, image_path: str, analysis_chain):
        self.image_path = image_path
        self.analysis_chain = analysis_chain
        return self

    def load_or_get_api_key(self,parent_widget):
        """
        Carica l'API key da file o chiede all'utente di inserirla.

        Args:
            parent_widget: Widget genitore per il dialogo di input

        Returns:
            str: API key valida
        """
        api_key_file = "api_key.txt"

        def is_valid_api_key(key):
            """Verifica se l'API key ha il formato corretto"""
            return key.startswith("sk-proj-") and len(key) > 20

        def save_api_key(key):
            """Salva l'API key nel file"""
            try:
                with open(api_key_file, "w") as f:
                    f.write(key.strip())
                return True
            except Exception as e:
                print(f"Errore nel salvare l'API key: {str(e)}")
                return False

        try:
            # Prova a leggere l'API key dal file
            if os.path.exists(api_key_file):
                with open(api_key_file, "r") as f:
                    api_key = f.read().strip()
                    if is_valid_api_key(api_key):
                        return api_key
        except Exception as e:
            print(f"Errore nella lettura dell'API key: {str(e)}")

        # Se il file non esiste o l'API key non è valida, chiedi all'utente
        while True:
            api_key, ok = QInputDialog.getText(
                parent_widget,
                "Inserisci API Key",
                "Inserisci la tua OpenAI API key:",
                QLineEdit.Password
            )

            if not ok:
                raise ValueError("È necessaria una API key valida per continuare")

            if is_valid_api_key(api_key):
                # Salva la nuova API key
                if save_api_key(api_key):
                    return api_key
            else:
                QMessageBox.warning(
                    parent_widget,
                    "API Key non valida",
                    "L'API key deve iniziare con 'sk-proj-' ed essere sufficientemente lunga.\nRiprova."
                )

    async def process_chains(self, text_content):
        self.log_message.emit("1. Iniziando l'analisi con la catena principale...")
        # Prima catena: Analisi base
        analysis_result = await self.analysis_chain.analysis_chain.ainvoke({"text": text_content})
        self.log_message.emit(f"Risultato analisi primaria: {analysis_result}")

        # Seconda catena: Validazione
        self.log_message.emit("\n2. Validazione dei dati estratti...")
        validation_result = await self.analysis_chain.validation_chain.ainvoke({"json": str(analysis_result)})
        self.log_message.emit(f"Risultato validazione: {validation_result}")

        # Parse del risultato dell'analisi
        try:
            if isinstance(analysis_result, str):
                data = json.loads(analysis_result)
            else:
                data = analysis_result
        except json.JSONDecodeError:
            self.log_message.emit("Errore nel parsing JSON, cercando JSON nella stringa...")
            json_start = str(analysis_result).find('{')
            json_end = str(analysis_result).rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(str(analysis_result)[json_start:json_end])
            else:
                raise ValueError("JSON non trovato nei risultati")

        # Log della conversione valuta in modo più dettagliato
        self.log_message.emit("\n3. Processo di conversione valuta...")
        if 'valuta' in data and 'importo' in data:
            original_currency = data['valuta']
            original_amount = float(data['importo'])
            self.log_message.emit(f"Valuta originale: {original_currency}, Importo: {original_amount}")

            try:
                # Tentativo con ExchangeRate API
                self.log_message.emit("Tentativo di conversione con ExchangeRate API...")
                rate, source = await self.parent().currency_conversion_manager.try_exchangerate_api(
                    original_currency, 'EUR')
                if rate:
                    self.log_message.emit(f"Tasso ExchangeRate API trovato: 1 {original_currency} = {rate} EUR")
                    converted_amount = original_amount * rate
                else:
                    # Tentativo con Forex Python
                    self.log_message.emit("ExchangeRate API non disponibile, provo con Forex Python...")
                    rate, source = await self.parent().currency_conversion_manager.try_forex_python(
                        original_currency, 'EUR')
                    if rate:
                        self.log_message.emit(f"Tasso Forex Python trovato: 1 {original_currency} = {rate} EUR")
                        converted_amount = original_amount * rate
                    else:
                        # Tentativo con Fixer.io
                        self.log_message.emit("Forex Python non disponibile, provo con Fixer.io...")
                        rate = self.parent().currency_conversion_manager.try_fixer_io(original_currency, 'EUR')
                        if rate:
                            self.log_message.emit(f"Tasso Fixer.io trovato: 1 {original_currency} = {rate} EUR")
                            converted_amount = original_amount * rate
                        else:
                            # Fallback alle conversioni locali
                            self.log_message.emit(
                                "Tutti i servizi online non disponibili, uso tasso di fallback...")
                            rate = self.parent().currency_conversion_manager.get_fallback_rate(original_currency,
                                                                                               'EUR')
                            if rate:
                                self.log_message.emit(
                                    f"Tasso di fallback trovato: 1 {original_currency} = {rate} EUR")
                                converted_amount = original_amount * rate
                            else:
                                self.log_message.emit("Nessun tasso di conversione disponibile")
                                converted_amount = original_amount

                if rate:
                    data['importo_eur'] = converted_amount
                    self.log_message.emit(
                        f"Conversione completata: {original_amount} {original_currency} = {converted_amount:.2f} EUR")
                    self.log_message.emit(
                        f"Fonte del tasso di conversione: {source if source else 'Tasso di fallback'}")

            except Exception as e:
                self.log_message.emit(f"Errore durante la conversione: {str(e)}")
                self.log_message.emit("Uso il tasso di fallback come ultima risorsa")
                rate = self.parent().currency_conversion_manager.get_fallback_rate(original_currency, 'EUR')
                if rate:
                    converted_amount = original_amount * rate
                    data['importo_eur'] = converted_amount
                    self.log_message.emit(
                        f"Conversione con fallback: {original_amount} {original_currency} = {converted_amount:.2f} EUR")
                else:
                    data['importo_eur'] = original_amount

        # Terza catena: Categorizzazione
        self.log_message.emit("\n4. Categorizzazione della spesa...")
        if "esercente" in data and "luogo" in data:
            description = f"{data['esercente']} - {data['luogo']}"
            category_result = await self.analysis_chain.categorization_chain.ainvoke({"description": description})
            self.log_message.emit(f"Risultato categorizzazione: {category_result}")
            data["categoria"] = category_result

        return data

    def run(self):
        try:
            self.log_message.emit("Iniziando il processo completo di analisi...")

            with open(self.image_path, "rb") as image_file:
                image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
                self.log_message.emit("Immagine caricata e codificata")

            # Ottieni il testo dall'immagine con Vision
            self.log_message.emit("Estraendo testo dall'immagine con GPT-4o...")
            completion = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Analizza questo scontrino ed estrai:
{
    "data": "data scontrino",
    "importo": numero,
    "valuta": "codice valuta",
    "esercente": "nome",
    "luogo": "località"
}
Rispondi SOLO con il JSON."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )

            analysis_text = completion.choices[0].message.content.strip()
            self.log_message.emit(f"Testo estratto dall'immagine: {analysis_text}")

            # Processa attraverso le catene
            self.log_message.emit("\nAvviando il processo delle catene di analisi...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                data = loop.run_until_complete(self.process_chains(analysis_text))
                self.log_message.emit("\nProcesso delle catene completato con successo")
                self.finished.emit(data)
            finally:
                loop.close()

        except Exception as e:
            error_msg = f"Errore nell'elaborazione: {str(e)}"
            self.log_message.emit(error_msg)
            self.error.emit(error_msg)



class ExpenseAnalysisAgent:
    """Agente per l'analisi delle spese sulle categorie."""

    def __init__(self, excel_file: str):
        self.excel_file = excel_file

    def analyze_expenses(self) -> str:
        """Analizza le spese e determina la categoria di spesa principale."""

        try:
            # Leggi lo storico delle spese dal file Excel
            df = pd.read_excel(self.excel_file)

            # Assicurati che le colonne siano correttamente nominate
            df.columns = df.columns.str.strip()

            # Somma gli importi per ogni categoria
            total_by_category = df.groupby('Descrizione')['Importo (EUR)'].sum()

            # Trova la categoria con la spesa maggiore
            highest_expense_category = total_by_category.idxmax()
            highest_expense_value = total_by_category.max()

            return (f"La categoria di spesa principale è '{highest_expense_category}' con una spesa totale di "
                    f"{highest_expense_value:.2f} EUR.")
        except Exception as e:
            print(f"Errore nell'analisi delle spese: {str(e)}")
            return "Errore nell'analisi delle spese."


class DateFormatterAgent:
    """Agente per la formattazione delle date."""

    @staticmethod
    def format_date(date_str: str) -> str:
        """Formatta la data nel formato AAAA-MM-GG."""
        from datetime import datetime
        import re

        try:
            # Se è già un oggetto datetime, formattalo direttamente
            if isinstance(date_str, datetime):
                return date_str.strftime("%Y-%m-%d")

            # Pulisci la stringa da eventuali caratteri non necessari
            date_str = str(date_str).strip()

            # Lista di formati da provare
            date_formats = [
                # Formati con mese in lettere
                "%d-%b-%y",  # 16-Dec-24
                "%d-%B-%y",  # 16-December-24
                "%d-%b-%Y",  # 16-Dec-2024
                "%d-%B-%Y",  # 16-December-2024
                "%d %b %y",  # 16 Dec 24
                "%d %B %y",  # 16 December 24
                "%d %b %Y",  # 16 Dec 2024
                "%d %B %Y",  # 16 December 2024
                "%b %d %Y",  # Dec 16 2024
                "%B %d %Y",  # December 16 2024
                "%b %d %y",  # Dec 16 24
                "%B %d %y",  # December 16 24
                # Formati numerici standard
                "%d/%m/%Y",  # 01/12/2024
                "%d-%m-%Y",  # 01-12-2024
                "%Y/%m/%d",  # 2024/12/01
                "%Y-%m-%d",  # 2024-12-01
                "%d/%m/%y",  # 01/12/24
                "%d-%m-%y",  # 01-12-24
                "%y/%m/%d",  # 24/12/01
                "%y-%m-%d",  # 24-12-01
            ]

            # Prova prima a parsare con i formati standard
            for fmt in date_formats:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    # Se l'anno è a due cifre, aggiungi 2000
                    if date_obj.year < 100:
                        date_obj = date_obj.replace(year=date_obj.year + 2000)
                    return date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    continue

            # Se nessun formato standard funziona, prova a estrarre i numeri e il mese
            # Pattern per trovare mesi in inglese
            month_pattern = r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)'
            month_match = re.search(month_pattern, date_str.lower())

            if month_match:
                # Mappa dei mesi in inglese
                month_map = {
                    'jan': 1, 'january': 1,
                    'feb': 2, 'february': 2,
                    'mar': 3, 'march': 3,
                    'apr': 4, 'april': 4,
                    'may': 5,
                    'jun': 6, 'june': 6,
                    'jul': 7, 'july': 7,
                    'aug': 8, 'august': 8,
                    'sep': 9, 'september': 9,
                    'oct': 10, 'october': 10,
                    'nov': 11, 'november': 11,
                    'dec': 12, 'december': 12
                }

                numbers = re.findall(r'\d+', date_str)
                if len(numbers) == 2:  # giorno e anno
                    day = int(numbers[0])
                    year = int(numbers[1])
                    month = month_map[month_match.group(1)]

                    # Gestisci anni a 2 cifre
                    if year < 100:
                        year += 2000

                    # Verifica che i numeri siano validi
                    if 1 <= day <= 31 and 1 <= month <= 12 and 2000 <= year <= 2100:
                        return f"{year:04d}-{month:02d}-{day:02d}"

            # Se ancora non funziona, prova a estrarre solo i numeri
            numbers = re.findall(r'\d+', date_str)
            if len(numbers) == 3:
                day = int(numbers[0])
                month = int(numbers[1])
                year = int(numbers[2])

                # Gestisci anni a 2 cifre
                if year < 100:
                    year += 2000

                # Verifica che i numeri siano validi
                if 1 <= day <= 31 and 1 <= month <= 12 and 2000 <= year <= 2100:
                    return f"{year:04d}-{month:02d}-{day:02d}"

            raise ValueError(f"Formato data non riconosciuto: {date_str}")

        except Exception as e:
            print(f"Errore nella formattazione della data: {str(e)}")
            return str(date_str)


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


class ReceiptAnalysisChain:
    def __init__(self, processor):
        self.logger = processor
        api_openai = ProcessingWorker().load_or_get_api_key(self)



        # Inizializzazione del modello
        self.llm = ChatOpenAI(
            temperature=0,
            api_key=api_openai,
            model="gpt-4o-mini"
        )

        # Output parser
        output_parser = StrOutputParser()

        # Definizione dei template usando la nuova sintassi
        self.analysis_prompt = ChatPromptTemplate.from_template("""
            Analizza il seguente testo estratto da uno scontrino e identifica:
            1. Data
            2. Importo totale
            3. Valuta
            4. Nome esercente
            5. Località

            Testo: {text}

            Rispondi in formato JSON strutturato.
        """)
        self.analysis_chain = self.analysis_prompt | self.llm | output_parser

        self.validation_prompt = ChatPromptTemplate.from_template("""
            Verifica la validità dei seguenti dati estratti:
            {json}

            Controlla:
            1. La data è in un formato valido?
            2. L'importo è un numero ragionevole?
            3. La valuta è riconosciuta?

            Suggerisci correzioni se necessario.
        """)
        self.validation_chain = self.validation_prompt | self.llm | output_parser

        self.categorization_prompt = ChatPromptTemplate.from_template("""
            Analizza questa descrizione e categorizza la spesa:
            {description}

            Categorie possibili:
            - Cibo e Ristorazione
            - Trasporti
            - Shopping
            - Servizi
            - Altro

            Fornisci anche un livello di confidenza (0-100%).
        """)
        self.categorization_chain = self.categorization_prompt | self.llm | output_parser

        # Non abbiamo più bisogno della memory qui poiché non stiamo
        # mantenendo uno stato della conversazione

    def get_conversion_info(self, currency: str) -> dict:
        """Ottiene informazioni sulla conversione utilizzata."""
        return {
            "valuta": currency,
            "tasso": getattr(self, 'current_rate', None),
            "fonte": getattr(self, 'rate_source', None),
            "timestamp": getattr(self, 'rate_timestamp', None)
        }


class FileAgent:
    """Agente per la gestione dei file e duplicati."""

    def __init__(self, watch_dir: str):
        self.watch_dir = watch_dir
        self.file_history = set()
        self.load_history()

    def load_history(self):
        """Carica la cronologia dei file processati."""
        try:
            history_file = os.path.join(self.watch_dir, ".file_history")
            if os.path.exists(history_file):
                with open(history_file, "r") as f:
                    self.file_history = set(f.read().splitlines())
        except Exception as e:
            print(f"Errore nel caricamento della cronologia: {str(e)}")

    def save_history(self):
        """Salva la cronologia dei file processati."""
        try:
            history_file = os.path.join(self.watch_dir, ".file_history")
            with open(history_file, "w") as f:
                f.write("\n".join(self.file_history))
        except Exception as e:
            print(f"Errore nel salvataggio della cronologia: {str(e)}")

    def is_duplicate(self, file_path: str) -> bool:
        """Controlla se il file è un duplicato."""
        import hashlib
        try:
            with open(file_path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
                if file_hash in self.file_history:
                    return True
                self.file_history.add(file_hash)
                self.save_history()
                return False
        except Exception as e:
            print(f"Errore nel controllo duplicati: {str(e)}")
            return False


class OCRAgent:
    """Agente per l'ottimizzazione del riconoscimento del testo."""

    def __init__(self):
        self.preprocessing_methods = [
            self.enhance_contrast,
            self.denoise,
            self.sharpen
        ]

    def enhance_contrast(self, image):
        """Migliora il contrasto dell'immagine."""
        try:
            import cv2
            import numpy as np
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            limg = cv2.merge((cl, a, b))
            return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        except:
            return image

    def denoise(self, image):
        """Rimuove il rumore dall'immagine."""
        try:
            import cv2
            return cv2.fastNlMeansDenoisingColored(image)
        except:
            return image

    def sharpen(self, image):
        """Aumenta la nitidezza dell'immagine."""
        try:
            import cv2
            import numpy as np
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            return cv2.filter2D(image, -1, kernel)
        except:
            return image

    def optimize_image(self, image_path: str) -> str:
        """Ottimizza l'immagine per il riconoscimento del testo."""
        try:
            import cv2
            image = cv2.imread(image_path)

            # Applica i metodi di preprocessing in sequenza
            for method in self.preprocessing_methods:
                image = method(image)

            # Salva l'immagine ottimizzata
            optimized_path = image_path.replace(".", "_optimized.")
            cv2.imwrite(optimized_path, image)
            return optimized_path
        except Exception as e:
            print(f"Errore nell'ottimizzazione dell'immagine: {str(e)}")
            return image_path



class ReceiptProcessor(QMainWindow):
    # Aggiungi un segnale personalizzato per il logging
    log_signal = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analisi Scontrini con IA")
        self.setGeometry(100, 100, 1200, 800)
        self.setup_ui()
        # Inizializza gli agenti
        self.date_formatter = DateFormatterAgent()
        self.currency_conversion_manager = CurrencyConversionManager(self)
        self.receipt_analysis_chain = ReceiptAnalysisChain(self)
        self.file_agent = FileAgent(WATCH_DIR)  # Aggiunto FileAgent
        self.ocr_agent = OCRAgent()  # Aggiunto OCRAgent

        # Connetti il segnale di log al metodo di logging
        self.log_signal.connect(self.log_action)


        self.data = []
        self.current_workers = []
        self.start_watching()

    @pyqtSlot(str)
    def log_action(self, message: str):
        """Logga un'azione nella finestra dei log."""
        print(f"Logging message: {message}")
        self.log_widget.append(message)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Pulsante per caricare gli scontrini
        self.load_button = QPushButton("Carica Scontrini")
        self.load_button.setMinimumHeight(40)
        self.load_button.clicked.connect(self.load_receipts)
        layout.addWidget(self.load_button)

        # Status Label
        self.status_label = QLabel("Pronto")
        layout.addWidget(self.status_label)

        # Tabella risultati
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Data", "Importo", "Valuta",
            "Importo (EUR)", "Descrizione", "File"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        # Widget per i log degli agenti
        self.log_widget = QTextEdit(self)
        self.log_widget.setReadOnly(True)



        layout.addWidget(self.log_widget)
        # Pulsante esportazione
        self.export_button = QPushButton("Esporta PDF")
        self.export_button.setMinimumHeight(40)
        self.export_button.clicked.connect(self.export_to_pdf)
        layout.addWidget(self.export_button)

        # Pulsante aggiorna Excel
        self.excel_button = QPushButton("Aggiorna Excel")
        self.excel_button.setMinimumHeight(40)
        self.excel_button.clicked.connect(self.save_to_excel)
        layout.addWidget(self.excel_button)

    def analyze_expenses(self):
        """Analisi completa delle spese usando ExpenseAnalysisAgent."""
        try:
            report_dir = os.path.join(os.getcwd(), "Reports")
            excel_file_path = os.path.join(report_dir, "pagamenti.xlsx")

            # Crea e utilizza l'agente di analisi delle spese
            expense_agent = ExpenseAnalysisAgent(excel_file_path)

            # Ottieni l'analisi delle spese
            analysis_result = expense_agent.analyze_expenses()

            # Aggiorna l'interfaccia con i risultati
            self.status_label.setText(analysis_result)
            self.log_action(f"Analisi spese completata: {analysis_result}")

            # Aggiorna il widget di log con informazioni dettagliate
            if os.path.exists(excel_file_path):
                df = pd.read_excel(excel_file_path)
                total_spent = df['Importo (EUR)'].sum()
                num_transactions = len(df)
                self.log_action(f"Totale spese: {total_spent:.2f} EUR")
                self.log_action(f"Numero totale transazioni: {num_transactions}")

        except Exception as e:
            self.handle_error(f"Errore nell'analisi delle spese: {str(e)}")

    def process_and_move_file(self, original_path: str) -> str:
        """
        Processa il file, controlla duplicati e ottimizza l'immagine.
        """
        try:
            # Controlla se è un duplicato usando FileAgent
            if self.file_agent.is_duplicate(original_path):
                self.log_action(f"File duplicato rilevato: {original_path}")
                return None

            # Ottimizza l'immagine usando OCRAgent
            optimized_path = self.ocr_agent.optimize_image(original_path)
            self.log_action(f"Immagine ottimizzata: {optimized_path}")

            # Ottieni la data di creazione del file
            creation_time = os.path.getctime(optimized_path)
            date_str = time.strftime('%Y%m%d_%H%M%S', time.localtime(creation_time))

            # Crea il nuovo nome file
            file_ext = os.path.splitext(optimized_path)[1].lower()
            new_filename = f"Scontrino_{date_str}{file_ext}"
            new_path = os.path.join(WATCH_DIR, new_filename)

            # Sposta il file
            import shutil
            shutil.copy2(optimized_path, new_path)

            # Pulisci i file temporanei se necessario
            if optimized_path != original_path:
                os.remove(optimized_path)

            return new_path

        except Exception as e:
            self.handle_error(f"Errore nel processamento del file: {str(e)}")
            return original_path

    def update_table(self):
        """Aggiorna la tabella UI con i dati correnti e formattazione corretta dei numeri."""
        try:
            self.table.setRowCount(len(self.data))
            for row, item in enumerate(self.data):
                # Data
                self.table.setItem(row, 0, QTableWidgetItem(str(item["Data"])))

                # Importo originale
                try:
                    importo = float(item["Importo"])
                    importo_str = f"{importo:.3f}" if importo % 1 != 0 else f"{int(importo)}"
                    self.table.setItem(row, 1, QTableWidgetItem(importo_str))
                except (ValueError, TypeError):
                    self.table.setItem(row, 1, QTableWidgetItem("0.000"))

                # Valuta
                self.table.setItem(row, 2, QTableWidgetItem(item["Valuta"]))

                # Importo EUR
                try:
                    importo_eur = float(item["Importo (EUR)"])
                    importo_eur_str = f"{importo_eur:.3f}" if importo_eur % 1 != 0 else f"{int(importo_eur)}"
                    self.table.setItem(row, 3, QTableWidgetItem(importo_eur_str))
                except (ValueError, TypeError):
                    self.table.setItem(row, 3, QTableWidgetItem("0.000"))

                # Descrizione e File
                self.table.setItem(row, 4, QTableWidgetItem(item["Descrizione"]))
                self.table.setItem(row, 5, QTableWidgetItem(item["File"]))

        except Exception as e:
            self.handle_error(f"Errore nell'aggiornamento della tabella: {str(e)}")

    def convert_to_eur(self, amount: float, currency: str = "OMR") -> float:
        """Converte l'importo in EUR usando tassi di conversione predefiniti."""
        try:
            # Mappa dei tassi di conversione (da aggiornare periodicamente)
            conversion_rates = {
                "OMR": 2.42,  # 1 OMR = 2.42 EUR
                "RO": 2.42,  # RO è un alias per OMR
                "AED": 0.25,  # 1 AED = 0.25 EUR
                "USD": 0.92,  # 1 USD = 0.92 EUR
            }

            # Standardizza il codice valuta
            currency = currency.upper().replace("RIAL", "OMR")

            # Ottieni il tasso di conversione
            rate = conversion_rates.get(currency, 1)  # Default a 1 se valuta non trovata

            # Assicurati che amount sia un float
            amount = float(str(amount).replace(',', '.')) if isinstance(amount, str) else float(amount)

            converted = amount * rate
            return round(converted, 3)

        except Exception as e:
            self.handle_error(f"Errore nella conversione valuta: {str(e)}")
            return 0.000  # Ritorna zero in caso di errore

    def load_receipts(self):
        """Gestisce il caricamento degli scontrini con controllo duplicati e ottimizzazione."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Seleziona Scontrini",
            os.path.expanduser("~"),
            "Immagini (*.png *.jpg *.jpeg);;Tutti i file (*.*)"
        )

        if not files:
            return

        self.status_label.setText("Elaborazione in corso...")

        for file_path in files:
            # Processa e sposta il file
            processed_path = self.process_and_move_file(file_path)
            if processed_path is None:
                continue  # Salta i duplicati

            # Crea e configura il worker per l'analisi
            worker = ProcessingWorker(self)
            worker.setup(processed_path, self.receipt_analysis_chain)

            worker.finished.connect(lambda data, fp=processed_path: self.handle_results(data, fp))
            worker.error.connect(self.handle_error)
            worker.progress.connect(lambda msg: self.status_label.setText(msg))
            worker.log_message.connect(self.log_action)

            worker.start()

    def handle_results(self, data: dict, file_path: str):
        """Versione sincrona di handle_results con correzione parsing dati"""
        try:
            # Estrai i dati dal JSON, gestendo nomi di campo diversi
            raw_date = data.get("data") or data.get("date", "N/A")

            # Formatta la data con l'agente
            try:
                formatted_date = self.date_formatter.format_date(raw_date)
                self.log_action(f"Data formattata: {formatted_date}")
            except Exception as e:
                self.log_action(f"Errore nella formattazione della data: {str(e)}")
                formatted_date = raw_date

            # Standardizza la valuta
            valuta = data.get("valuta", "").upper().replace("RO", "OMR")

            # Gestione corretta dei numeri
            try:
                importo = data.get("importo") or data.get("importo_totale", 0)
                if isinstance(importo, str):
                    importo = float(importo.replace(',', '.'))
                else:
                    importo = float(importo)
                importo_eur = self.convert_to_eur(importo, valuta)
            except (ValueError, TypeError) as e:
                self.log_action(f"Errore nella conversione dell'importo: {str(e)}")
                importo = 0.000
                importo_eur = 0.000

            # Gestione della descrizione
            esercente = data.get("esercente") or data.get("nome_esercente", "")
            luogo = data.get("luogo") or data.get("localita", "")
            descrizione = f"{esercente}"
            if luogo:
                descrizione += f" - {luogo}"
            descrizione = descrizione.strip(" -")

            # Crea una singola riga per questo scontrino
            row_data = {
                "Data": formatted_date,
                "Importo": importo,
                "Valuta": valuta,
                "Importo (EUR)": importo_eur,
                "Descrizione": descrizione,
                "File": os.path.basename(file_path)
            }

            self.log_action(f"Dati processati: {row_data}")
            self.data.append(row_data)

            # Aggiorna la tabella e salva in Excel
            self.update_table()
            self.save_to_excel()
            self.status_label.setText(f"Elaborazione completata per {os.path.basename(file_path)}")
        except Exception as e:
            self.handle_error(f"Errore nell'elaborazione dei risultati: {str(e)}")

        self.analyze_expenses()

    def handle_error(self, error_msg: str):
        self.status_label.setText(f"Errore: {error_msg}")
        print(f"Errore: {error_msg}")

    def save_to_excel(self):
        """Salva i dati in un file Excel."""
        try:
            # Crea la cartella Reports se non esiste
            reports_dir = os.path.join(os.getcwd(), "Reports")
            os.makedirs(reports_dir, exist_ok=True)
            excel_path = os.path.join(reports_dir, EXCEL_FILE)

            # Prepara i dati per l'Excel
            formatted_data = []
            for item in self.data:
                # Converti esplicitamente i valori numerici
                try:
                    importo_originale = float(str(item['Importo']).replace(',', '.'))
                    importo_eur = float(str(item['Importo (EUR)']).replace(',', '.'))
                except ValueError as e:
                    self.logger.log_action(f"Errore nella conversione dell'importo: {str(e)}")
                    importo_originale = 0.0
                    importo_eur = 0.0

                formatted_item = {
                    'Data': item['Data'],
                    'Importo Originale': importo_originale,
                    'Valuta': item['Valuta'],
                    'Importo (EUR)': importo_eur,
                    'Descrizione': item['Descrizione'],
                    'Categoria': item.get('categoria', 'Altro'),
                    'File': item['File'],
                    'Percorso Completo': os.path.join(WATCH_DIR, item['File'])
                }
                formatted_data.append(formatted_item)

            # Crea un DataFrame con i dati
            df = pd.DataFrame(formatted_data)

            # Se il file esiste, carica i dati esistenti e aggiungi i nuovi
            if os.path.exists(excel_path):
                existing_df = pd.read_excel(excel_path)
                # Converti le colonne numeriche in float
                existing_df['Importo Originale'] = pd.to_numeric(existing_df['Importo Originale'], errors='coerce')
                existing_df['Importo (EUR)'] = pd.to_numeric(existing_df['Importo (EUR)'], errors='coerce')

                # Rimuovi eventuali duplicati
                combined_df = pd.concat([existing_df, df])
                combined_df = combined_df.drop_duplicates(
                    subset=['Data', 'Importo Originale', 'Descrizione'],
                    keep='last'
                )
                df = combined_df

            # Formatta il DataFrame
            writer = pd.ExcelWriter(excel_path, engine='xlsxwriter')
            df.to_excel(writer, index=False, sheet_name='Scontrini')

            # Ottieni il foglio di lavoro
            workbook = writer.book
            worksheet = writer.sheets['Scontrini']

            # Definisci i formati
            money_format = workbook.add_format({'num_format': '#,##0.00'})
            date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})

            # Imposta la larghezza delle colonne e i formati
            worksheet.set_column('A:A', 15, date_format)  # Data
            worksheet.set_column('B:B', 15, money_format)  # Importo Originale
            worksheet.set_column('C:C', 10)  # Valuta
            worksheet.set_column('D:D', 15, money_format)  # Importo (EUR)
            worksheet.set_column('E:E', 40)  # Descrizione
            worksheet.set_column('F:F', 20)  # Categoria
            worksheet.set_column('G:G', 30)  # File
            worksheet.set_column('H:H', 50)  # Percorso Completo

            # Salva il file
            writer.close()

            self.status_label.setText(f"Dati salvati in: {excel_path}")

        except Exception as e:
            self.status_label.setText(f"Errore nel salvataggio Excel: {str(e)}")
            print(f"Errore nel salvataggio Excel: {str(e)}")
            import traceback
            traceback.print_exc()

    def export_to_pdf(self):
        """Esporta i dati in PDF con supporto Unicode usando FPDF2."""
        from fpdf import FPDF
        import arabic_reshaper
        from bidi.algorithm import get_display

        class PDF(FPDF):
            def __init__(self):
                super().__init__(orientation='L', unit='mm', format='A4')
                self.col_widths = {
                    "Data": 25,
                    "Importo": 25,
                    "Valuta": 15,
                    "EUR": 25,
                    "Descrizione": 95,
                    "Categoria": 35,
                    "File": 50
                }
                # Imposta il font predefinito
                self.add_font("NotoSans", fname="fonts/NotoSans-Regular.ttf")
                self.add_font("NotoSans", fname="fonts/NotoSans-Bold.ttf", style="B")
                self.set_auto_page_break(auto=True, margin=15)

            def header(self):
                self.set_font("NotoSans", "B", 16)
                self.cell(0, 10, "Report Scontrini", align="C")
                self.ln()
                self.set_font("NotoSans", size=10)
                self.cell(0, 5, f"Generato il: {time.strftime('%d/%m/%Y %H:%M:%S')}", align="R")
                self.ln(10)

                # Intestazione tabella
                self.set_font("NotoSans", "B", 10)
                self.set_fill_color(230, 230, 230)
                x_pos = 10
                for header, width in self.col_widths.items():
                    self.rect(x_pos, self.get_y(), width, 8, "DF")
                    self.set_xy(x_pos, self.get_y())
                    self.cell(width, 8, header, align="C")
                    x_pos += width
                self.ln(8)

            def footer(self):
                self.set_y(-15)
                self.set_font("NotoSans", size=8)
                self.cell(0, 10, f'Pagina {self.page_no()}', align="C")

            def add_row(self, data):
                self.set_font("NotoSans", size=9)

                # Calcola l'altezza necessaria
                max_height = 6
                desc_lines = []

                def process_text(text):
                    try:
                        text = arabic_reshaper.reshape(str(text))
                        text = get_display(text)
                        return text
                    except:
                        return str(text)

                # Prepara il testo della descrizione
                if "Descrizione" in data:
                    desc_text = process_text(data["Descrizione"])
                    desc_lines = self.multi_cell_planning(desc_text,
                                                          self.col_widths["Descrizione"] - 2)
                    max_height = max(len(desc_lines) * 6, max_height)

                # Stampa le celle
                x_start = 10
                y_start = self.get_y()
                cell_height = max_height

                for key, width in self.col_widths.items():
                    self.set_xy(x_start, y_start)
                    content = str(data.get(key, ""))

                    if key in ["Descrizione", "File"]:
                        content = process_text(content)
                        lines = self.multi_cell_planning(content, width - 2)
                        for i, line in enumerate(lines):
                            self.set_xy(x_start, y_start + (i * 6))
                            self.cell(width, 6, line, border=1, align="L")
                    else:
                        self.cell(width, cell_height, process_text(content),
                                  border=1, align="C")
                    x_start += width

                self.ln(cell_height)

            def multi_cell_planning(self, text, width):
                lines = []
                running_line = ""
                words = text.split()

                for word in words:
                    test_line = f"{running_line} {word}".strip()
                    if self.get_string_width(test_line) <= width:
                        running_line = test_line
                    else:
                        if running_line:
                            lines.append(running_line)
                        running_line = word

                if running_line:
                    lines.append(running_line)

                return lines if lines else [text]

        try:
            # Verifica se la cartella fonts esiste, altrimenti creala
            if not os.path.exists('fonts'):
                os.makedirs('fonts')

            # Verifica se il font è presente, altrimenti scaricalo
            font_path = "fonts/NotoSans-Regular.ttf"
            bold_font_path = "fonts/NotoSans-Bold.ttf"

            if not (os.path.exists(font_path) and os.path.exists(bold_font_path)):
                self.status_label.setText("Scaricamento font in corso...")
                import urllib.request

                # URLs per i font Noto Sans (questi sono esempi, usa URLs corrette)
                font_url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf"
                bold_font_url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Bold.ttf"

                urllib.request.urlretrieve(font_url, font_path)
                urllib.request.urlretrieve(bold_font_url, bold_font_path)

                self.status_label.setText("Font scaricati con successo")

            # Leggi i dati e prepara il PDF
            data = self.read_excel_data()
            self.data = self.prepare_data(data)

            pdf = PDF()
            pdf.add_page()

            # Aggiungi le righe
            for item in self.data:
                if pdf.get_y() > 180:
                    pdf.add_page()

                row_data = {
                    "Data": str(item.get("Data", "")),
                    "Importo": f"{float(item.get('Importo Originale', 0)):.3f}",
                    "Valuta": str(item.get("Valuta", "")),
                    "EUR": f"{float(item.get('Importo (EUR)', 0)):.2f}",
                    "Descrizione": str(item.get("Descrizione", "")),
                    "Categoria": str(item.get("Categoria", "Non specificata")),
                    "File": str(item.get("File", ""))
                }
                pdf.add_row(row_data)

            # Aggiungi riepilogo
            pdf.add_page()
            pdf.set_font("NotoSans", "B", 12)
            pdf.cell(0, 10, "Riepilogo", align="L")
            pdf.ln()

            total_eur = sum(float(item.get("Importo (EUR)", 0)) for item in self.data)
            pdf.set_font("NotoSans", size=10)
            pdf.cell(0, 8, f"Totale spese: {total_eur:.2f} EUR", align="L")
            pdf.ln()
            pdf.cell(0, 8, f"Numero scontrini elaborati: {len(self.data)}", align="L")
            pdf.ln()

            # Salva il PDF
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            pdf_filename = f"report_scontrini_{timestamp}.pdf"
            pdf_path = os.path.join("Reports", pdf_filename)
            pdf.output(pdf_path)

            self.status_label.setText(f"PDF esportato con successo: {pdf_filename}")

        except Exception as e:
            self.status_label.setText(f"Errore nell'esportazione PDF: {str(e)}")
            print(f"Errore nell'esportazione PDF: {str(e)}")
            import traceback
            traceback.print_exc()

    def read_excel_data(self):
        try:
            # Costruisci il percorso assoluto al file Excel
            report_dir = os.path.join(os.getcwd(), "Reports")
            excel_file_path = os.path.join(report_dir, "pagamenti.xlsx")

            # Leggi i dati dall'Excel
            df = pd.read_excel(excel_file_path)

            # Rimuove gli spazi dai nomi delle colonne
            df.columns = df.columns.str.strip()

            # Gestisce valori nulli riempiendoli con stringa vuota
            df.fillna("", inplace=True)

            # Converti il DataFrame in una lista di dizionari
            return df.to_dict(orient="records")
        except Exception as e:
            print(f"Errore nella lettura del file Excel: {str(e)}")
            return []

    def prepare_data(self, data):
        prepared_data = []
        for item in data:
            try:
                # Formatta la data
                date_str = self.date_formatter.format_date(item.get("Data", ""))

                # Assicurati che tutti i campi necessari esistano
                prepared_item = {
                    "Data": date_str,
                    "Importo Originale": float(item.get("Importo Originale", 0)),
                    "Valuta": str(item.get("Valuta", "")),
                    "Importo (EUR)": float(item.get("Importo (EUR)", 0)),
                    "Descrizione": str(item.get("Descrizione", "")),
                    "Categoria": str(item.get("Categoria", "Non specificata")),
                    "File": str(item.get("File", "")),
                    "Percorso Completo": str(item.get("Percorso Completo", ""))
                }
                prepared_data.append(prepared_item)
            except Exception as e:
                print(f"Errore nella preparazione dei dati per la riga: {item}")
                print(f"Errore specifico: {str(e)}")
        return prepared_data

    def start_watching(self):
        self.observer = Observer()
        handler = ReceiptWatcher(self)
        self.observer.schedule(handler, WATCH_DIR, recursive=False)
        self.observer.start()

    def closeEvent(self, event):
        """Handle cleanup when closing the window."""
        try:
            self.observer.stop()
            self.observer.join()
            for worker in self.current_workers:
                worker.wait()
        except:
            pass
        super().closeEvent(event)


class ReceiptWatcher(FileSystemEventHandler):
    def __init__(self, processor):
        self.processor = processor

    def on_created(self, event):
        if not event.is_directory:
            worker = ProcessingWorker(event.src_path)
            worker.finished.connect(lambda data: self.processor.handle_results(data, event.src_path))
            worker.error.connect(self.processor.handle_error)
            worker.progress.connect(lambda msg: self.processor.status_label.setText(msg))

            self.processor.current_workers.append(worker)
            worker.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ReceiptProcessor()
    window.show()

    sys.exit(app.exec_())