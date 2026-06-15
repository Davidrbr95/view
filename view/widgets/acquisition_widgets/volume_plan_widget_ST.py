import useq
from view.widgets.base_device_widget import create_widget
from view.widgets.miscellaneous_widgets.q_item_delegates import QSpinItemDelegate
from view.widgets.miscellaneous_widgets.q_start_stop_table_header import QStartStopTableHeader
import numpy as np
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QButtonGroup,
    QDoubleSpinBox,
    QLabel,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QMainWindow,
    QFrame,
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
    QSizePolicy,
    QPushButton,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QGridLayout,
    QSpacerItem
)
from typing import Literal, Union, Generator
from qtpy.QtCore import Signal
import json
from qtpy.QtWidgets import QFileDialog
import csv
from qtpy.QtWidgets import QFileDialog

class GridFromEdges(useq.GridFromEdges):
    """Subclassing useq.GridFromEdges to add row and column attributes and allow reversible order"""

    reverse = property()  # initialize property

    def __init__(self, reverse=False, *args, **kwargs):
        # rewrite property since pydantic doesn't allow to add attr
        setattr(type(self), 'reverse', property(fget=lambda x: reverse))
        super().__init__(*args, **kwargs)

    @property
    def rows(self) -> int:
        """Property that returns number of rows in configured scan"""
        dx, _ = self._step_size(self.fov_width, self.fov_height)
        return self._nrows(dx)

    @property
    def columns(self) -> int:
        """Property that returns number of columns in configured scan"""
        _, dy = self._step_size(self.fov_width, self.fov_height)
        return self._ncolumns(dy)

    def iter_grid_positions(self, *args, **kwargs) -> Generator:
        """Return generator that contains positions of tiles. If reversed property is True, yield in revere order"""

        if not self.reverse:
            for tile in super().iter_grid_positions(*args, **kwargs):
                yield tile
        else:
            for tile in reversed(list(super().iter_grid_positions(*args, **kwargs))):
                yield tile

class GridWidthHeight(useq.GridWidthHeight):
    """Subclassing useq.GridWidthHeight to add row and column attributes and allow reversible order"""

    reverse = property()

    def __init__(self, reverse=False, *args, **kwargs):
        # rewrite property since pydantic doesn't allow to add attr
        setattr(type(self), 'reverse', property(fget=lambda x: reverse))
        super().__init__(*args, **kwargs)

    @property
    def rows(self) -> int:
        """Property that returns number of rows in configured scan"""
        dx, _ = self._step_size(self.fov_width, self.fov_height)
        return self._nrows(dx)

    @property
    def columns(self) -> int:
        """Property that returns number of rows in configured scan"""
        _, dy = self._step_size(self.fov_width, self.fov_height)
        return self._ncolumns(dy)

    def iter_grid_positions(self, *args, **kwargs) -> Generator:
        """Return generator that contains positions of tiles. If reversed property is True, yield in revere order"""

        if not self.reverse:
            for tile in super().iter_grid_positions(*args, **kwargs):
                yield tile
        else:
            for tile in reversed(list(super().iter_grid_positions(*args, **kwargs))):
                yield tile

class GridRowsColumns(useq.GridRowsColumns):
    """Subclass useq.GridRowsColumns to allow reversible order"""
    reverse = property()

    def __init__(self, reverse=False, *args, **kwargs):
        setattr(type(self), 'reverse', property(fget=lambda x: reverse))
        super().__init__(*args, **kwargs)

    def iter_grid_positions(self, *args, **kwargs) -> Generator:
        """Return generator that contains positions of tiles. If reversed property is True, yield in revere order"""

        if not self.reverse:
            for tile in super().iter_grid_positions(*args, **kwargs):
                yield tile
        else:
            for tile in reversed(list(super().iter_grid_positions(*args, **kwargs))):
                yield tile

class VolumePlanWidget_ST(QMainWindow):
    """Widget to plan out volume. Grid aspect based on pymmcore GridPlanWidget"""

    valueChanged = Signal(object)
    coordinateChangeODO2ProfilerRequested = Signal()
    coordinateChangeProfiler2ODORequested = Signal()
    coordinateChangeODO2NODORequested = Signal()
    coordinateChangeNODO2ODORequested = Signal()
    coordinateChangeProfiler2NODORequested = Signal()
    coordinateChangeNODO2ProfilerRequested = Signal()
    request_heightmaps_display = Signal()
    coordinateSystemChanged = Signal(str)
    request_boundary_calculation = Signal(float, int)
    enable_filter_changed = Signal(bool)
    enable_thresholding = Signal(bool)
    enable_surface_tracking = Signal(bool)
    enable_sync_tracking = Signal(bool)
    surfaceTrackingPathGenerated = Signal(str, str)
    feedforwardpathRequested = Signal(str)
    pathdisplayRequested = Signal(str)
    livetrackingRequested = Signal(bool)
    strideChanged = Signal(int)
    offsetChanged = Signal(float)
    positionChanged = Signal(float)
    loadBoundingBoxesRequested = Signal()

    def __init__(self,
                 acquisition_view,
                 instrument_view,
                 limits: list[[float, float], [float, float], [float, float]] = None,
                 fov_dimensions: list[float, float, float] = None,
                 fov_position: list[float, float, float] = None,
                 coordinate_plane: list[str, str, str] = None,
                 unit: str = 'um'):
        """
        :param limits: 2D list containing min and max stage limits for each coordinate plane in the order of [
        tiling_dim[0], tiling_dim[1], scanning_dim[0]]
        :param fov_dimensions: dimensions of field of view in
        specified unit in order of [tiling_dim[0], tiling_dim[1], scanning_dim[0]]
        :param fov_position:  position of
        field of view in specified unit in order of [tiling_dim[0], tiling_dim[1], scanning_dim[0]]
        :param coordinate_plane: coordinate plane describing the [tiling_dim[0], tiling_dim[1], scanning_dim[0]]. Can
        contain negatives.
        :param unit: common unit of all arguments. Defaults to um
        """
        super().__init__()
        self.instrument_view = instrument_view
        self.acquisition_view = acquisition_view
        self.acquisition_view.initialBoundaryReferenceChanged.connect(self._update_initial_reference)
        self.current_initial_reference = None  # or default to (0.0, 0.0)
        layout = QVBoxLayout()
        self.button_group = QButtonGroup()
        self.button_group.setExclusive(True)

        self.limits = sorted(limits) if limits else [[float('-inf'), float('inf')] for _ in range(3)]
        self._fov_dimensions = fov_dimensions if fov_dimensions else [1.0, 1.0, 0]
        self._fov_position = fov_position if fov_position else [0.0, 0.0, 0.0]
        self.coordinate_plane = [x.replace('-', '') for x in coordinate_plane] if coordinate_plane else ['x', 'y', 'z']
        self.unit = unit

        # initialize property values
        self._grid_offset = [0, 0]
        self._mode = None
        self._apply_all = True
        self._tile_visibility = np.ones([1, 1], dtype=bool)  # init as True
        self._scan_starts = np.zeros([1, 1], dtype=float)
        self._scan_ends = np.zeros([1, 1], dtype=float)
        self.start = None   # tile to start at. If none, then default is first tile
        self.stop = None    # tile to end at. If none, then default is last tile
        self.serpentine_scan = False
        self.bounding_boxes = []

        # ---------------------------
        # Set Coordinate Group
        # ---------------------------
        # Create a group box to hold coordinate status + buttons
        coord_group = QGroupBox("Setup Coordinate System")
        coord_group.setStyleSheet("""
            QGroupBox { border: 1px dashed gray; margin-top: 10px; padding: 5px; }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
            }
        """)

        coord_layout = QGridLayout()
        self.current_coordinate_system = "Unknown"
        self.coordinate_status_label = QLabel(f"Current Coordinate: {self.current_coordinate_system}")
        self.coordinate_status_label.setStyleSheet("font-weight: bold; color: navy;")
        coord_layout.addWidget(self.coordinate_status_label, 0, 0, 1, 3)  # Span label across 3 columns

        # Connect signal
        self.coordinateSystemChanged.connect(self.update_coordinate_status)

        # Create buttons
        self.btn_profiler_to_odo = QPushButton("Profiler to Low Res")
        self.btn_odo_to_profiler = QPushButton("Low Res to Profiler")
        self.btn_odo_to_nodo = QPushButton("Low Res to High Res")
        self.btn_nodo_to_odo = QPushButton("High Res to Low Res")
        self.btn_profiler_to_nodo = QPushButton("Profiler to High Res")
        self.btn_nodo_to_profiler = QPushButton("High Res to Profiler")

        # Connect buttons to signals
        self.btn_profiler_to_odo.clicked.connect(self.coordinateChangeProfiler2ODORequested.emit)
        self.btn_odo_to_profiler.clicked.connect(self.coordinateChangeODO2ProfilerRequested.emit)
        self.btn_odo_to_nodo.clicked.connect(self.coordinateChangeODO2NODORequested.emit)
        self.btn_nodo_to_odo.clicked.connect(self.coordinateChangeNODO2ODORequested.emit)
        self.btn_profiler_to_nodo.clicked.connect(self.coordinateChangeProfiler2NODORequested.emit)
        self.btn_nodo_to_profiler.clicked.connect(self.coordinateChangeNODO2ProfilerRequested.emit)

        # Add buttons to layout (2 rows × 3 columns)
        coord_layout.addWidget(self.btn_profiler_to_odo,      1, 0)
        coord_layout.addWidget(self.btn_odo_to_profiler,      2, 0)
        coord_layout.addWidget(self.btn_odo_to_nodo,          1, 1)
        coord_layout.addWidget(self.btn_nodo_to_odo,          2, 1)
        coord_layout.addWidget(self.btn_profiler_to_nodo,     1, 2)
        coord_layout.addWidget(self.btn_nodo_to_profiler,     2, 2)

        coord_group.setLayout(coord_layout)
        layout.addWidget(coord_group)

        # ---------------------------
        # Set Scan Bounds Group
        # ---------------------------
        for i in range(2):
            low = QDoubleSpinBox()
            low.setSizePolicy(QSizePolicy.Policy(7), QSizePolicy.Policy(0))
            low.setSuffix(f" {self.unit}")
            low.setRange(*self.limits[i])
            low.setDecimals(3)
            low.setValue(0)
            setattr(self, f'dim_{i}_low', low)
            high = QDoubleSpinBox()
            high.setSizePolicy(QSizePolicy.Policy(7), QSizePolicy.Policy(0))
            high.setSuffix(f" {self.unit}")
            high.setRange(*self.limits[i])
            high.setDecimals(3)
            high.setValue(0)
            setattr(self, f'dim_{i}_high', high)
        
        # For z-coordinate (dim_2)
        self.dim_2_low = QDoubleSpinBox()
        self.dim_2_low.setSizePolicy(QSizePolicy.Policy(7), QSizePolicy.Policy(0))
        self.dim_2_low.setSuffix(f" {self.unit}")
        self.dim_2_low.setRange(*self.limits[2])
        self.dim_2_low.setDecimals(3)
        self.dim_2_low.setValue(0)

        self.dim_2_high = QDoubleSpinBox()
        self.dim_2_high.setSizePolicy(QSizePolicy.Policy(7), QSizePolicy.Policy(0))
        self.dim_2_high.setSuffix(f" {self.unit}")
        self.dim_2_high.setRange(*self.limits[2])
        self.dim_2_high.setDecimals(3)
        self.dim_2_high.setValue(0)

        # create labels based on polarity
        polarity = [1 if '-' not in x else -1 for x in coordinate_plane]
        dim_0_low_label = QLabel('Z_start: ') if polarity[0] == 1 else QLabel('Z_end: ')
        dim_0_high_label = QLabel('Z_end: ') if polarity[0] == 1 else QLabel('Z_start: ')
        dim_1_low_label = QLabel('Y_start: ') if polarity[1] == 1 else QLabel('Y_end: ')
        dim_1_high_label = QLabel('Y_end: ') if polarity[0] == 1 else QLabel('Y_start: ')

        polarity_z = 1 if '-' not in self.coordinate_plane[2] else -1
        dim_2_low_label = QLabel('X_start') if polarity_z == 1 else QLabel('X_end')
        dim_2_high_label = QLabel('X_end') if polarity_z == 1 else QLabel('X_start')
        # add to layout
        # self.bounds_button = QRadioButton()
        # self.bounds_button.clicked.connect(lambda: setattr(self, 'mode', 'bounds'))
        # self.button_group.addButton(self.bounds_button)
        self.bounds_widget = create_widget(
                                        'VH',
                                        dim_0_low_label, self.dim_0_low,
                                        dim_0_high_label, self.dim_0_high,
                                        dim_1_low_label, self.dim_1_low,
                                        dim_1_high_label, self.dim_1_high,
                                        dim_2_low_label, self.dim_2_low,
                                        dim_2_high_label, self.dim_2_high
                                    )
        self.bounds_widget.layout().setAlignment(Qt.AlignLeft)
        # layout.addWidget(create_widget('H', self.bounds_button, self.bounds_widget))
        # layout.addWidget(self.bounds_widget)
        bounds_group = QGroupBox("Setup Scan Bounds")
        bounds_group.setStyleSheet("QGroupBox { border: 1px dashed gray; margin-top: 10px; padding: 5px; }")
        bounds_group.setStyleSheet("""
                    QGroupBox { border: 1px dashed gray; margin-top: 10px; padding: 5px; }
                    QGroupBox::title {
                        subcontrol-origin: margin;
                        subcontrol-position: top left;
                        padding: 0 3px;
                    }
                    """)

        bounds_layout = QVBoxLayout()
        bounds_layout.addWidget(self.bounds_widget)
        bounds_group.setLayout(bounds_layout)

        layout.addWidget(bounds_group)
        # layout.addWidget(line())


        # ---------------------------
        # Overlap + Anchor Group
        # ---------------------------
        self.overlap = QDoubleSpinBox()
        self.overlap.setRange(-100, 100)
        self.overlap.setValue(0)
        self.overlap.setSuffix(" %")
        overlap_widget = create_widget('H', QLabel('Overlap: '), self.overlap)
        overlap_widget.layout().setAlignment(Qt.AlignLeft)
        # layout.addWidget(overlap_widget)

        self.order = QComboBox()
        self.order.addItems(["row_wise_snake", "column_wise_snake", "spiral", "row_wise", "column_wise"])
        self.reverse = QCheckBox('Reverse')
        order_widget = create_widget('H', QLabel('Order: '), self.order, self.reverse)
        order_widget.layout().setAlignment(Qt.AlignLeft)
        # layout.addWidget(order_widget)

        self.relative_to = QComboBox()
        # create items based on polarity
        item = f"{'top' if polarity[1] == 1 else 'bottom'} {'left' if polarity[0] == 1 else 'right'}"
        self.relative_to.addItems(['center', item])
        relative_to_widget = create_widget('H', QLabel('Relative to: '), self.relative_to)
        relative_to_widget.layout().setAlignment(Qt.AlignLeft)
        # layout.addWidget(relative_to_widget)

        self.anchor_widgets = [QCheckBox(), QCheckBox(), QCheckBox()]
        self.grid_offset_widgets = [QDoubleSpinBox(), QDoubleSpinBox(), QDoubleSpinBox()]
        for i in range(3):
            box = self.grid_offset_widgets[i]
            box.setSizePolicy(QSizePolicy.Policy(7), QSizePolicy.Policy(0))
            box.setValue(self.fov_position[i])
            box.setDecimals(6)
            box.setRange(*self.limits[i])
            box.setSuffix(f" {unit}")
            box.valueChanged.connect(lambda: setattr(self, 'grid_offset', [self.grid_offset_widgets[0].value(),
                                                                           self.grid_offset_widgets[1].value(),
                                                                           self.grid_offset_widgets[2].value()]))
            box.setDisabled(True)

            self.anchor_widgets[i].toggled.connect(lambda enable, index=i: self.toggle_grid_position(enable, index))
        anchor_widget = create_widget('VH', QWidget(), QLabel('Anchor Grid: '),
                                      self.grid_offset_widgets[0], self.anchor_widgets[0],
                                      self.grid_offset_widgets[1], self.anchor_widgets[1],
                                      self.grid_offset_widgets[2], self.anchor_widgets[2], )
        anchor_widget.layout().setAlignment(Qt.AlignLeft)
        # layout.addWidget(anchor_widget)

        # --- Group overlap + anchor grid side by side ---
        overlap_anchor_group = QGroupBox("Setup Overlap and Anchor Grid")
        overlap_anchor_group.setStyleSheet("""
                            QGroupBox { border: 1px dashed gray; margin-top: 10px; padding: 5px; }
                            QGroupBox::title {
                                subcontrol-origin: margin;
                                subcontrol-position: top left;
                                padding: 0 3px;
                            }
                            """)


        # Create horizontal layout to place widgets side by side
        overlap_anchor_layout = QHBoxLayout()
        overlap_anchor_layout.addWidget(overlap_widget)
        overlap_anchor_layout.addWidget(anchor_widget)

        overlap_anchor_group.setLayout(overlap_anchor_layout)

        layout.addWidget(overlap_anchor_group)
        # ---------------------------

        # ---------------------------
        # Threshold Group
        # ---------------------------
        self.percentile_group = QGroupBox("Setup OTLS-ODO Bounding Box")
        self.percentile_group.setStyleSheet("""
            QGroupBox {
                border: 1px dashed gray;
                margin-top: 10px;
                padding: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
            }
        """)

        grid_layout = QGridLayout()

        # Row 0: Enable thresholding
        self.enable_thresholding_checkbox = QCheckBox("Enable thresholding")
        self.enable_thresholding_checkbox.setChecked(True)
        self.enable_thresholding_checkbox.stateChanged.connect(self.toggle_thresholding_group)
        grid_layout.addWidget(self.enable_thresholding_checkbox, 0, 0, 1, 2)

        # Row 1: Threshold percentile
        grid_layout.addWidget(QLabel("Threshold percentile:"), 1, 0)
        self.percentile_spinbox = QDoubleSpinBox()
        self.percentile_spinbox.setRange(0.0, 100.0)
        self.percentile_spinbox.setDecimals(1)
        self.percentile_spinbox.setValue(99.0)
        self.percentile_spinbox.setSuffix(" %")
        self.percentile_spinbox.setSingleStep(0.1)
        grid_layout.addWidget(self.percentile_spinbox, 1, 1)

        # Row 2: Enable largest object filter
        self.enable_filter_checkbox = QCheckBox("Enable largest object filter")
        self.enable_filter_checkbox.setChecked(False)
        self.enable_filter_checkbox.stateChanged.connect(self.toggle_largest_object_input)
        grid_layout.addWidget(self.enable_filter_checkbox, 2, 0)

        # Row 2: Number of objects
        self.num_largest_spinbox = QSpinBox()
        self.num_largest_spinbox.setRange(1, 1000)
        self.num_largest_spinbox.setValue(5)
        self.num_largest_spinbox.setEnabled(False)
        grid_layout.addWidget(self.num_largest_spinbox, 2, 1)

        # Row 1: Show new bounding box (aligned with percentile input)
        self.calculate_percentile_button = QPushButton("Show new bounding box")
        self.calculate_percentile_button.clicked.connect(self.calculate_percentile)
        grid_layout.addWidget(self.calculate_percentile_button, 1, 2)

        # Row 2: Show height maps
        self.show_heightmaps_button = QPushButton("Show height maps")
        self.show_heightmaps_button.clicked.connect(self.request_heightmaps_display.emit)
        grid_layout.addWidget(self.show_heightmaps_button, 2, 2)

        self.percentile_group.setLayout(grid_layout)
        layout.addWidget(self.percentile_group)
        self.percentile_group.setEnabled(False)  # Enable by default if checkbox is checked

        # ---------------------------
        # Surface Tracking Group
        # ---------------------------

        self.surface_tracking_group = QGroupBox("Setup OTLS-ODO Surface Tracking")
        self.surface_tracking_group.setStyleSheet("""
                                QGroupBox { border: 1px dashed gray; margin-top: 10px; padding: 5px; }
                                QGroupBox::title {
                                    subcontrol-origin: margin;
                                    subcontrol-position: top left;
                                    padding: 0 3px;
                                }
                                """)

        # Checkbox
        self.enable_surface_tracking_checkbox = QCheckBox("Enable surface tracking")
        self.enable_surface_tracking_checkbox.setChecked(False)
        self.enable_surface_tracking_checkbox.stateChanged.connect(self.surface_tracking)

        self.enable_sync_tracking_checkbox = QCheckBox("Enable sync calculation")
        self.enable_sync_tracking_checkbox.setChecked(False)
        self.enable_sync_tracking_checkbox.stateChanged.connect(self.sync_tracking)

        # Surface tracking model selector
        self.surface_tracking_model_combo = QComboBox()
        self.surface_tracking_model_combo.addItems(["A* test", "A*", "A* sync", "D*"])

        # Model Parameters dropdown (ComboBox)
        # self.model_parameters_label = QLabel("Model Parameters:")
        self.model_parameters_combo = QComboBox()
        self.model_parameters_combo.addItems(["astar-32px-coarsespacing-50Hz", "astar-32px-finespacing-50Hz", "astar-32px-finespacing", "astar-32px-coarsespacing", "astar-128px", "astar-128px-live"])

        # Generate path button
        self.generate_surface_path_button = QPushButton("Generate Surface Tracking Path")
        self.generate_surface_path_button.clicked.connect(self.generate_surface_tracking_path)

        self.generate_feedforward_path_button = QPushButton("Generate Feedforward Path")
        self.generate_feedforward_path_button.clicked.connect(self.generate_feedforward_path)

        self.display_path_button = QPushButton("Display Path")
        self.display_path_button.clicked.connect(self.generate_path_display)

        # Layouts
        surface_tracking_layout = QVBoxLayout()

        # Row 1 → both checkboxes on the same row
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(5)
        row1_layout.addWidget(self.enable_surface_tracking_checkbox)
        row1_layout.addWidget(self.enable_sync_tracking_checkbox)
        surface_tracking_layout.addLayout(row1_layout)

        # Row 2 → both dropdowns on the next row
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(5)
        row2_layout.addWidget(self.surface_tracking_model_combo)
        row2_layout.addWidget(self.model_parameters_combo)
        surface_tracking_layout.addLayout(row2_layout)

        # Row 3 → buttons
        row3_layout = QHBoxLayout()
        row3_layout.setSpacing(5)
        row3_layout.addWidget(self.generate_surface_path_button)
        row3_layout.addWidget(self.generate_feedforward_path_button)
        row3_layout.addWidget(self.display_path_button)
        surface_tracking_layout.addLayout(row3_layout)

        self.surface_tracking_group.setLayout(surface_tracking_layout)
        layout.addWidget(self.surface_tracking_group)
        self.surface_tracking_group.setEnabled(True)
        # ---------------------------


        # ---------------------------
        # Live Surface Tracking Group
        # ---------------------------

        self.live_tracking_group = QGroupBox("Setup Live Surface Tracking")
        self.live_tracking_group.setStyleSheet("""
            QGroupBox { border: 1px dashed gray; margin-top: 10px; padding: 5px; }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
            }
        """)

        # Checkbox (Row 1)
        self.enable_live_tracking_checkbox = QCheckBox("Enable live tracking")
        self.enable_live_tracking_checkbox.setChecked(False)
        self.enable_live_tracking_checkbox.stateChanged.connect(self.live_tracking)

        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(5)
        row1_layout.addWidget(self.enable_live_tracking_checkbox)

        # Row 2: Stride + Offset
        self.stride_label = QLabel("Stride (frames):")
        self.set_stride = QSpinBox()
        self.set_stride.setRange(0, 1000)
        self.set_stride.setSingleStep(1)
        self.set_stride.setValue(5)
        self.set_stride.valueChanged.connect(self.strideChanged.emit)

        self.offset_label = QLabel("Offset (µm):")
        self.set_offset = QDoubleSpinBox()
        self.set_offset.setDecimals(2)
        self.set_offset.setRange(-1000.0, 1000.0)
        self.set_offset.setSingleStep(1.0)
        self.set_offset.setValue(0.0)
        self.set_offset.valueChanged.connect(self.offsetChanged.emit)

        # New: Position (X-start) input
        self.position_label = QLabel("Start at X (mm):")
        self.set_position = QDoubleSpinBox()
        self.set_position.setDecimals(3)
        self.set_position.setRange(-200.0, 200.0)
        self.set_position.setSingleStep(1.0)
        self.set_position.setValue(0.0)
        self.set_position.valueChanged.connect(self.positionChanged.emit)

        # Layout for stride + offset + position
        row2_layout = QHBoxLayout()
        row2_layout.addWidget(self.stride_label)
        row2_layout.addWidget(self.set_stride)
        row2_layout.addWidget(self.offset_label)
        row2_layout.addWidget(self.set_offset)
        row2_layout.addWidget(self.position_label)
        row2_layout.addWidget(self.set_position)

        # Combine into main layout
        live_tracking_layout = QVBoxLayout()
        live_tracking_layout.addLayout(row1_layout)
        live_tracking_layout.addLayout(row2_layout)

        self.live_tracking_group.setLayout(live_tracking_layout)
        layout.addWidget(self.live_tracking_group)
        self.live_tracking_group.setEnabled(True)

        # ---------------------------

        self.apply_all_box = QCheckBox('Apply to all: ')
        self.apply_all_box.setChecked(True)
        self.apply_all_box.toggled.connect(lambda checked: setattr(self, 'apply_all', checked))
        # layout.addWidget(self.apply_all_box)

        # connect widgets to trigger on_change when toggled
        self.dim_1_high.valueChanged.connect(self._on_change)
        self.dim_0_high.valueChanged.connect(self._on_change)
        self.dim_1_low.valueChanged.connect(self._on_change)
        self.dim_0_low.valueChanged.connect(self._on_change)
        self.dim_2_high.valueChanged.connect(self._on_change)
        self.dim_2_low.valueChanged.connect(self._on_change)

        # self.rows.valueChanged.connect(self._on_change)
        # self.columns.valueChanged.connect(self._on_change)
        # self.area_width.valueChanged.connect(self._on_change)
        # self.area_height.valueChanged.connect(self._on_change)
        self.overlap.valueChanged.connect(self._on_change)
        self.order.currentIndexChanged.connect(self._on_change)
        self.relative_to.currentIndexChanged.connect(self._on_change)
        self.reverse.toggled.connect(self._on_change)

        # create table portion
        self.table_columns = ['row, column', *[f'{x} [{unit}]' for x in self.coordinate_plane],
                              f'{self.coordinate_plane[2]} max [{unit}]', 'visibility']
        self.tile_table = QTableWidget()
        # configure and set header
        self.header = QStartStopTableHeader(self.tile_table)     # header object that allows user to specify start/stop tile
        self.header.startChanged.connect(lambda index: setattr(self, 'start', index))
        self.header.stopChanged.connect(lambda index: setattr(self, 'stop', index))

        self.tile_table.setVerticalHeader(self.header)

        self.tile_table.setColumnCount(len(self.table_columns))
        self.tile_table.setHorizontalHeaderLabels(self.table_columns)
        self.tile_table.resizeColumnsToContents()
        for i in range(1, len(self.table_columns)):  # skip first column
            column_name = self.tile_table.horizontalHeaderItem(i).text()
            delegate = QSpinItemDelegate()
            # table does not take ownership of the delegates, so they are removed from memory as they
            # are local variables causing a Segmentation fault. Need to be attributes
            setattr(self, f'table_column_{column_name}_delegate', delegate)
            self.tile_table.setItemDelegateForColumn(i, delegate)

        self.tile_table.itemChanged.connect(self.tile_table_changed)

        layout.addWidget(self.tile_table)

        widget = QWidget()
        widget.setLayout(layout)

        self.setCentralWidget(widget)

        self.mode = 'bounds'  # initialize mode
        self.update_tile_table(self.value())  # initialize table


        # ---------------------------
        # Loading bounding boxes
        # ---------------------------
        # self.load_xml_button = QPushButton("Load Bounding Boxes")
        # self.load_xml_button.clicked.connect(self.load_bounding_boxes)
        # layout.addWidget(self.load_xml_button)
        # self.bounding_box_dropdown = QComboBox()
        # self.bounding_box_dropdown.addItem("Select Bounding Box")
        # self.bounding_box_dropdown.currentIndexChanged.connect(self.bounding_box_selected)
        # layout.addWidget(self.bounding_box_dropdown)

        # Load button
        self.load_xml_button = QPushButton("Load Bounding Boxes")
        # self.load_xml_button.clicked.connect(self.loadBoundingBoxesRequested.emit)  # emits signal to trigger external logic
        self.load_xml_button.clicked.connect(self.save_drawn_bounding_boxes)
        layout.addWidget(self.load_xml_button)
        self.bounding_box_dropdown = QComboBox()
        # self.bounding_box_dropdown.addItem("Select Bounding Box")  # Placeholder
        self.bounding_box_dropdown.currentIndexChanged.connect(self.bounding_box_selected)
        layout.addWidget(self.bounding_box_dropdown)

    def _update_initial_reference(self, ref: tuple):
        print(f"Volume plan received updated initial reference: {ref}")
        self.current_initial_reference = ref

    def save_drawn_bounding_boxes(self):
        viewer = self.instrument_view.viewer

        # Find the Shapes layer with rectangles
        shapes_layers = [
            layer for layer in viewer.layers
            if layer.__class__.__name__ == 'Shapes'
            and any(s == 'rectangle' for s in layer.shape_type)
        ]

        if not shapes_layers:
            print("No rectangle shapes layer found.")
            return

        shapes = shapes_layers[0]
        rectangles = shapes.data
        self.saved_bounding_boxes = [r.tolist() for r in rectangles]
        print("Saved bounding boxes:", self.saved_bounding_boxes)

        # Ask user for save location
        default_name = "ODO_bounding_boxes.csv"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save bounding boxes",
            default_name,
            filter="CSV Files (*.csv)"
        )
        if not save_path:
            print("Save cancelled.")
            return

        # Write Napari shapes CSV format
        with open(save_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["index", "shape-type", "vertex-index", "axis-0", "axis-1", "axis-2"])

            for shape_index, rectangle in enumerate(self.saved_bounding_boxes):
                for vertex_index, vertex in enumerate(rectangle):
                    z, y, x = vertex
                    writer.writerow([shape_index, "rectangle", vertex_index, z, y, x])

        print(f"Bounding boxes saved to {save_path}")

        # === Now update the dropdown immediately ===
        calibration = getattr(self.acquisition_view, "odo_calibration", None)
        if calibration is None:
            raise RuntimeError("ODO calibration is not available from the acquisition view.")
        pixel_size_um = float(calibration.pixel_size_um)
        um_to_mm = 1e-3
        pixel_size_mm = pixel_size_um * um_to_mm

        # Determine image height from viewer shape
        image_height_px = viewer.layers[0].data.shape[1]

        if self.current_initial_reference is not None:
            ref_scanmin, ref_width_center = self.current_initial_reference
        else:
            print("⚠️ No initial boundary reference found! Assuming scan and width start from 0.")
            ref_scanmin = 0.0
            ref_width_center = 0.0

        odo_fov_y_mm = float(calibration.full_fov_mm)
        nodo_fov_y_mm = float(
            self.instrument_view.config["acquisition_view"]["fov_dimensions_new"]["NODO_camera"][1]
        )
        width_offset = odo_fov_y_mm - nodo_fov_y_mm
        scan_offset1 = 2
        scan_offset2 = 1
        ref_width_max = ref_width_center + width_offset

        bounding_boxes_mm = []

        for rect in self.saved_bounding_boxes:
            ys = [v[1] for v in rect]  # axis-1 = Y
            xs = [v[2] for v in rect]  # axis-2 = X

            # Scan axis (X, axis-2)
            scanmin = round(min(xs) * pixel_size_mm + ref_scanmin, 3)-scan_offset1
            scanmax = round(max(xs) * pixel_size_mm + ref_scanmin, 3)+scan_offset2

            # Width axis (Y, axis-1) → flipped, then offset from ref_width_max
            # flipped_ys = [image_height_px - y for y in ys]
            # widthmin = round(ref_width_max - max(flipped_ys) * pixel_size_mm, 3)
            # widthmax = round(ref_width_max - min(flipped_ys) * pixel_size_mm, 3)
            widthmin = round(ref_width_max - max(ys) * pixel_size_mm, 3)
            widthmax = round(ref_width_max - min(ys) * pixel_size_mm, 3)

            bounding_boxes_mm.append((scanmin, scanmax, widthmin, widthmax))

        self.update_bounding_box_dropdown(bounding_boxes_mm)


    def update_bounding_box_dropdown(self, bounding_boxes):
        self.bounding_boxes = bounding_boxes
        self.bounding_box_dropdown.clear()
        self.bounding_box_dropdown.addItem("Select Bounding Box")
        for i, bbox in enumerate(bounding_boxes):
            scanmin, scanmax, widthmin, widthmax = bbox
            label = f"bbox {i+1}: scan=({scanmin}-{scanmax} mm), width=({widthmin}-{widthmax} mm)"
            self.bounding_box_dropdown.addItem(label)

    def live_tracking(self, state):
        enabled = state == Qt.Checked
        self.livetrackingRequested.emit(enabled)
        # print("Live_tracking enabled", enabled)
        self.set_stride.setEnabled(enabled)

    def generate_feedforward_path(self):
        model_param = self.model_parameters_combo.currentText()
        self.feedforwardpathRequested.emit(model_param)

    def generate_path_display(self):
        model_param = self.model_parameters_combo.currentText()
        self.pathdisplayRequested.emit(model_param)

    def generate_surface_tracking_path(self):
        model = self.surface_tracking_model_combo.currentText()
        model_param = self.model_parameters_combo.currentText()
        self.surfaceTrackingPathGenerated.emit(model, model_param)
    
    def toggle_thresholding_group(self, state):
        enabled = state == Qt.Checked
        for child in self.percentile_group.findChildren(QWidget):
            if child is not self.enable_thresholding_checkbox:
                child.setEnabled(enabled)
        self.enable_thresholding.emit(enabled)

    def toggle_largest_object_input(self, state):
        """
        Enable or disable the largest objects spinbox based on checkbox.
        """
        enabled = state == Qt.Checked
        self.num_largest_spinbox.setEnabled(enabled)
        self.enable_filter_changed.emit(enabled)

    def surface_tracking(self, state):
        enabled = state == Qt.Checked
        self.enable_surface_tracking.emit(enabled)
        self.enable_sync_tracking_checkbox.setEnabled(enabled)
        self.surface_tracking_model_combo.setEnabled(enabled)
        self.generate_surface_path_button.setEnabled(enabled)
        self.display_path_button.setEnabled(enabled)
        self.generate_feedforward_path_button.setEnabled(enabled)
        self.live_tracking_group.setEnabled(enabled)
    
    def sync_tracking(self, state):
        enabled = state == Qt.Checked
        self.enable_sync_tracking.emit(enabled)
    
    def calculate_percentile(self):
        # Example function to be triggered by button
        percentile = self.percentile_spinbox.value()
        num_largest = self.num_largest_spinbox.value()
        print(f"[VolumePlanWidget] Requesting boundary with percentile: {percentile}%")
        self.request_boundary_calculation.emit(percentile, num_largest)
    
    def update_coordinate_status(self, new_coord: str):
        self.current_coordinate_system = new_coord
        self.coordinate_status_label.setText(f"Current Coordinate: {new_coord}")
    
    def coordinate_change_ODO_2_Profiler(self):
        print("Custom Action 1 triggered")

    def coordinate_change_Profiler_2_ODO(self):
        print("Custom Action 2 triggered")

    def bigstitcher_to_stage_position(self, bigstitcher_x, bigstitcher_y, bigstitcher_z):
        # TODO: Make this not a hard code
        size_x = 0.18  # μm
        size_y = 0.18  # μm
        size_z = 0.18  # μm
        theta_deg = 74.0  # degrees
        
        # Calculate effective voxel size in y-direction
        theta_rad = np.deg2rad(theta_deg)
        size_y_eff = size_y * np.cos(theta_rad)
        
        # Scaling factors
        scale_x = size_x / size_y_eff
        scale_y = 1.0
        scale_z = size_z / size_y_eff
        
        # Invert the shift equations
        x_position_mm = (size_x * bigstitcher_x) / (scale_x * 1000)
        y_position_mm = -(size_y_eff * bigstitcher_y) / (scale_y * 1000)
        z_position_mm = -(size_z * bigstitcher_z) / (scale_z * 1000)
    
        return x_position_mm, y_position_mm, z_position_mm
    
    # def bounding_box_selected(self, index):
    #     if index == 0:
    #         return  # "Select Bounding Box" selected
    #     name = self.bounding_box_dropdown.currentText()
    #     bbox = self.bounding_boxes[name]
    #     min_coords = bbox['min']
    #     min_coords = [min_coords[2], min_coords[0], min_coords[1]]
    #     max_coords = bbox['max']
    #     max_coords = [max_coords[2], max_coords[0], max_coords[1]]

    #     # Convert coordinates using your function
    #     stage_min = self.bigstitcher_to_stage_position(*min_coords)
    #     stage_max = self.bigstitcher_to_stage_position(*max_coords)

    #     # Update the bounds widget min and max coordinates
    #     # Assuming dim_0 corresponds to X, dim_1 to Y, dim_2 to Z
    #     self.dim_0_low.setValue(stage_min[2])  # Z_start
    #     self.dim_0_high.setValue(stage_max[2])  # z_end
    #     self.dim_1_low.setValue(stage_min[1])  # Y_start
    #     self.dim_1_high.setValue(stage_max[1])  # Y_end
    #     self.dim_2_low.setValue(stage_min[0])  # x_start
    #     self.dim_2_high.setValue(stage_max[0])  # x_end

    #     # Switch to bounds mode if not already in that mode
    #     if self.mode != 'bounds':
    #         self.mode = 'bounds'

    #     # Trigger an update
    #     self._on_change()

    def bounding_box_selected(self, index):
        if index <= 0:
            return  # "Select Bounding Box" placeholder selected
        if not hasattr(self, "bounding_boxes"):
            return
        if not self.bounding_boxes:
            return
        if (index - 1) >= len(self.bounding_boxes):
            return

        # Get bbox tuple from list using (index - 1) to account for placeholder
        bbox = self.bounding_boxes[index - 1]
        scanmin, scanmax, widthmin, widthmax = bbox

        self.dim_2_low.setValue(scanmin)
        self.dim_2_high.setValue(scanmax)
        self.dim_1_low.setValue(widthmin)
        self.dim_1_high.setValue(widthmax)
        self._on_change()

    def update_tile_table(self, value: Union[GridRowsColumns, GridFromEdges, GridWidthHeight]) -> None:
        """
        Update tile table when value changes
        :param value: newest value containing details of scan
        """

        # check if order changed
        table_order = [[int(x) for x in self.tile_table.item(i, 0).text() if x.isdigit()] for i in
                       range(self.tile_table.rowCount())]
        value_order = [[t.row, t.col] for t in value]
        order_matches = np.array_equal(table_order, value_order)
        if not order_matches:
            self.refill_table()
            return

        # check if tile positions match
        table_pos = [[self.tile_table.item(j, i).data(Qt.EditRole) for i in range(1, 4)] for j in
                     range(self.tile_table.rowCount())]
        value_pos = self.tile_positions
        pos_matches = np.array_equal(table_pos, value_pos)
        if not pos_matches:
            self.refill_table()
            return

        # TODO: Fix this?
        # # check if visibility matches
        # table_vis = [self.tile_table.item(i, self.table_columns.index('visibility')).data(Qt.EditRole) for i in
        #              range(self.tile_table.rowCount())]
        # value_vis = [self._tile_visibility[t.row, t.col] for t in value]
        # vis_matches = (table_vis == value_vis).all()
        # if not vis_matches:
        #     self.refill_table()
        #     return

    def refill_table(self) -> None:
        """Function to clear and populate tile table with current tile configuration"""
        value = self.value()
        self.tile_table.clearContents()
        self.tile_table.setRowCount(0)
        for tile in value:
            self.add_tile_to_table(tile.row, tile.col)
        self.header.blockSignals(True)   # don't trigger update
        if self.start is not None:
            self.header.set_start(self.start)
        if self.stop is not None:
            self.header.set_stop(self.stop)
        self.header.blockSignals(False)

    def add_tile_to_table(self, row: int, column: int) -> None:
        """
        Add a configured tile into tile_table
        :param row: row of tile
        :param column: column of value
        """

        self.tile_table.blockSignals(True)
        # add new row to table
        table_row = self.tile_table.rowCount()
        self.tile_table.insertRow(table_row)

        # Determine if we should reverse the scan direction
        z_start = self._scan_starts[row, column]
        z_end = self._scan_ends[row, column]
        if self.serpentine_scan and row % 2 == 1:
            z_start, z_end = z_end, -z_end

        kwargs = {
            'row, column': [row, column],
            f'{self.coordinate_plane[0]} [{self.unit}]': self.tile_positions[row, column][0],
            f'{self.coordinate_plane[1]} [{self.unit}]': self.tile_positions[row, column][1]-self._fov_dimensions[1],
            f'{self.coordinate_plane[2]} [{self.unit}]': z_start,
            f'{self.coordinate_plane[2]} max [{self.unit}]': z_end
        }

        # kwargs = {'row, column': [row, column],
        #           f'{self.coordinate_plane[0]} [{self.unit}]': self.tile_positions[row, column][0],
        #           f'{self.coordinate_plane[1]} [{self.unit}]': self.tile_positions[row, column][1],
        #           f'{self.coordinate_plane[2]} [{self.unit}]': self._scan_starts[row, column],
        #           f'{self.coordinate_plane[2]} max [{self.unit}]': self._scan_ends[row, column]}

        items = {}
        for header_col, header in enumerate(self.table_columns[:-1]):
            item = QTableWidgetItem()
            if header == 'row, column':
                item.setText(str([row, column]))
            else:
                value = float(kwargs[header])
                item.setData(Qt.EditRole, value)
            items[header] = item
            self.tile_table.setItem(table_row, header_col, item)

        # disable cells
        disable = list(kwargs.keys())
        if not self.apply_all or (row, column) == (0, 0):
            disable.remove(f'{self.coordinate_plane[2]} max [{self.unit}]')
            if self.anchor_widgets[2].isChecked() or not self.apply_all:
                disable.remove(f'{self.coordinate_plane[2]} [{self.unit}]')
        flags = QTableWidgetItem().flags()
        flags &= ~Qt.ItemIsEditable
        for var in disable:
            items[var].setFlags(flags)

        # add in QCheckbox for visibility
        visible = QCheckBox('Visible')
        visible.setChecked(bool(self._tile_visibility[row, column]))
        visible.toggled.connect(lambda checked: self.toggle_visibility(checked, row, column))
        visible.setEnabled(not all([self.apply_all, (row, column) != (0, 0)]))
        self.tile_table.setCellWidget(table_row, self.table_columns.index('visibility'), visible)

        self.tile_table.blockSignals(False)

    def toggle_visibility(self, checked: bool, row: int, column: int) -> None:
        """
        Handle visibility checkbox being toggled
        :param checked: check state of checkbox
        :param row: row of tile
        :param column: column of tile
        """

        self._tile_visibility[row, column] = checked
        if self.apply_all and [row, column] == [0, 0]:  # trigger update of all subsequent checkboxes
            for r in range(self.tile_table.rowCount()):
                self.tile_table.cellWidget(r, self.table_columns.index('visibility')).setChecked(checked)
            self.valueChanged.emit(self.value())  # emit value changes at end of changes

        elif not self.apply_all:
            self.valueChanged.emit(self.value())

    def tile_table_changed(self, item: QTableWidgetItem) -> None:
        """
        Update values if item is changed
        :param item: item that has been changed
        """

        row, column = [int(x) for x in self.tile_table.item(item.row(), 0).text() if x.isdigit()]
        col_title = self.table_columns[item.column()]
        titles = [f'{self.coordinate_plane[2]} [{self.unit}]', f'{self.coordinate_plane[2]} max [{self.unit}]']
        if col_title in titles:
            value = item.data(Qt.EditRole)
            array = self._scan_starts if col_title == titles[0] else self._scan_ends
            array[row, column] = value

            if self.apply_all and [row, column] == [0, 0]:  # trigger update of all subsequent tiles
                for r in range(self.tile_table.rowCount()):
                    self.tile_table.item(r, item.column()).setData(Qt.EditRole, value)
                self.valueChanged.emit(self.value())  # emit value changes at end of changes

            elif not self.apply_all:
                self.valueChanged.emit(self.value())

            if col_title == f'{self.coordinate_plane[2]} [{self.unit}]':
                self.grid_offset_widgets[2].setValue(value)

    def toggle_grid_position(self, enable: bool, index: Literal[0, 1, 2]) -> None:
        """
        Function connected to the anchor checkboxes. If grid is anchored, allow user to input grid position
        :param enable: State checkbox was toggled to
        :param index: Index of what anchor was checked (0-2)
        """

        self.grid_offset_widgets[index].setEnabled(enable)
        if not enable:  # Graph is not anchored
            self.grid_offset_widgets[index].setValue(self.fov_position[index])
        self._on_change()
        if not enable:
            self.refill_table()  # order, pos, and visibilty doesn't change, so update table to reconfigure editablility

    @property
    def apply_all(self) -> bool:
        """
        Return boolean specifying if settings for the 0, 0 tile apply to all tiles
        :return: boolean specifying if settings for the 0, 0 tile apply to all tiles
        """
        return self._apply_all

    @apply_all.setter
    def apply_all(self, value: bool) -> None:
        """
        Setting for the 0, 0 tile apply all. If True, will update all tiles
        :param value: boolean to set apply all
        """

        self._apply_all = value

        # correctly configure anchor and grid_offset_widget
        self.anchor_widgets[2].setEnabled(value)
        self.grid_offset_widgets[2].setEnabled(value and self.anchor_widgets[2].isChecked())

        # update values if apply_all applied
        if value:
            self.blockSignals(True)  # emit signal only once
            self.toggle_visibility(self.tile_visibility[0, 0], 0, 0)
            tile_zero_row = self.tile_table.findItems('[0, 0]', Qt.MatchExactly)[0].row()
            start_i = self.table_columns.index(f'{self.coordinate_plane[2]} [{self.unit}]')
            end_i = self.table_columns.index(f'{self.coordinate_plane[2]} max [{self.unit}]')
            self.tile_table_changed(self.tile_table.item(tile_zero_row, start_i))
            self.tile_table_changed(self.tile_table.item(tile_zero_row, end_i))
            self.blockSignals(False)

        self._on_change()
        self.refill_table()  # order, pos, and visibilty doesn't change, so update table to reconfigure editablility

    @property
    def fov_position(self) -> list[float, float, float]:
        """
        Current position of the field of view in the specified unit
        :return: list of length 3 specifying current position of fov
        """
        return self._fov_position

    @fov_position.setter
    def fov_position(self, value: list[float, float, float]) -> None:
        """
        Set the current position of the field of view in the specified unit
        :param value: list of length 3 specifying new position of fov
        """
        if type(value) is not list and len(value) != 3:
            raise ValueError
        elif value != self._fov_position:
            self._fov_position = value
            for anchor, pos, val in zip(self.anchor_widgets, self.grid_offset_widgets, value):
                if not anchor.isChecked() and anchor.isEnabled():
                    self.blockSignals(True)  # only emit valueChanged once at end
                    pos.setValue(val)
                    self.blockSignals(False)

            self._on_change()

    @property
    def fov_dimensions(self) -> list[float, float, float]:
        """
        Returns current field of view dimensions
        :return: list of 3 floats defining the field of view dimensions
        """
        return self._fov_dimensions

    @fov_dimensions.setter
    def fov_dimensions(self, value: list[float, float, float]) -> None:
        """
        Setting the fov dimension in the specified unit
        :param value: list of length 3 specifying dimension for field of view
        """
        if type(value) is not list and len(value) != 2:
            raise ValueError
        self._fov_dimensions = value
        self._on_change()

    @property
    def grid_offset(self) -> list[float, float, float]:
        """Returns off set from 0 of tile positions"""
        return self._grid_offset

    @grid_offset.setter
    def grid_offset(self, value: list[float, float, float]) -> None:
        """
        Setting offset from 0 of tile positions in the 3 dimensions of coordinate plane
        :param value: a list of len 3 specifying offset for tile starts
        """
        if type(value) is not list and len(value) != 3:
            raise ValueError
        self._grid_offset = value
        self._scan_starts[:, :] = value[2]
        self._on_change()

    # @property
    # def tile_positions(self) -> [[float, float, float]]:
    #     """
    #     Creates 3d list of tile positions based on widget values
    #     :return: 3D list of tile coordinates
    #     """

    #     value = self.value()
    #     coords = np.zeros((value.rows, value.columns, 3))
    #     if self._mode != "bounds":
    #         for tile in value:
    #             coords[tile.row, tile.col, :] = [tile.x + self.grid_offset[0],
    #                                           tile.y + self.grid_offset[1],
    #                                           self._scan_starts[tile.row][tile.col]]
    #     else:
    #         for tile in value:
    #             coords[tile.row, tile.col, :] = [tile.x, tile.y, self._scan_starts[tile.row][tile.col]]
    #     return coords

    @property
    def tile_positions(self) -> [[float, float, float]]:
        """
        Creates 3D list of tile positions based on widget values
        :return: 3D list of tile coordinates
        """
        value = self.value()
        tile_rows = [tile.row for tile in value]
        tile_cols = [tile.col for tile in value]
        max_row = max(tile_rows)
        max_col = max(tile_cols)
        coords = np.zeros((max_row + 1, max_col + 1, 3))

        if self._mode != "bounds":
            for tile in value:
                coords[tile.row, tile.col, :] = [
                    tile.x + self.grid_offset[0],
                    tile.y + self.grid_offset[1],
                    self._scan_starts[tile.row][tile.col],
                ]
        else:
            for tile in value:
                coords[tile.row, tile.col, :] = [
                    tile.x,
                    tile.y,
                    self._scan_starts[tile.row][tile.col],
                ]
        return coords



    @property
    def tile_visibility(self) -> np.ndarray:
        """
        2D matrix of boolean values specifying if tile should be visible
        :return: 2D numpy array containing the start coordinates where the i, j position of start coordinates correlates
        to the i, j position of tile in scan
        """
        return self._tile_visibility

    @property
    def scan_starts(self) -> np.ndarray:
        """
        2D matrix of tile start position in scan dimension
        :return: 2D numpy array containing the start coordinates where the i, j position of start coordinates correlates
        to the i, j position of tile in scan
        """
        return self._scan_starts

    @property
    def scan_ends(self) -> np.ndarray:
        """
        2D matrix of tile start position in scan dimension
        :return: 2D numpy array containing the end coordinates where the i, j position of end coordinates correlates to
        the i, j position of tile in scan
        """
        return self._scan_ends

    # def _on_change(self) -> None:
    #     """
    #     Function called when things are changed within the widget. Handles formatting start, end, and visibility
    #     of tiles and emits signal when done.
    #     """
    #     if (val := self.value()) is None:
    #         return  # pragma: no cover
    #     # update sizes of arrays
    #     if (val.rows, val.columns) != self._scan_starts.shape:
    #         self._tile_visibility = np.resize(self._tile_visibility, [val.rows, val.columns])
    #         self._scan_starts = np.resize(self._scan_starts, [val.rows, val.columns])
    #         self._scan_ends = np.resize(self._scan_ends, [val.rows, val.columns])
    #     self.update_tile_table(val)
    #     self.valueChanged.emit(val)

    def _on_change(self) -> None:
        """
        Function called when things are changed within the widget. Handles formatting start, end, and visibility
        of tiles and emits signal when done.
        """
        if (val := self.value()) is None:
            return  # pragma: no cover

        # Calculate max indices
        tile_rows = [tile.row for tile in val]
        tile_cols = [tile.col for tile in val]
        max_row = max(tile_rows)
        max_col = max(tile_cols)

        # Update sizes of arrays based on max indices
        if (max_row + 1, max_col + 1) != self._scan_starts.shape:
            self._tile_visibility = np.resize(self._tile_visibility, [max_row + 1, max_col + 1])
            self._scan_starts = np.resize(self._scan_starts, [max_row + 1, max_col + 1])
            self._scan_ends = np.resize(self._scan_ends, [max_row + 1, max_col + 1])

        # Only update _scan_starts and _scan_ends if mode is 'bounds'
        if self._mode == 'bounds':
            if self.apply_all:
                self._scan_starts[:, :] = self.dim_2_low.value()
                self._scan_ends[:, :] = self.dim_2_high.value()
            else:
                # Only update the first tile
                self._scan_starts[0, 0] = self.dim_2_low.value()
                self._scan_ends[0, 0] = self.dim_2_high.value()
        elif self._mode == 'number':
            # Reset to current stage position
            current_z = self.fov_position[2]
            if self.apply_all:
                self._scan_starts[:, :] = current_z
            else:
                self._scan_starts[0, 0] = current_z

        self.update_tile_table(val)
        self.valueChanged.emit(val)


    @property
    def mode(self) -> Literal['bounds']:
        """Mode used to calculate tile position
        :return: current mode of widget
        """
        return self._mode

    @mode.setter
    def mode(self, value: Literal['bounds']) -> None:
        """
        Set mode of widget
        :param value: value to change mode to. Must be 'number', 'area', or 'bounds'
        """

        if value not in ['bounds']:
            raise ValueError
        self._mode = value

        # getattr(self, f'{value}_button').setChecked(True)

        for mode in ['bounds']:
            getattr(self, f'{mode}_widget').setEnabled(value == mode)

        for i in range(3):
            anchor, pos = self.anchor_widgets[i], self.grid_offset_widgets[i]
            anchor_enable = value != 'bounds' if i != 2 else value != 'bounds' and self.apply_all
            anchor.setEnabled(anchor_enable)
            pos_enable = anchor_enable and anchor.isChecked()
            pos.setEnabled(pos_enable)

        self._on_change()

    def value(self) -> Union[GridRowsColumns, GridFromEdges, GridWidthHeight]:
        """
        Value based on widget values
        :return: value containing information about tiles
        """
        over = self.overlap.value()
        common = {
            "reverse": False,
            "overlap": (over, over),
            # "mode": self.order.currentText(),
            "mode": "row_wise_snake",
            "fov_width": self.fov_dimensions[0],
            "fov_height": self.fov_dimensions[1],
        }
        if self._mode == 'number':
            return GridRowsColumns(
                rows=self.rows.value(),
                columns=self.columns.value(),
                relative_to='center' if self.relative_to.currentText() == 'center' else "top_left",
                **common,
            )
        elif self._mode == 'bounds':
            return GridFromEdges(
                top=self.dim_1_high.value(),
                left=self.dim_0_low.value(),
                bottom=self.dim_1_low.value(),
                right=self.dim_0_high.value(),
                z_start=self.dim_2_low.value(),
                z_end=self.dim_2_high.value(),
                **common,
            )
        elif self._mode == 'area':
            return GridWidthHeight(
                width=self.area_width.value(),
                height=self.area_height.value(),
                relative_to='center' if self.relative_to.currentText() == 'center' else "top_left",
                **common,
            )
        raise NotImplementedError


def line():
    frame = QFrame()
    frame.setFrameShape(QFrame.HLine)
    return frame
