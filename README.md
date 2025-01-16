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
