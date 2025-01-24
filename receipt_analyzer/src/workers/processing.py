"""
Automatically generated file from migration script.
"""

import os
import json
import asyncio
import base64
from typing import Dict, Any, Optional, Tuple
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QInputDialog, QMessageBox, QLineEdit
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
        self.api_key_openai = self.load_or_get_api_key(parent)
        self.client = openai.OpenAI(api_key=self.api_key_openai)

    def setup(self, image_path: str, analysis_chain) -> 'ProcessingWorker':
        self.image_path = image_path
        self.analysis_chain = analysis_chain
        return self

    async def process_chains(self, text_content: str) -> Dict[str, Any]:
        """Gestisce l'intero processo di analisi dello scontrino"""
        try:
            # Analisi iniziale
            self.log_message.emit("1. Primo Step: Iniziando l'analisi con la catena principale...")
            analysis_result = await self.analysis_chain.analysis_chain.ainvoke({"text": text_content})
            analysis_data = self.parse_json_result(analysis_result)
            self.log_message.emit(f"Questo è cio che è stato estratto: {json.dumps(analysis_data, ensure_ascii=False)}\n")
            self.log_message.emit(f"Proviamo a Validare...\n")

            # Validazione
            self.log_message.emit("\n2. Secondo Step: Validazione in corso...")
            validation_result = await self.analysis_chain.validation_chain.ainvoke(
                {"json": json.dumps(analysis_data)}
            )
            validation_data = self.parse_json_result(validation_result)
            #self.log_message.emit(f"Risultato validazione: {json.dumps(validation_data, ensure_ascii=False)}\n")

            self.log_message.emit(f"Procediamo a convertire la valuta...\n")

            # Conversione valuta
            self.log_message.emit("\n3. Terzo Step: Sto convertendo...")
            analysis_data = await self.handle_currency_conversion(analysis_data)
            if analysis_data:


                self.log_message.emit(f"Procediamo con la categorizzazione...\n")

            # Categorizzazione
            self.log_message.emit("\n4. Quarto step: Categorizzazione della spesa...")
            categorization_result = await self.analysis_chain.categorize_with_intermediate_steps(
                analysis_data,
                self
            )
            #self.log_message.emit(
                #f"Risultato categorizzazione: {json.dumps(categorization_result, ensure_ascii=False)}")

            return {
                **analysis_data,
                "validation": validation_data,
                "categorization": categorization_result
            }

        except Exception as e:
            self.log_message.emit(f"Errore nel processo delle catene: {str(e)}")
            raise

    def parse_json_result(self, result: str) -> Dict[str, Any]:
        """Gestisce il parsing del JSON con gestione errori migliorata"""
        try:
            if isinstance(result, dict):
                return result

            cleaned = self.clean_json_string(result)
            return json.loads(cleaned)

        except json.JSONDecodeError:
            return self.extract_json_from_string(result)

    def clean_json_string(self, text: str) -> str:
        """Pulisce una stringa JSON da markup e caratteri non necessari"""
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return cleaned.strip()

    def extract_json_from_string(self, text: str) -> Dict[str, Any]:
        """Estrae JSON da una stringa con gestione errori"""
        json_start = text.find('{')
        json_end = text.rfind('}') + 1

        if json_start >= 0 and json_end > json_start:
            try:
                return json.loads(text[json_start:json_end])
            except json.JSONDecodeError:
                raise ValueError("JSON non valido nel testo estratto")
        raise ValueError("Nessun JSON trovato nel testo")

    async def handle_currency_conversion(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Gestisce la conversione della valuta con fallback multipli"""
        if not ('valuta' in data and 'importo' in data):
            return data

        currency = data['valuta']
        amount = float(data['importo'])
        self.log_message.emit(f"Valuta originale: {currency}, Importo: {amount}")

        try:
            rate, source = await self.get_conversion_rate(currency)
            if rate:
                data['importo_eur'] = round(amount * rate, 2)
                self.log_message.emit(
                    f"Conversione: {amount} {currency} = {data['importo_eur']} EUR (Fonte: {source})"
                )
            else:
                data['importo_eur'] = amount
                self.log_message.emit("Conversione non possibile, uso importo originale")

        except Exception as e:
            self.log_message.emit(f"Errore conversione: {str(e)}")
            data['importo_eur'] = amount

        return data

    async def get_conversion_rate(self, currency: str) -> Tuple[Optional[float], Optional[str]]:
        """Ottiene il tasso di conversione provando diversi servizi"""
        services = [
            (self.parent().currency_conversion_manager.try_exchangerate_api, "ExchangeRate API"),
            (self.parent().currency_conversion_manager.try_forex_python, "Forex Python"),
            (lambda c, t: (self.parent().currency_conversion_manager.try_fixer_io(c, t), "Fixer.io")),
            (lambda c, t: (self.parent().currency_conversion_manager.get_fallback_rate(c, t), "Fallback"))
        ]

        for service, name in services:
            try:
                rate = await service(currency, 'EUR') if asyncio.iscoroutinefunction(service) else service(currency,
                                                                                                           'EUR')
                if isinstance(rate, tuple):
                    rate, _ = rate
                if rate:
                    return rate, name
            except Exception as e:
                self.log_message.emit(f"Errore con {name}: {str(e)}")

        return None, None

    def run(self):
        """Esegue il processo principale di analisi"""
        try:
            self.log_message.emit("Avvio analisi scontrino...")

            image_base64 = self.encode_image()
            analysis_text = self.extract_text_from_image(image_base64)
            self.log_message.emit(f"Testo estratto: {analysis_text}")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                data = loop.run_until_complete(self.process_chains(analysis_text))
                self.log_message.emit("Processo completato con successo")
                self.finished.emit(data)
            finally:
                loop.close()

        except Exception as e:
            error_msg = f"Errore elaborazione: {str(e)}"
            self.log_message.emit(error_msg)
            self.error.emit(error_msg)

    def encode_image(self) -> str:
        """Codifica l'immagine in base64"""
        with open(self.image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def extract_text_from_image(self, image_base64: str) -> str:
        """Estrae il testo dall'immagine usando GPT-4 Vision"""
        completion = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [{
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
                }, {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                }]
            }],
            max_tokens=1000
        )
        return completion.choices[0].message.content.strip()

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

