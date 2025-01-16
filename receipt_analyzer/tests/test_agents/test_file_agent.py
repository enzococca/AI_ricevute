import unittest

import tempfile
import shutil
import sys
import os
# Aggiungi il percorso root del progetto al PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.agents.file_agent import FileAgent


class TestFileAgent(unittest.TestCase):
    def setUp(self):
        # Crea una directory temporanea per i test
        self.test_dir = tempfile.mkdtemp()
        self.agent = FileAgent(self.test_dir)

    def tearDown(self):
        # Pulisci dopo i test
        shutil.rmtree(self.test_dir)

    def test_duplicate_detection(self):
        # Crea due file con lo stesso contenuto
        file1_path = os.path.join(self.test_dir, "test1.txt")
        file2_path = os.path.join(self.test_dir, "test2.txt")

        content = "test content"
        with open(file1_path, "w") as f:
            f.write(content)
        with open(file2_path, "w") as f:
            f.write(content)

        # Il primo file non dovrebbe essere un duplicato
        self.assertFalse(self.agent.is_duplicate(file1_path))
        # Il secondo file dovrebbe essere riconosciuto come duplicato
        self.assertTrue(self.agent.is_duplicate(file2_path))

    def test_history_persistence(self):
        # Crea un file e verifica che venga salvato nella cronologia
        test_file = os.path.join(self.test_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        self.agent.is_duplicate(test_file)  # Questo dovrebbe salvare il file nella cronologia

        # Crea un nuovo agente e verifica che carichi la cronologia
        new_agent = FileAgent(self.test_dir)
        self.assertTrue(new_agent.is_duplicate(test_file))

    def test_nonexistent_file(self):
        # Verifica che gestisca correttamente i file inesistenti
        nonexistent_file = os.path.join(self.test_dir, "nonexistent.txt")
        self.assertFalse(self.agent.is_duplicate(nonexistent_file))


if __name__ == '__main__':
    unittest.main()