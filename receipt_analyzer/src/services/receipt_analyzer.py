"""
Automatically generated file from migration script.
"""


from receipt_analyzer.src.workers.processing import ProcessingWorker


class ReceiptAnalysisChain:
    def __init__(self, processor):
        self.logger = processor
        api_openai = ProcessingWorker().load_or_get_api_key(self)

        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        self.llm = ChatOpenAI(
            temperature=0,
            api_key=api_openai,
            model="gpt-4o-mini"
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
