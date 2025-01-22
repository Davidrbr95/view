# visualization_widget.py

from qtpy.QtWidgets import QWidget, QVBoxLayout
import napari
import numpy as np

class VisualizationWidget(QWidget):
    """Widget for displaying the volume and scanning progress."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Create Napari viewer
        self.viewer = napari.Viewer()
        layout.addWidget(self.viewer.window.qt_viewer)

        # Layers for visualization
        self.survey_points_layer = self.viewer.add_points(
            [], size=1, face_color='yellow', name='Survey Points'
        )
        self.boundary_points_layer = self.viewer.add_points(
            [], size=1, face_color='red', name='Boundary Points'
        )
        self.scan_pattern_layer = None  # Will be added when displaying scan pattern
        self.voi_layer = None  # Will be added when displaying VOI

    def update_survey_point(self, point):
        """Update survey points layer."""
        data = self.survey_points_layer.data.tolist()
        data.append(point)
        self.survey_points_layer.data = data

    def update_boundary_point(self, point):
        """Update boundary points layer."""
        data = self.boundary_points_layer.data.tolist()
        data.append(point)
        self.boundary_points_layer.data = data

    def display_scan_pattern(self, points):
        """Display the planned scan pattern in the viewer."""
        if self.scan_pattern_layer:
            self.viewer.layers.remove(self.scan_pattern_layer)
        self.scan_pattern_layer = self.viewer.add_points(
            points,
            size=1,
            face_color='blue',
            name='Planned Scan Pattern',
            opacity=0.5,
        )

    def display_voi(self, boundaries):
        """Display the volume of interest as a wireframe box."""
        # Remove existing VOI layer if it exists
        if self.voi_layer:
            self.viewer.layers.remove(self.voi_layer)

        # Extract boundaries
        (x_start, x_end), (y_start, y_end), (z_start, z_end) = boundaries

        # Define the 8 corners of the box
        corners = np.array([
            [x_start, y_start, z_start],
            [x_end, y_start, z_start],
            [x_end, y_end, z_start],
            [x_start, y_end, z_start],
            [x_start, y_start, z_end],
            [x_end, y_start, z_end],
            [x_end, y_end, z_end],
            [x_start, y_end, z_end],
        ])

        # Define the edges connecting the corners to form a box
        # Each edge is defined by two points (start and end)
        edges = [
            [corners[0], corners[1]],
            [corners[1], corners[2]],
            [corners[2], corners[3]],
            [corners[3], corners[0]],
            [corners[4], corners[5]],
            [corners[5], corners[6]],
            [corners[6], corners[7]],
            [corners[7], corners[4]],
            [corners[0], corners[4]],
            [corners[1], corners[5]],
            [corners[2], corners[6]],
            [corners[3], corners[7]],
        ]

        # Create a list of lines for the Shapes layer
        lines = [np.array(edge) for edge in edges]

        # Add the wireframe box as a Shapes layer
        self.voi_layer = self.viewer.add_shapes(
            lines,
            shape_type='line',
            edge_color='white',
            edge_width=2,
            opacity=0.25,
            name='Volume of Interest',
            blending='translucent_no_depth',
        )
