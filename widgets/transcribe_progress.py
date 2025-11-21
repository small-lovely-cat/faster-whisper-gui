from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar

class TranscribeProgress(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout()

        self.label = QLabel("转录进度")
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.progress_bar)

        self.setLayout(self.layout)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def set_status_message(self, message):
        self.label.setText(message)