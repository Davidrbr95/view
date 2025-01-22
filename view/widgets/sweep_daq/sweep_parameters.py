# daq_parameters_widget.py

from qtpy.QtWidgets import QWidget, QVBoxLayout, QLabel, QFormLayout, QDoubleSpinBox, QSpinBox, QGroupBox, QTabWidget, QRadioButton, QButtonGroup, QHBoxLayout
from qtpy.QtCore import Signal


class DAQParametersWidget(QWidget):
    """Widget to adjust DAQ parameters for sweeping."""

    parametersChanged = Signal()

    def __init__(self, daq):
        super().__init__()

        self.daq = daq  # The DAQ configuration dictionary

        # Define the galvos, parameters
        self.galvos = ['x galvo mirror', 'y galvo mirror']
        self.parameters = ['amplitude_volts', 'offset_volts']
        self.channels = ['CH405', 'CH488', 'CH561', 'CH638']

        # Create the main layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        title = QLabel("DAQ Parameters Sweep Settings")
        self.layout.addWidget(title)

        # Create laser (channel) selection outside of the galvo tabs
        self.create_laser_selection()

        # Create a QTabWidget to hold the galvos
        self.tab_widget = QTabWidget()
        self.layout.addWidget(self.tab_widget)



        self.parameter_widgets = {}

        # Get device min/max volts for each galvo
        self.device_voltages = {}
        for galvo in self.galvos:
            # Navigate to DAQ configuration to get device_min_volts and device_max_volts
            try:
                print(self.daq)
                galvo_config = self.daq['tasks']['ao_task']['ports'][galvo]
                device_min_volts = galvo_config.get('device_min_volts', -10.0)
                device_max_volts = galvo_config.get('device_max_volts', 10.0)
                self.device_voltages[galvo] = (device_min_volts, device_max_volts)
            except KeyError:
                self.device_voltages[galvo] = (-10.0, 10.0)  # Default values if not specified

        # Create tabs for each galvo
        for galvo in self.galvos:
            galvo_widget = QWidget()
            galvo_layout = QVBoxLayout()
            galvo_widget.setLayout(galvo_layout)

            # Get device min/max volts for this galvo
            device_min_volts, device_max_volts = self.device_voltages.get(galvo, (-10.0, 10.0))

            # Create parameter group boxes
            self.param_widgets = {}
            for param in self.parameters:
                param_groupbox = QGroupBox(param)
                param_layout = QFormLayout()
                param_groupbox.setLayout(param_layout)

                # Initialize the widgets
                param_widgets = {}

                # Read the center value from the DAQ configuration
                # Since the channel is selected outside, we'll default to the first channel for initial values
                default_channel = self.selected_channel
                print('BEFORE THE TRY', self.daq)
                try:
                    center_value = self.daq['tasks']['ao_task']['ports'][galvo]['parameters'][param]['channels'][default_channel]
                except KeyError:
                    center_value = 0.0  # Default value if not found

                # Center value spinbox
                center_spinbox = QDoubleSpinBox()
                center_spinbox.setRange(device_min_volts, device_max_volts)
                center_spinbox.setDecimals(6)
                center_spinbox.setValue(center_value)
                center_spinbox.setSingleStep(0.1)
                center_spinbox.valueChanged.connect(self.parametersChanged.emit)

                # Radius value spinbox
                max_radius = (device_max_volts - device_min_volts) / 2
                radius_spinbox = QDoubleSpinBox()
                radius_spinbox.setRange(0.0, max_radius)
                radius_spinbox.setDecimals(6)
                radius_spinbox.setValue(0)
                radius_spinbox.setSingleStep(0.1)
                radius_spinbox.valueChanged.connect(self.parametersChanged.emit)

                # Number of steps spinbox
                steps_spinbox = QSpinBox()
                steps_spinbox.setRange(1, 10000)
                steps_spinbox.setValue(1)
                steps_spinbox.valueChanged.connect(self.parametersChanged.emit)

                # Add widgets to the form layout
                param_layout.addRow("Center:", center_spinbox)
                param_layout.addRow("Radius:", radius_spinbox)
                param_layout.addRow("Steps:", steps_spinbox)

                # Store widgets for later access
                param_widgets['center'] = center_spinbox
                param_widgets['radius'] = radius_spinbox
                param_widgets['steps'] = steps_spinbox

                # Store param_widgets in a dict with key (galvo, param)
                self.parameter_widgets[(galvo, param)] = param_widgets

                galvo_layout.addWidget(param_groupbox)

            # Add the galvo widget as a tab
            self.tab_widget.addTab(galvo_widget, galvo)

        # Add the tunable lens parameters
        self.add_tunable_lens_parameters()
        
        # Estimated Number of Combinations
        self.num_combinations_label = QLabel("Estimated Number of Combinations: N/A")
        self.layout.addWidget(self.num_combinations_label)

        # Connect parametersChanged signal to update estimates
        self.parametersChanged.connect(self.update_estimates)

        # Initial estimate
        self.update_estimates()

    def create_laser_selection(self):
        """Create the laser (channel) selection radio buttons."""
        # Create a group for channels with radio buttons
        channel_groupbox = QGroupBox("Select Channel")
        channel_layout = QHBoxLayout()
        channel_groupbox.setLayout(channel_layout)

        self.channel_button_group = QButtonGroup()
        self.channel_buttons = {}
        self.selected_channel = self.channels[0]  # Default selected channel

        for channel in self.channels:
            radio_button = QRadioButton(channel)
            self.channel_button_group.addButton(radio_button)
            channel_layout.addWidget(radio_button)
            self.channel_buttons[channel] = radio_button

            if channel == self.selected_channel:
                radio_button.setChecked(True)

        self.channel_button_group.buttonClicked.connect(self.channel_selection_changed)

        self.layout.addWidget(channel_groupbox)

    def channel_selection_changed(self, button):
        """Update the parameter widgets when the selected channel changes."""
        self.selected_channel = button.text()
        # Update the parameter widgets with values from the selected channel
        for galvo in self.galvos:
            for param in self.parameters:
                # Get the widgets
                param_widgets = self.parameter_widgets[(galvo, param)]
                center_spinbox = param_widgets['center']

                # Read the center value from the DAQ configuration
                try:
                    center_value = self.daq['tasks']['ao_task']['ports'][galvo]['parameters'][param]['channels'][self.selected_channel]
                except KeyError:
                    center_value = 0.0  # Default value if not found

                # Update center_spinbox value
                center_spinbox.blockSignals(True)
                center_spinbox.setValue(center_value)
                center_spinbox.blockSignals(False)

        # Emit parametersChanged signal to update estimates
        self.parametersChanged.emit()

    def add_tunable_lens_parameters(self):
        """Add tunable lens parameters to the GUI."""
        tunable_lens_groupbox = QGroupBox("Tunable Lens Parameters")
        tunable_lens_layout = QFormLayout()
        tunable_lens_groupbox.setLayout(tunable_lens_layout)

        self.tunable_lens_widgets = {}

        # Assume device limits for current (in mA)
        device_min_current = -300.0  # Example values, adjust as per your device specs
        device_max_current = 300.0

        # Read the current value from the instrument's tunable lens settings
        try:
            current_value = self.instrument.tunable_lens['tunablelens'].current  # Assuming current is in mA
        except (KeyError, AttributeError):
            current_value = 0.0  # Default value if not found

        # Center value spinbox
        center_spinbox = QDoubleSpinBox()
        center_spinbox.setRange(device_min_current, device_max_current)
        center_spinbox.setDecimals(2)
        center_spinbox.setValue(current_value)
        center_spinbox.setSingleStep(1.0)
        center_spinbox.valueChanged.connect(self.parametersChanged.emit)

        # Radius value spinbox
        max_radius = (device_max_current - device_min_current) / 2
        radius_spinbox = QDoubleSpinBox()
        radius_spinbox.setRange(0.0, max_radius)
        radius_spinbox.setDecimals(2)
        radius_spinbox.setValue(10.0)
        radius_spinbox.setSingleStep(1.0)
        radius_spinbox.valueChanged.connect(self.parametersChanged.emit)

        # Number of steps spinbox
        steps_spinbox = QSpinBox()
        steps_spinbox.setRange(1, 100)
        steps_spinbox.setValue(5)
        steps_spinbox.valueChanged.connect(self.parametersChanged.emit)

        # Add widgets to the form layout
        tunable_lens_layout.addRow("Center Current (mA):", center_spinbox)
        tunable_lens_layout.addRow("Radius (mA):", radius_spinbox)
        tunable_lens_layout.addRow("Steps:", steps_spinbox)

        # Store widgets for later access
        self.tunable_lens_widgets['center'] = center_spinbox
        self.tunable_lens_widgets['radius'] = radius_spinbox
        self.tunable_lens_widgets['steps'] = steps_spinbox

        # Add the group box to the main layout
        self.layout.addWidget(tunable_lens_groupbox)

    def get_parameters(self):
        """Get the DAQ sweep parameters as a dictionary."""
        sweep_parameters = {}
        total_combinations = 0
        for galvo in self.galvos:
            for param in self.parameters:
                param_widgets = self.parameter_widgets[(galvo, param)]
                center = param_widgets['center'].value()
                radius = param_widgets['radius'].value()
                steps = param_widgets['steps'].value()

                key = (galvo, param)
                sweep_parameters[key] = {
                    'center': center,
                    'radius': radius,
                    'steps': steps,
                }
                total_combinations += steps  # Since we're sweeping one parameter at a time

        # Add tunable lens parameters
        center = self.tunable_lens_widgets['center'].value()
        radius = self.tunable_lens_widgets['radius'].value()
        steps = self.tunable_lens_widgets['steps'].value()

        key = ('tunable_lens', 'current_ma')
        sweep_parameters[key] = {
            'center': center,
            'radius': radius,
            'steps': steps,
        }
        total_combinations += steps  # Since we're sweeping one parameter at a time

        self.total_combinations = total_combinations
        return sweep_parameters

    def update_estimates(self):
        """Update the estimated number of combinations."""
        self.get_parameters()  # Updates self.total_combinations
        self.num_combinations_label.setText(f"Estimated Number of Combinations: {self.total_combinations}")

    def get_selected_channel(self):
        """Return the currently selected channel."""
        return self.selected_channel