"""
Automatically generated file from migration script.
"""

import json
import re
from typing import Dict, Any
from PyQt5.QtWidgets import QInputDialog
from aiohttp import ClientSession
from receipt_analyzer.src.workers.processing import ProcessingWorker

class ReceiptAnalysisChain:
    """
            Questa classe integra varie funzionalità di elaborazione utilizzando un bastone LLM
            Pipeline per l'analisi del testo. Le catene implementate sono progettate per la ricezione
            Attività di analisi, validazione e categorizzazione. I suggerimenti usano strutturati
            Modelli per garantire formati di output coerenti in JSON. Questo facilita il
            elaborazione e validazione di dati testuali estratti in modo efficiente, eseguiti in
            Collaborazione con il modello GPT-4.0 di Openi. Ogni catena inizia con un suggerimento
            Il modello, passa attraverso l'LLM e analizza il risultato in formati strutturati.
    """

    def __init__(self, processor):

        self.logger = processor.log_signal.emit
        
        api_openai = ProcessingWorker().load_or_get_api_key(self)

        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        self.llm = ChatOpenAI(
            temperature=0,
            api_key = api_openai,
            model="gpt-4o",
            streaming=True
        )

        output_parser = StrOutputParser()

        # Template per l'analisi dello scontrino
        self.analysis_prompt = ChatPromptTemplate.from_template("""
            Analizza il seguente testo estratto da uno scontrino e restituisci un JSON con questa struttura esatta:
            {{
                "data": "YYYY-MM-DD",
                "importo": number,
                "valuta": "codice valuta a 3 lettere",
                "esercente": "nome dell'esercente",
                "luogo": "località"
            }}

            Non includere commenti o spiegazioni, solo il JSON.

            Testo da analizzare: {text}
        """)
        self.analysis_chain = self.analysis_prompt | self.llm | output_parser

        # Template per la validazione
        self.validation_prompt = ChatPromptTemplate.from_template("""
            Verifica i seguenti dati e restituisci un JSON con questa struttura esatta:
            {{
                "data_valida": boolean,
                "importo_valido": boolean,
                "valuta_valida": boolean,
                "correzioni": {{
                    "data": "YYYY-MM-DD oppure null se non serve correzione",
                    "importo": number oppure null se non serve correzione,
                    "valuta": "codice valuta oppure null se non serve correzione"
                }},
                "messaggi": ["lista di messaggi sulle correzioni necessarie"]
            }}

            Non includere commenti o spiegazioni, solo il JSON.

            Dati da validare: {json}
        """)
        self.validation_chain = self.validation_prompt | self.llm | output_parser

        # Template per la categorizzazione
        self.categorization_prompt = ChatPromptTemplate.from_template("""
            Analizza questa descrizione e restituisci un JSON con questa struttura esatta:
            {{
                "categoria": "una tra: Cibo e Ristorazione, Trasporti, Shopping, Servizi, Altro",
                "confidenza": number,
                "sottocategoria": "descrizione più specifica",
                "tags": ["lista", "di", "parole", "chiave"]
            }}

            Non includere commenti o spiegazioni, solo il JSON.

            Descrizione da analizzare: {description}
        """)
        self.categorization_chain = self.categorization_prompt | self.llm | output_parser

    def get_conversion_info(self, currency: str) -> dict:
        """Ottiene informazioni sulla conversione utilizzata."""
        return {
            "valuta": currency,
            "tasso": getattr(self, 'current_rate', None),
            "fonte": getattr(self, 'rate_source', None),
            "timestamp": getattr(self, 'rate_timestamp', None)
        }

    @staticmethod
    def validate_esercente_and_luogo(esercente: str, luogo: str) -> bool:
        """
        Verifica se le informazioni su esercente e luogo sono sufficienti.

        Args:
            esercente (str): Nome dell'esercente.
            luogo (str): Località o indirizzo.

        Returns:
            bool: True se sufficienti, False altrimenti.
        """
        return bool(
            esercente and luogo and esercente != "Esercente sconosciuto" and luogo != "Località sconosciuta")

    async def search_online_information(self, luogo: str) -> str:
        """
        Cerca informazioni con gestione degli errori migliorata.
        """
        if not luogo or not isinstance(luogo, str):
            self.logger("Luogo non valido")
            return "Generico"

        try:
            async with ClientSession() as session:
                url = f"https://nominatim.openstreetmap.org/search"
                params = {
                    "format": "json",
                    "q": luogo,
                    "limit": 1
                }

                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        self.logger(f"API call failed with status {response.status}")
                        return "Generico"

                    data = await response.json()

                    if not data:
                        return "Generico"

                    return data[0].get("display_name", "Generico")

        except Exception as e:
            self.logger(f"Error in online search: {str(e)}")
            return "Generico"

    async def process_intermediate_steps(self, analysis_result: Dict[str, Any], parent_widget=None) -> Dict[str, Any]:
        """Esegue gli step intermedi per l'analisi della categoria."""
        try:
            if not isinstance(analysis_result, dict):
                raise ValueError("analysis_result deve essere un dizionario")

            esercente = analysis_result.get("esercente", "Esercente sconosciuto")
            luogo = analysis_result.get("luogo", "Località sconosciuta")

            # Step 1: Validazione base
            if self.validate_esercente_and_luogo(esercente, luogo):
                self.logger(f"Categoria validata: {esercente}")
                return analysis_result
            else:
                self.logger("Categoria non valida, procedo con gli step intermedi...")

            # Step 2: Ricerca online
            self.logger("Provo a cercare la categoria online...")
            category_hint = await self.search_online_information(luogo)

            if category_hint != "Generico":
                analysis_result["esercente"] = f"{esercente} ({category_hint})"
                self.logger(f"Categoria trovata online: {analysis_result['esercente']}")
                return analysis_result
            else:
                self.logger("Nessuna categoria trovata online, procedo con lo step successivo...")

            # Step 3: Input manuale
            self.logger("Ti tocca inserirlo manualmente")
            if parent_widget:
                self.logger("Richiesta input manuale per categoria...")
                manual_category = self.ask_user_for_category(parent_widget)
                analysis_result["esercente"] = f"{esercente} ({manual_category})"
                self.logger(f"Categoria inserita manualmente: {analysis_result['esercente']}")

            return analysis_result

        except Exception as e:
            self.logger(f"Errore processo categorizzazione: {str(e)}")
            raise

    async def categorize_with_intermediate_steps(self, analysis_result, parent_widget=None):
        """
        Esegue la categorizzazione con step intermedi per verificare e arricchire i dati.

        Args:
            analysis_result (dict): Dati analizzati contenenti esercente, luogo, importo e valuta.
            parent_widget: Widget genitore per dialoghi (se necessario).

        Returns:
            dict: Risultato della categorizzazione con i dettagli aggiuntivi.
        """
        # Passa attraverso gli step intermedi
        enriched_result = await self.process_intermediate_steps(analysis_result, parent_widget)

        # Crea la descrizione categorizzata
        esercente = enriched_result.get("esercente", "Esercente sconosciuto")
        luogo = enriched_result.get("luogo", "Località sconosciuta")
        importo = enriched_result.get("importo", 0)
        valuta = enriched_result.get("valuta", "EUR")

        description = f"{esercente} situato a {luogo}. Importo: {importo} {valuta}."

        # Passa la descrizione alla catena di categorizzazione
        category_result_raw = await self.categorization_chain.ainvoke({"description": description})

        # Pulisci la stringa JSON
        self.logger(f"Risultato categorizzazione (raw): {category_result_raw}")
        category_result_cleaned = self.clean_json_string(category_result_raw)

        # Effettua il parsing del JSON pulito
        try:
            category_result = json.loads(category_result_cleaned)
        except json.JSONDecodeError as e:
            self.logger(f"Errore nel parsing del JSON pulito: {str(e)}")
            raise ValueError("Errore durante il parsing della categorizzazione.")

        return {
            "descrizione": description,
            "categoria": category_result
        }

    def ask_user_for_category(self, parent_widget=None) -> str:
        """
        Richiede input utente con validazione.
        """
        try:
            if parent_widget is None:
                return "Generico"

            category, ok = QInputDialog.getText(
                parent_widget,
                "Inserisci Categoria",
                "Non è stato possibile identificare la categoria. Inseriscila manualmente:"
            )

            return category.strip() if ok and category.strip() else "Generico"

        except Exception as e:
            self.logger(f"Error in ask_user_for_category: {str(e)}")
            return "Generico"

    def clean_json_string(self, json_string: str) -> str:
        """Enhanced JSON cleaning with markdown code block handling"""
        try:
            # Remove markdown code blocks
            cleaned = re.sub(r"```json\n|\n```", "", json_string).strip()
            # Parse and re-stringify to ensure valid JSON
            parsed = json.loads(cleaned)
            return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError as e:
            self.logger(f"JSON cleaning error: {str(e)}, Input: {json_string}")
            raise ValueError(f"Invalid JSON after cleaning: {str(e)}")