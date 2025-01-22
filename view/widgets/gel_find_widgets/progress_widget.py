from qtpy.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar

class ProgressWidget(QWidget):
    """Widget to display the progress bar."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.progress_label = QLabel("Scanning Progress")
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

    def update_progress(self, value):
        """Update the progress bar."""
        self.progress_bar.setValue(value)
