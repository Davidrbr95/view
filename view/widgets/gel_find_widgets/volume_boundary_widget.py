from qtpy.QtWidgets import QWidget, QVBoxLayout, QLabel, QFormLayout, QDoubleSpinBox
from qtpy.QtCore import Signal


class VolumeBoundaryWidget(QWidget):
    """Widget to input the boundaries of the volume of interest."""
    
    boundariesChanged = Signal()

    def __init__(self, unit='mm', parent=None):
        super().__init__(parent)
        self.unit = unit

        layout = QVBoxLayout()
        self.setLayout(layout)

        title = QLabel("Volume Boundaries")
        layout.addWidget(title)

        self.boundary_form = QFormLayout()
        layout.addLayout(self.boundary_form)

        # X boundaries
        self.x_start = QDoubleSpinBox()
        self.x_start.setRange(-1000.0, 1000.0)
        self.x_start.setSuffix(f" {self.unit}")
        self.boundary_form.addRow("X Start:", self.x_start)

        self.x_end = QDoubleSpinBox()
        self.x_end.setRange(-1000.0, 1000.0)
        self.x_end.setSuffix(f" {self.unit}")
        self.boundary_form.addRow("X End:", self.x_end)

        # Y boundaries
        self.y_start = QDoubleSpinBox()
        self.y_start.setRange(-1000.0, 1000.0)
        self.y_start.setSuffix(f" {self.unit}")
        self.boundary_form.addRow("Y Start:", self.y_start)

        self.y_end = QDoubleSpinBox()
        self.y_end.setRange(-1000.0, 1000.0)
        self.y_end.setSuffix(f" {self.unit}")
        self.boundary_form.addRow("Y End:", self.y_end)

        # Z boundaries
        self.z_start = QDoubleSpinBox()
        self.z_start.setRange(-1000.0, 1000.0)
        self.z_start.setSuffix(f" {self.unit}")
        self.boundary_form.addRow("Z Start:", self.z_start)

        self.z_end = QDoubleSpinBox()
        self.z_end.setRange(-1000.0, 1000.0)
        self.z_end.setSuffix(f" {self.unit}")
        self.boundary_form.addRow("Z End:", self.z_end)
        
        # Connect signals
        self.x_start.valueChanged.connect(self.boundariesChanged.emit)
        self.x_end.valueChanged.connect(self.boundariesChanged.emit)
        self.y_start.valueChanged.connect(self.boundariesChanged.emit)
        self.y_end.valueChanged.connect(self.boundariesChanged.emit)
        self.z_start.valueChanged.connect(self.boundariesChanged.emit)
        self.z_end.valueChanged.connect(self.boundariesChanged.emit)

    def get_boundaries(self):
        """Get the boundaries as a tuple."""
        return (
            (self.x_start.value(), self.x_end.value()),
            (self.y_start.value(), self.y_end.value()),
            (self.z_start.value(), self.z_end.value()),
        )
