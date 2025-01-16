"""
Automatically generated file from migration script.
"""



class OCRAgent:
    """Agente per l'ottimizzazione del riconoscimento del testo."""

    def __init__(self):
        self.preprocessing_methods = [
            self.enhance_contrast,
            self.denoise,
            self.sharpen
        ]

    def enhance_contrast(self, image):
        """Migliora il contrasto dell'immagine."""
        try:
            import cv2
            import numpy as np
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            limg = cv2.merge((cl, a, b))
            return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        except:
            return image

    def denoise(self, image):
        """Rimuove il rumore dall'immagine."""
        try:
            import cv2
            return cv2.fastNlMeansDenoisingColored(image)
        except:
            return image

    def sharpen(self, image):
        """Aumenta la nitidezza dell'immagine."""
        try:
            import cv2
            import numpy as np
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            return cv2.filter2D(image, -1, kernel)
        except:
            return image

    def optimize_image(self, image_path: str) -> str:
        """Ottimizza l'immagine per il riconoscimento del testo."""
        try:
            import cv2
            image = cv2.imread(image_path)

            # Applica i metodi di preprocessing in sequenza
            for method in self.preprocessing_methods:
                image = method(image)

            # Salva l'immagine ottimizzata
            optimized_path = image_path.replace(".", "_optimized.")
            cv2.imwrite(optimized_path, image)
            return optimized_path
        except Exception as e:
            print(f"Errore nell'ottimizzazione dell'immagine: {str(e)}")
            return image_path

