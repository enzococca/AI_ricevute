#!/usr/bin/env python3
from src.ui.main_window import ReceiptProcessor
from PyQt5.QtWidgets import QApplication
import sys

def main():
    app = QApplication(sys.argv)
    window = ReceiptProcessor()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
