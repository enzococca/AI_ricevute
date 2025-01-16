"""
Automatically generated file from migration script.
"""


from watchdog.events import FileSystemEventHandler

from receipt_analyzer.src.workers.processing import ProcessingWorker


class ReceiptWatcher(FileSystemEventHandler):
    def __init__(self, processor):
        self.processor = processor

    def on_created(self, event):
        if not event.is_directory:
            worker = ProcessingWorker(event.src_path)
            worker.finished.connect(lambda data: self.processor.handle_results(data, event.src_path))
            worker.error.connect(self.processor.handle_error)
            worker.progress.connect(lambda msg: self.processor.status_label.setText(msg))

            self.processor.current_workers.append(worker)
            worker.start()

