"""
Automatically generated file from migration script.
"""



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

