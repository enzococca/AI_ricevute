"""
Automatically generated file from migration script.
"""

import time
import json

from watchdog.observers import Observer

import pandas as pd

from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QFileDialog, QLabel, QHeaderView, QWidget, QTextEdit)
from PyQt5.QtCore import pyqtSignal, pyqtSlot


from ..agents.expense_analyzer import ExpenseAnalysisAgent
from ..services.receipt_watcher import ReceiptWatcher
from ..workers.processing import ProcessingWorker
from ..agents.date_formatter import DateFormatterAgent
from ..models.currency_manager import CurrencyConversionManager
from ..services.receipt_analyzer import ReceiptAnalysisChain
from ..agents.file_agent import FileAgent
from ..agents.ocr_agent import OCRAgent
from ..utils.config import *


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
        self.receipt_analysis_chain = ReceiptAnalysisChain(self)

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
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Data", "Importo", "Valuta",
            "Importo (EUR)", "Descrizione","Categoria","Sottocategoria",
            "File"
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
        try:
            self.table.setRowCount(len(self.data))
            for row, item in enumerate(self.data):
                self.table.setItem(row, 0, QTableWidgetItem(str(item["Data"])))
                self.table.setItem(row, 1, QTableWidgetItem(f"{float(item['Importo']):.3f}"))
                self.table.setItem(row, 2, QTableWidgetItem(item["Valuta"]))
                self.table.setItem(row, 3, QTableWidgetItem(f"{float(item['Importo (EUR)']):.3f}"))
                self.table.setItem(row, 4, QTableWidgetItem(item["Descrizione"]))
                self.table.setItem(row, 5, QTableWidgetItem(item["Categoria"]))
                self.table.setItem(row, 6, QTableWidgetItem(item["Sottocategoria"]))
                self.table.setItem(row, 7, QTableWidgetItem(item["File"]))

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
        try:
            if isinstance(data, str):
                data = json.loads(data)

            # Estrazione dati base
            raw_date = data.get("data") or data.get("date", "N/A")
            formatted_date = self.date_formatter.format_date(raw_date)
            valuta = data.get("valuta", "").upper().replace("RO", "OMR")

            # Gestione importi
            try:
                importo = float(str(data.get("importo", 0)).replace(',', '.'))
                importo_eur = self.convert_to_eur(importo, valuta)
            except (ValueError, TypeError):
                importo = 0.000
                importo_eur = 0.000

            # Gestione esercente e luogo
            esercente = data.get("esercente", "")
            luogo = data.get("luogo", "")
            descrizione = f"{esercente} - {luogo}".strip(" -")

            # Estrazione categoria e sottocategoria
            categoria = "Altro"
            sottocategoria = ""
            if "categorization" in data and isinstance(data["categorization"], dict):
                cat_data = data["categorization"].get("categoria", {})
                if isinstance(cat_data, dict):
                    categoria = cat_data.get("categoria", "Altro")
                    sottocategoria = cat_data.get("sottocategoria", "")

            # Preparazione dati riga
            row_data = {
                "Data": formatted_date,
                "Importo": importo,
                "Valuta": valuta,
                "Importo (EUR)": importo_eur,
                "Descrizione": descrizione,
                "Categoria": categoria,
                "Sottocategoria": sottocategoria,
                "File": os.path.basename(file_path)
            }

            self.log_action(f"Dati processati: {row_data}")
            self.data.append(row_data)
            self.update_table()
            self.save_to_excel()

        except Exception as e:
            self.handle_error(f"Errore nell'elaborazione dei risultati: {str(e)}")



    def handle_error(self, error_msg: str):
        self.status_label.setText(f"Errore: {error_msg}")
        print(f"Errore: {error_msg}")

    def save_to_excel(self):
        try:
            reports_dir = os.path.join(os.getcwd(), "Reports")
            os.makedirs(reports_dir, exist_ok=True)
            excel_path = os.path.join(reports_dir, EXCEL_FILE)

            formatted_data = []
            for item in self.data:
                try:
                    importo_originale = float(str(item['Importo']).replace(',', '.'))
                    importo_eur = float(str(item['Importo (EUR)']).replace(',', '.'))
                except ValueError as e:
                    self.logger.log_action(f"Errore conversione importo: {str(e)}")
                    importo_originale = 0.0
                    importo_eur = 0.0



                formatted_item = {
                    'Data': item['Data'],
                    'Importo Originale': importo_originale,
                    'Valuta': item['Valuta'],
                    'Importo (EUR)': importo_eur,
                    'Descrizione': item.get('Descrizione', ''),
                    'Categoria': item.get('Categoria', ''),
                    'Sottocategoria': item.get('Sottocategoria', ''),

                    'File': item['File']
                }
                formatted_data.append(formatted_item)

            df = pd.DataFrame(formatted_data)

            if os.path.exists(excel_path):
                existing_df = pd.read_excel(excel_path)
                existing_df['Importo Originale'] = pd.to_numeric(existing_df['Importo Originale'], errors='coerce')
                existing_df['Importo (EUR)'] = pd.to_numeric(existing_df['Importo (EUR)'], errors='coerce')

                combined_df = pd.concat([existing_df, df])
                combined_df = combined_df.drop_duplicates(
                    subset=['Data', 'Importo Originale', 'Descrizione','Categoria','Sottocategoria'],
                    keep='last'
                )
                df = combined_df

            writer = pd.ExcelWriter(excel_path, engine='xlsxwriter')
            df.to_excel(writer, index=False, sheet_name='Scontrini')

            workbook = writer.book
            worksheet = writer.sheets['Scontrini']

            # Formati
            money_format = workbook.add_format({'num_format': '#,##0.00'})
            date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
            percent_format = workbook.add_format({'num_format': '0.00%'})

            # Colonne
            worksheet.set_column('A:A', 15, date_format)  # Data
            worksheet.set_column('B:B', 15, money_format)  # Importo Originale
            worksheet.set_column('C:C', 10)  # Valuta
            worksheet.set_column('D:D', 15, money_format)  # Importo (EUR)
            worksheet.set_column('E:E', 40)  # Descrizione
            worksheet.set_column('F:F', 20)  # Categoria
            worksheet.set_column('G:G', 25)  # Sottocategoria
            worksheet.set_column('H:H', 25)  # file


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
                    "Sottocategoria":35,
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

