"""
Automatically generated file from migration script.
"""


import os

import json

from PyQt5.QtWidgets import ( QInputDialog, QMessageBox, QLineEdit)

import asyncio
import base64
from PyQt5.QtCore import QThread, pyqtSignal
import openai


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

