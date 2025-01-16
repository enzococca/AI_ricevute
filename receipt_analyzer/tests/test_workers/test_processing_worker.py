# tests/test_workers/test_processing_worker.py
import unittest
from unittest.mock import Mock, patch
import sys
import os
# Aggiungi il percorso root del progetto al PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.workers.processing import ProcessingWorker


class TestProcessingWorker(unittest.TestCase):
    def setUp(self):
        self.mock_parent = Mock()
        self.worker = ProcessingWorker(self.mock_parent)
        self.worker.api_key_openai = "test-key"  # Mock API key

        # Mock per l'analysis chain
        self.mock_analysis_chain = Mock()
        self.worker.analysis_chain = self.mock_analysis_chain

    @patch('openai.OpenAI')
    def test_worker_initialization(self, mock_openai):
        """Test l'inizializzazione corretta del worker."""
        worker = ProcessingWorker(self.mock_parent)
        self.assertIsNotNone(worker.client)
        mock_openai.assert_called_once()

    def test_setup(self):
        """Test il metodo setup."""
        image_path = "test.jpg"
        analysis_chain = Mock()

        worker = self.worker.setup(image_path, analysis_chain)

        self.assertEqual(worker.image_path, image_path)
        self.assertEqual(worker.analysis_chain, analysis_chain)
        self.assertIs(worker, self.worker)  # Verifica il return self

    @patch('base64.b64encode')
    @patch('builtins.open', create=True)
    def test_image_processing(self, mock_open, mock_b64encode):
        """Test il processing dell'immagine."""
        mock_b64encode.return_value = b"test-encoded"
        mock_open.return_value.__enter__.return_value.read.return_value = b"test-image"

        self.worker.image_path = "test.jpg"
        self.worker.client.chat.completions.create = Mock(return_value=Mock(
            choices=[Mock(message=Mock(content='{"test": "data"}'))]
        ))

        # Esegui il worker in modo sincrono per il test
        self.worker.run()

        # Verifica che l'immagine sia stata letta e codificata
        mock_open.assert_called_once_with("test.jpg", "rb")
        mock_b64encode.assert_called_once_with(b"test-image")

    @patch('asyncio.new_event_loop')
    async def test_process_chains(self, mock_new_loop):
        """Test l'elaborazione delle catene di analisi."""
        test_json = '{"data": "2024-01-16", "importo": 100, "valuta": "EUR"}'

        # Mock delle risposte delle catene
        self.mock_analysis_chain.analysis_chain.ainvoke = Mock(
            return_value=test_json
        )
        self.mock_analysis_chain.validation_chain.ainvoke = Mock(
            return_value='{"valid": true}'
        )
        self.mock_analysis_chain.categorization_chain.ainvoke = Mock(
            return_value='{"categoria": "Test"}'
        )

        # Esegui il processing
        result = await self.worker.process_chains(test_json)

        # Verifica i risultati
        self.assertIsInstance(result, dict)
        self.mock_analysis_chain.analysis_chain.ainvoke.assert_called_once()
        self.mock_analysis_chain.validation_chain.ainvoke.assert_called_once()

    def test_error_handling(self):
        """Test la gestione degli errori."""
        # Simula un errore durante il processing
        self.worker.process_chains = Mock(side_effect=Exception("Test error"))

        # Connetti i segnali di test
        error_signal = Mock()
        self.worker.error.connect(error_signal)

        # Esegui il worker
        self.worker.run()

        # Verifica che il segnale di errore sia stato emesso
        error_signal.assert_called_once()

    def test_successful_processing(self):
        """Test un processing completato con successo."""
        # Mock dei risultati
        mock_results = {
            "data": "2024-01-16",
            "importo": 100,
            "valuta": "EUR",
            "esercente": "Test Shop"
        }

        # Mock del processing
        self.worker.process_chains = Mock(return_value=mock_results)

        # Connetti i segnali di test
        finished_signal = Mock()
        self.worker.finished.connect(finished_signal)

        # Esegui il worker
        self.worker.run()

        # Verifica che il segnale finished sia stato emesso con i risultati corretti
        finished_signal.assert_called_once_with(mock_results)

    def tearDown(self):
        """Pulizia dopo ogni test."""
        self.worker.client = None
        self.worker = None


if __name__ == '__main__':
    unittest.main()