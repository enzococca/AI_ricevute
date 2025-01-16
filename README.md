# Analizzatore Scontrini

Un'applicazione desktop Python per l'automazione della gestione e analisi degli scontrini, con supporto per valute multiple e generazione di report dettagliati.

## Caratteristiche Principali

### 🖥️ Interfaccia Utente
- Interfaccia grafica intuitiva basata su PyQt5
- Visualizzazione dati in formato tabellare
- Area di log per monitoraggio in tempo reale
- Pulsanti per:
  - Caricamento scontrini
  - Esportazione PDF
  - Aggiornamento Excel

### 🔍 Analisi degli Scontrini
- Integrazione con GPT-4o per estrazione dati
- Riconoscimento automatico di:
  - Data
  - Importo
  - Valuta
  - Esercente
- Categorizzazione automatica delle spese
- Standardizzazione dei formati data

### 💱 Gestione Valute
Sistema di conversione multi-livello:
1. ExchangeRate API
2. Forex Python
3. Fixer.io
4. Tassi di fallback predefiniti

Conversione automatica di tutti gli importi in EUR.

### 📊 Archiviazione e Report
- **Excel**: 
  - Salvataggio automatico dei dati
  - Formattazione personalizzata
  
- **PDF**:
  - Report dettagliati
  - Tabelle transazioni
  - Riepiloghi spese
  - Analisi per categoria
  - Dettagli singole transazioni

### 🔄 Funzionalità in Sviluppo
- [ ] Monitoraggio cartella automatico
- [ ] Rilevamento duplicati
- [ ] Ottimizzazione immagini
- [ ] Logging avanzato

## Casi d'Uso

✓ Gestione spese aziendali  
✓ Tracciamento spese personali  
✓ Organizzazione contabile  
✓ Analisi tendenze di spesa  
✓ Gestione multi-valuta

## Requisiti di Sistema

```bash
# Dipendenze principali
python >= 3.9
PyQt5
langchain
openai
fpdf2
pandas
```

## Installazione

```bash
# Clona il repository
git clone [repository-url]

# Installa le dipendenze
pip install -r requirements.txt
```

## Configurazione

1. Crea un file `.env` nella root del progetto
2. Aggiungi le seguenti variabili:
```env
OPENAI_API_KEY=your-api-key
EXCHANGE_RATE_API_KEY=your-api-key
FIXER_API_KEY=your-api-key
```

## Utilizzo

```bash
# Avvia l'applicazione
python main.py
```

### Caricamento Scontrini
1. Clicca su "Carica Scontrini"
2. Seleziona uno o più file immagine
3. Attendi l'elaborazione automatica

### Esportazione Report
- PDF: Clicca su "Esporta PDF"
- Excel: Clicca su "Aggiorna Excel"

## Struttura Cartelle

```
project/
│
├── main.py           # Entry point
├── requirements.txt  # Dipendenze
├── README.md        # Documentazione
│
├── scontrini/       # Cartella monitorata
├── Reports/         # Output report
└── fonts/          # Font per PDF
```

## Contribuire

Le pull request sono benvenute. Per modifiche importanti, apri prima una issue per discutere cosa vorresti cambiare.

## Licenza

[MIT](https://choosealicense.com/licenses/mit/)

## Supporto

Per supporto, apri una issue o contatta il team di sviluppo.

## Roadmap

- [ ] Implementazione OCR locale
- [ ] Supporto per più valute di base
- [ ] Dashboard web
- [ ] API REST
- [ ] App mobile companion