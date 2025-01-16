"""
Automatically generated file from migration script.
"""


import os



class FileAgent:
    """Agente per la gestione dei file e duplicati."""

    def __init__(self, watch_dir: str):
        self.watch_dir = watch_dir
        self.file_history = set()
        self.load_history()

    def load_history(self):
        """Carica la cronologia dei file processati."""
        try:
            history_file = os.path.join(self.watch_dir, ".file_history")
            if os.path.exists(history_file):
                with open(history_file, "r") as f:
                    self.file_history = set(f.read().splitlines())
        except Exception as e:
            print(f"Errore nel caricamento della cronologia: {str(e)}")

    def save_history(self):
        """Salva la cronologia dei file processati."""
        try:
            history_file = os.path.join(self.watch_dir, ".file_history")
            with open(history_file, "w") as f:
                f.write("\n".join(self.file_history))
        except Exception as e:
            print(f"Errore nel salvataggio della cronologia: {str(e)}")

    def is_duplicate(self, file_path: str) -> bool:
        """Controlla se il file è un duplicato."""
        import hashlib
        try:
            with open(file_path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
                if file_hash in self.file_history:
                    return True
                self.file_history.add(file_hash)
                self.save_history()
                return False
        except Exception as e:
            print(f"Errore nel controllo duplicati: {str(e)}")
            return False

