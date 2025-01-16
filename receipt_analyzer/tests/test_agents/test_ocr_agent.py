import shutil
import unittest

import cv2
import numpy as np
import tempfile
import sys
import os
# Aggiungi il percorso root del progetto al PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.agents.ocr_agent import OCRAgent


class TestOCRAgent(unittest.TestCase):
    def setUp(self):
        self.agent = OCRAgent()
        # Crea un'immagine di test
        self.test_img = np.full((100, 100, 3), 255, dtype=np.uint8)
        cv2.putText(self.test_img, "Test", (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        # Salva l'immagine di test
        self.temp_dir = tempfile.mkdtemp()
        self.test_image_path = os.path.join(self.temp_dir, "test_image.jpg")
        cv2.imwrite(self.test_image_path, self.test_img)

    def tearDown(self):
        # Pulisci i file temporanei
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_enhance_contrast(self):
        enhanced = self.agent.enhance_contrast(self.test_img)
        self.assertEqual(enhanced.shape, self.test_img.shape)
        # Verifica che il contrasto sia effettivamente cambiato
        self.assertFalse(np.array_equal(enhanced, self.test_img))

    def test_denoise(self):
        # Aggiungi rumore all'immagine
        noisy = self.test_img + np.random.normal(0, 25, self.test_img.shape).astype(np.uint8)
        denoised = self.agent.denoise(noisy)
        self.assertEqual(denoised.shape, noisy.shape)
        # Verifica che il rumore sia stato ridotto
        self.assertLess(np.std(denoised), np.std(noisy))

    def test_sharpen(self):
        sharpened = self.agent.sharpen(self.test_img)
        self.assertEqual(sharpened.shape, self.test_img.shape)
        # Verifica che l'immagine sia stata modificata
        self.assertFalse(np.array_equal(sharpened, self.test_img))

    def test_optimize_image(self):
        optimized_path = self.agent.optimize_image(self.test_image_path)
        self.assertTrue(os.path.exists(optimized_path))
        self.assertNotEqual(optimized_path, self.test_image_path)

        # Verifica che l'immagine ottimizzata sia diversa dall'originale
        optimized_img = cv2.imread(optimized_path)
        original_img = cv2.imread(self.test_image_path)
        self.assertFalse(np.array_equal(optimized_img, original_img))

if __name__ == '__main__':
    unittest.main()