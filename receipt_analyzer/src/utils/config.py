import os

# Percorsi
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
WATCH_DIR = os.path.join(DATA_DIR, "scontrini")
REPORTS_DIR = os.path.join(DATA_DIR, "Reports")

# File names
EXCEL_FILE = "pagamenti.xlsx"
PDF_REPORT = "report_pagamenti.pdf"

# Tassi di cambio di fallback
FALLBACK_RATES = {
    ('USD', 'EUR'): 0.85,
    ('EUR', 'USD'): 1.18,
    ('EUR', 'OMR'): 0.44,
    ('OMR', 'EUR'): 2.27,
}

# Assicurati che le directory esistano
os.makedirs(WATCH_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
