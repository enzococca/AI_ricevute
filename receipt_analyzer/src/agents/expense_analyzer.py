"""
Automatically generated file from migration script.
"""


import pandas as pd


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

