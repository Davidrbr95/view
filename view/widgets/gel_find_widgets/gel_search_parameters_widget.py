# gel_search_parameters_widget.py

import numpy as np
from qtpy.QtWidgets import QWidget, QVBoxLayout, QLabel, QFormLayout, QDoubleSpinBox, QComboBox
from qtpy.QtCore import Signal

class GelSearchParametersWidget(QWidget):
    """Widget to adjust parameters for gel search and display estimates."""

    parametersChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.boundaries = None  # To store volume boundaries

        layout = QVBoxLayout()
        self.setLayout(layout)

        title = QLabel("Gel Search Parameters")
        layout.addWidget(title)

        self.parameters_form = QFormLayout()
        layout.addLayout(self.parameters_form)

        # Intensity Threshold
        self.intensity_threshold = QDoubleSpinBox()
        self.intensity_threshold.setRange(0.0, 65535.0)
        self.intensity_threshold.setValue(10.0)
        self.parameters_form.addRow("Intensity Threshold:", self.intensity_threshold)
        self.intensity_threshold.valueChanged.connect(self.parametersChanged.emit)

        # Z Step Size
        self.z_step_size_mm = QDoubleSpinBox()
        self.z_step_size_mm.setRange(0.001, 1.0)
        self.z_step_size_mm.setValue(0.01)
        self.parameters_form.addRow("Z Step Size (mm):", self.z_step_size_mm)
        self.z_step_size_mm.valueChanged.connect(self.parametersChanged.emit)

        # X Step Size
        self.x_step_mm = QDoubleSpinBox()
        self.x_step_mm.setRange(0.01, 10.0)
        self.x_step_mm.setValue(0.5)
        self.parameters_form.addRow("X Step Size (mm):", self.x_step_mm)
        self.x_step_mm.valueChanged.connect(self.parametersChanged.emit)

        # Y Step Size
        self.y_step_mm = QDoubleSpinBox()
        self.y_step_mm.setRange(0.01, 10.0)
        self.y_step_mm.setValue(0.5)
        self.parameters_form.addRow("Y Step Size (mm):", self.y_step_mm)
        self.y_step_mm.valueChanged.connect(self.parametersChanged.emit)

        # Exposure Time
        self.exposure_time_ms = QDoubleSpinBox()
        self.exposure_time_ms.setRange(0.1, 1000.0)
        self.exposure_time_ms.setValue(5.0)
        self.parameters_form.addRow("Exposure Time (ms):", self.exposure_time_ms)
        self.exposure_time_ms.valueChanged.connect(self.parametersChanged.emit)

        # Laser Power
        self.laser_power_percent = QDoubleSpinBox()
        self.laser_power_percent.setRange(0.0, 100.0)
        self.laser_power_percent.setValue(30.0)
        self.parameters_form.addRow("Laser Power (%):", self.laser_power_percent)
        self.laser_power_percent.valueChanged.connect(self.parametersChanged.emit)

        # Z Margin
        self.z_margin_mm = QDoubleSpinBox()
        self.z_margin_mm.setRange(0.0, 10.0)
        self.z_margin_mm.setValue(0.1)
        self.parameters_form.addRow("Z Margin (mm):", self.z_margin_mm)
        self.z_margin_mm.valueChanged.connect(self.parametersChanged.emit)

        # Scanning Pattern
        self.scan_pattern = QComboBox()
        self.scan_pattern.addItems(["Rectangular Grid"])
        self.parameters_form.addRow("Scanning Pattern:", self.scan_pattern)
        self.scan_pattern.currentTextChanged.connect(self.parametersChanged.emit)

        # Estimated Number of Images
        self.num_images_label = QLabel("Estimated Number of Images: N/A")
        layout.addWidget(self.num_images_label)

        # Estimated Acquisition Time
        self.acquisition_time_label = QLabel("Estimated Acquisition Time: N/A")
        layout.addWidget(self.acquisition_time_label)

        # Connect parametersChanged signal to update estimates
        self.parametersChanged.connect(self.update_estimates)

    def get_parameters(self):
        """Get the parameters as a dictionary."""
        return {
            'intensity_threshold': self.intensity_threshold.value(),
            'z_step_size_mm': self.z_step_size_mm.value(),
            'x_step_mm': self.x_step_mm.value(),
            'y_step_mm': self.y_step_mm.value(),
            'exposure_time_ms': self.exposure_time_ms.value(),
            'laser_power_percent': self.laser_power_percent.value(),
            'z_margin_mm': self.z_margin_mm.value(),
            'scan_pattern': self.scan_pattern.currentText(),
        }

    def set_boundaries(self, boundaries):
        """Set the volume boundaries."""
        self.boundaries = boundaries
        self.update_estimates()

    def update_estimates(self):
        """Update the estimated number of images and acquisition time."""
        if self.boundaries is None:
            self.num_images_label.setText("Estimated Number of Images: N/A")
            self.acquisition_time_label.setText("Estimated Acquisition Time: N/A")
            return

        parameters = self.get_parameters()

        x_start, x_end = self.boundaries[0]
        y_start, y_end = self.boundaries[1]
        z_start, z_end = self.boundaries[2]

        x_step = parameters['x_step_mm']
        y_step = parameters['y_step_mm']
        z_step = parameters['z_step_size_mm']
        exposure_time_ms = parameters['exposure_time_ms']

        # Compute number of steps in each dimension
        num_x_steps = int(np.ceil((x_end - x_start) / x_step)) + 1
        num_y_steps = int(np.ceil((y_end - y_start) / y_step)) + 1
        num_z_steps = int(np.ceil((z_end - z_start) / z_step)) + 1

        total_images = num_x_steps * num_y_steps * num_z_steps

        # Compute total acquisition time in seconds
        total_time_s = total_images * (exposure_time_ms / 1000.0)

        # Update labels
        self.num_images_label.setText(f"Estimated Number of Images: {total_images}")

        # Convert total_time_s to hours, minutes, seconds
        hours = int(total_time_s // 3600)
        minutes = int((total_time_s % 3600) // 60)
        seconds = int(total_time_s % 60)

        self.acquisition_time_label.setText(f"Estimated Acquisition Time: {hours}h {minutes}m {seconds}s")
