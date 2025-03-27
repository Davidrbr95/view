from view.widgets.base_device_widget import BaseDeviceWidget, scan_for_properties
from qtpy.QtWidgets import QLabel
import importlib

# class TunableLensWidget(BaseDeviceWidget):

#     def __init__(self, stage,
#                  advanced_user: bool = True):
#         """
#         Modify BaseDeviceWidget to be specifically for Stage. Main need is advanced user.
#         :param stage: stage object
#         :param advanced_user: boolean specifying complexity of widget. If False, only position is shown
#         """

#         self.stage_properties = scan_for_properties(stage) if advanced_user else {'position_mm': stage.position_mm}

#         del self.stage_properties['signal_temperature_c']
#         del self.stage_properties['mode']
#         self.stage_module = importlib.import_module(stage.__module__)
#         super().__init__(type(stage), self.stage_properties)

#         # alter position_mm widget to use instrument_axis as label
#         self.property_widgets['position_mm'].setEnabled(False)
#         position_label = self.property_widgets['position_mm'].findChild(QLabel)
#         unit = getattr(type(stage).position_mm, 'unit', 'mm')  # TODO: Change when deliminated property is updated
#         position_label.setText(f'X [{unit}]')

#         # update property_widgets['position_mm'] text to be white
#         style = """
#         QScrollableLineEdit {
#             color: white;
#         } 

#         QLabel {
#             color : white;     
#         }    
#         """
#         self.property_widgets['position_mm'].setStyleSheet(style)

from qtpy.QtWidgets import QLabel, QLineEdit, QPushButton, QHBoxLayout, QWidget
from view.widgets.base_device_widget import BaseDeviceWidget, scan_for_properties

class TunableLensWidget(BaseDeviceWidget):
    """
    Example of a specialized widget for a tunable lens (KDC101) that:
      1. Displays the current position_mm property (inherited from BaseDeviceWidget).
      2. Lets the user set the lens position with a custom button + line edit.
    """

    def __init__(self, stage, advanced_user: bool = True):
        props = scan_for_properties(stage) if advanced_user else {"position_mm": stage.position_mm}
        properties = {}
        for i in props.keys():
            if i not in ["signal_temperature_c", "mode"]:
                properties[i] = props[i]
        
        super().__init__(
            device_type=type(stage),
            properties=properties,
        )
        self.stage = stage  # Keep a reference to the actual device object

        # ---------------------------------------------------------------------
        # Optionally remove some properties that you don't want from BaseWidget
        # (if they exist in the scanned properties).
        # Because BaseDeviceWidget just used the 'properties' dict you passed in,
        # you can delete from self.property_widgets if desired:
        

        # Example: If you want to disable the existing `position_mm` property,
        # you can do so by grabbing its top-level QWidget and disabling it:
        if "position_mm" in self.property_widgets:
            self.property_widgets["position_mm"].setDisabled(True)

        # ---------------------------------------------------------------------
        # CREATE A SET-POSITION SECTION
        # QMainWindow has no direct .layout() to add sub-layouts,
        # so retrieve the central widget & its layout.
        parent_widget = self.centralWidget()       # The QWidget used by BaseDeviceWidget
        parent_layout = parent_widget.layout()      # e.g. QVBoxLayout or QHBoxLayout

        # Make a small horizontal layout with a label, line-edit, and button.
        set_position_layout = QHBoxLayout()

        self.set_position_label = QLabel("Set Position [mm]:")
        self.set_position_edit  = QLineEdit()
        self.set_position_button = QPushButton("Set position")

        set_position_layout.addWidget(self.set_position_label)
        set_position_layout.addWidget(self.set_position_edit)
        set_position_layout.addWidget(self.set_position_button)

        # Add this small layout to the *existing* layout.
        parent_layout.addLayout(set_position_layout)

        # Connect button click -> set_position
        self.set_position_button.clicked.connect(self._on_set_position_clicked)

    def _on_set_position_clicked(self):
        """Called when user clicks 'Set position' button."""
        text = self.set_position_edit.text().strip()
        if not text:
            return
        try:
            new_position = float(text)
        except ValueError:
            # You may want to show a warning or beep if it's not a float
            return

        # Actually move the lens
        self.stage.position_mm = new_position
