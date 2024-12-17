from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import (
    QFileDialog,
    QComboBox,
    QInputDialog,
    QMessageBox,
    QGraphicsObject,
)
from PyQt5.QtGui import QPixmap, QPen, QColor, QBrush, QPainter
from PyQt5.QtCore import pyqtSignal, QPointF, QRectF
import sys
import logging


class CornerMarker(QGraphicsObject):
    """
    A draggable corner marker represented as a red ellipse.
    Emits a 'moved' signal whenever its position changes.
    """

    # Signal emitted when the marker is moved
    moved = pyqtSignal()

    def __init__(self, x, y, size=10, parent=None):
        super().__init__(parent)
        self.setPos(x, y)
        self.size = size
        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsMovable
            | QtWidgets.QGraphicsItem.ItemSendsScenePositionChanges
            | QtWidgets.QGraphicsItem.ItemIsSelectable
        )
        self.brush_color = QBrush(QColor("red"))
        self.setZValue(1)  # Ensure markers are on top

    def boundingRect(self):
        """
        Defines the bounding rectangle of the ellipse.
        """
        return QRectF(-self.size / 2, -self.size / 2, self.size, self.size)

    def paint(self, painter, option, widget):
        """
        Paints the ellipse representing the corner marker.
        """
        painter.setBrush(self.brush_color)
        painter.setPen(QPen(QColor("black")))
        painter.drawEllipse(self.boundingRect())

    def itemChange(self, change, value):
        """
        Handles item changes. Emits 'moved' signal when position changes.
        """
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            self.moved.emit()
        return super().itemChange(change, value)


class SensorGUI(QtWidgets.QWidget):
    """
    Main GUI class for sensor positioning and ground plan management.
    """

    def __init__(self, eos=None, recalibrate_state=None):
        super().__init__()
        self.eos = eos
        self.recalibrate_state = recalibrate_state
        self.lock_sensors = False  # Initialize before initUI
        self.scale_factor = 1.0  # Default scale (1:1)

        self.standard_sizes = {
            "ASME A": {"width": 8.5, "height": 11},
            "ASME B": {"width": 11, "height": 17},
            "ASME C": {"width": 17, "height": 22},
            "ASME D": {"width": 22, "height": 34},
            "ASME E": {"width": 34, "height": 44},
            "ARCH A": {"width": 9, "height": 12},
            "ARCH B": {"width": 12, "height": 18},
            "ARCH C": {"width": 18, "height": 24},
            "ARCH D": {"width": 24, "height": 36},
            "ARCH E": {"width": 36, "height": 48},
            "ARCH E1": {"width": 30, "height": 42},
            "Custom": {"width": None, "height": None},
        }
        self.stage_corners = []  # To store stage corner points as (x, y)
        self.corner_markers = []  # To store CornerMarker instances
        self.stage_polygon = None  # Graphics item for stage polygon
        self.setting_stage_corners = False  # Flag for corner setting mode
        self.stage_transform = QtGui.QTransform()  # Transformation matrix
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface components.
        """
        self.setWindowTitle("Sensor Positioning")
        self.setGeometry(100, 100, 1200, 800)  # Increased width to accommodate new controls

        # Create a Graphics Scene and View
        self.scene = QtWidgets.QGraphicsScene()
        self.view = QtWidgets.QGraphicsView(self.scene, self)
        self.view.setGeometry(10, 10, 960, 600)  # Adjusted size
        self.view.setRenderHint(QtGui.QPainter.Antialiasing)
        self.view.viewport().installEventFilter(self)  # Event filter for mouse clicks

        # Create sensor rectangles
        self.sensors = {}
        self.create_sensor(1, 100, 100)
        self.create_sensor(2, 700, 100)
        self.create_sensor(3, 100, 500)
        self.create_sensor(4, 700, 500)

        # Create Buttons
        self.print_button = QtWidgets.QPushButton("Print Sensor Positions", self)
        self.print_button.setGeometry(10, 620, 200, 30)
        self.print_button.clicked.connect(self.print_sensor_positions)

        self.reset_button = QtWidgets.QPushButton("Reset Sensor Positions", self)
        self.reset_button.setGeometry(220, 620, 200, 30)
        self.reset_button.clicked.connect(self.reset_positions)

        self.lock_button = QtWidgets.QPushButton("Toggle Lock", self)
        self.lock_button.setGeometry(430, 620, 150, 30)
        self.lock_button.clicked.connect(self.toggle_lock)

        self.recalibrate_button = QtWidgets.QPushButton("Recalibrate", self)
        self.recalibrate_button.setGeometry(590, 620, 150, 30)
        self.recalibrate_button.clicked.connect(self.recalibrate)

        # Add a progress label
        self.progress_label = QtWidgets.QLabel("Status: Ready", self)
        self.progress_label.setGeometry(10, 660, 480, 30)

        # Add Upload Ground Plan Button
        self.upload_button = QtWidgets.QPushButton("Upload Ground Plan", self)
        self.upload_button.setGeometry(750, 620, 200, 30)
        self.upload_button.clicked.connect(self.upload_ground_plan)

        # Add Set Stage Corners Button (Toggle)
        self.set_stage_corners_button = QtWidgets.QPushButton("Set Stage Corners", self)
        self.set_stage_corners_button.setCheckable(True)
        self.set_stage_corners_button.setGeometry(750, 660, 200, 30)
        self.set_stage_corners_button.clicked.connect(self.toggle_stage_corner_setting)

        # Add Ground Plan Size Selection
        self.size_label = QtWidgets.QLabel("Ground Plan Size:", self)
        self.size_label.setGeometry(10, 700, 120, 30)

        self.size_combo = QComboBox(self)
        self.size_combo.setGeometry(130, 700, 150, 30)
        self.size_combo.addItems(self.standard_sizes.keys())
        self.size_combo.currentTextChanged.connect(self.size_changed)

        # Add Scale Input
        self.scale_label = QtWidgets.QLabel("Scale (inches per foot):", self)
        self.scale_label.setGeometry(300, 700, 150, 30)

        self.scale_input = QtWidgets.QLineEdit(self)
        self.scale_input.setGeometry(460, 700, 100, 30)
        self.scale_input.setPlaceholderText("e.g., 0.5")

        self.set_scale_button = QtWidgets.QPushButton("Set Scale", self)
        self.set_scale_button.setGeometry(570, 700, 100, 30)
        self.set_scale_button.clicked.connect(self.set_scale)

    def create_sensor(self, sensor_id, x, y):
        """
        Creates a sensor represented as a movable rectangle with an ID label.
        """
        if sensor_id in self.sensors:
            logging.warning(f"Sensor {sensor_id} already exists. Skipping creation.")
            return

        rect_size = 50
        rect = QtWidgets.QGraphicsRectItem(0, 0, rect_size, rect_size)  # Local coordinates start at (0,0)
        rect.setBrush(QBrush(QColor("lightblue")))
        rect.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, not self.lock_sensors)
        rect.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        rect.setData(0, sensor_id)  # Store sensor ID
        rect.setPos(x, y)  # Set scene position
        self.scene.addItem(rect)

        text = QtWidgets.QGraphicsTextItem(str(sensor_id), rect)
        text.setDefaultTextColor(QtCore.Qt.black)
        text.setPos(rect_size / 2 - 10, rect_size / 2 - 10)  # Center the text within the rectangle
        self.scene.addItem(text)

        self.sensors[sensor_id] = rect

    def upload_ground_plan(self):
        """
        Allows the user to upload a ground plan image and sets it as the background.
        """
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Ground Plan Image",
            "",
            "Image Files (*.png *.jpg *.bmp);;All Files (*)",
            options=options,
        )
        if file_name:
            pixmap = QPixmap(file_name)
            if not pixmap.isNull():
                if hasattr(self, "ground_plan"):
                    self.scene.removeItem(self.ground_plan)

                # Apply smooth transformation when scaling
                scaled_pixmap = pixmap.scaled(
                    self.view.viewport().size(),
                    QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.SmoothTransformation,
                )
                self.ground_plan = QtWidgets.QGraphicsPixmapItem(scaled_pixmap)
                self.ground_plan.setZValue(-1)  # Ensure it's in the background
                self.scene.addItem(self.ground_plan)
                self.view.fitInView(self.ground_plan, QtCore.Qt.KeepAspectRatio)
                logging.info(f"Ground plan '{file_name}' uploaded and set as background.")

                # Reset stage corners if a new ground plan is uploaded
                self.reset_stage_corners()
            else:
                logging.error("Failed to load the selected image.")
                QMessageBox.critical(self, "Error", "Failed to load the selected image.")

    def reset_stage_corners(self):
        """
        Resets all stage corners and related graphical items.
        """
        # Clear existing stage corners and polygon
        self.stage_corners = []
        for marker in self.corner_markers:
            self.scene.removeItem(marker)
        self.corner_markers = []
        if self.stage_polygon:
            self.scene.removeItem(self.stage_polygon)
            self.stage_polygon = None
        self.stage_transform = QtGui.QTransform()  # Reset transformation
        self.progress_label.setText("Status: Ground plan uploaded. Please set stage corners.")
        logging.info("Stage corners reset.")

    def toggle_stage_corner_setting(self, checked):
        """
        Toggles the mode for setting stage corners.
        """
        if checked:
            if not hasattr(self, "ground_plan"):
                QMessageBox.warning(self, "No Ground Plan", "Please upload a ground plan first.")
                self.set_stage_corners_button.setChecked(False)
                return

            self.setting_stage_corners = True
            self.progress_label.setText("Status: Stage corner setting mode enabled.")

            if not self.corner_markers:
                self.progress_label.setText("Status: Click four corners of the stage on the ground plan.")
            elif len(self.corner_markers) < 4:
                self.progress_label.setText(
                    f"Status: {len(self.corner_markers)} corners set. Please set {4 - len(self.corner_markers)} more."
                )
            else:
                self.progress_label.setText("Status: Drag the red markers to adjust stage corners.")
                # Make existing markers movable
                for marker in self.corner_markers:
                    marker.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        else:
            self.setting_stage_corners = False
            self.set_stage_corners_button.setChecked(False)
            self.progress_label.setText("Status: Stage corners set.")

            # Make markers non-movable
            for marker in self.corner_markers:
                marker.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)

            if self.stage_polygon:
                self.scene.removeItem(self.stage_polygon)

            if len(self.stage_corners) == 4:
                self.create_stage_polygon()
                self.calculate_stage_transform()
                self.adjust_sensors_based_on_stage()
                self.progress_label.setText("Status: Stage corners set successfully.")
                logging.info("Stage corners updated.")
            else:
                self.progress_label.setText("Status: Please set all four stage corners.")
                QMessageBox.warning(self, "Incomplete Corners", "Please set all four stage corners.")

    def size_changed(self, size_name):
        """
        Handles changes in the ground plan size selection.
        """
        if size_name != "Custom":
            size = self.standard_sizes[size_name]
            if size["width"] and size["height"]:
                self.set_scale_dialog(size["width"], size["height"])
        else:
            self.set_custom_size()

    def set_scale_dialog(self, width, height):
        """
        Prompts the user to set the scale based on the ground plan size.
        """
        scale, ok = QInputDialog.getDouble(
            self,
            "Set Scale",
            "Enter scale (inches per foot):",
            decimals=4,
            min=0.0001,
        )
        if ok and scale > 0:
            self.scale_factor = scale
            self.apply_scale()
            logging.info(f"Scale set to {scale}:1")
        else:
            logging.error("Invalid scale input.")
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid positive number for scale.")

    def set_custom_size(self):
        """
        Allows the user to set a custom ground plan size.
        """
        width, ok1 = QInputDialog.getDouble(self, "Custom Width", "Enter width (feet):", decimals=2, min=0.01)
        if ok1 and width > 0:
            height, ok2 = QInputDialog.getDouble(self, "Custom Height", "Enter height (feet):", decimals=2, min=0.01)
            if ok2 and height > 0:
                self.standard_sizes["Custom"]["width"] = width
                self.standard_sizes["Custom"]["height"] = height
                self.set_scale_dialog(width, height)
            else:
                logging.error("Invalid height input for custom size.")
                QMessageBox.warning(self, "Invalid Input", "Please enter a valid positive number for height.")
        else:
            logging.error("Invalid width input for custom size.")
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid positive number for width.")

    def set_scale(self):
        """
        Sets the scale based on user input from the scale input field.
        """
        try:
            scale_value = float(self.scale_input.text())
            if scale_value <= 0:
                raise ValueError
            self.scale_factor = scale_value  # For example, 0.5 inches per foot
            self.apply_scale()
            logging.info(f"Scale set to {scale_value}:1")
        except ValueError:
            logging.error("Invalid scale value entered.")
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid positive number for scale.")

    def apply_scale(self):
        """
        Applies the current scale factor to the view.
        """
        # Reset any previous scaling
        self.view.resetTransform()
        # Apply the new scale
        self.view.scale(self.scale_factor, self.scale_factor)
        # Optionally, fit the view to the ground plan
        if hasattr(self, "ground_plan"):
            self.view.fitInView(self.ground_plan, QtCore.Qt.KeepAspectRatio)
        logging.info("Scale applied.")

    def recalibrate(self):
        """
        Placeholder for recalibration logic.
        """
        # TODO: Implement recalibration logic
        logging.info("Recalibrate button clicked.")
        QMessageBox.information(self, "Recalibrate", "Recalibration is not yet implemented.")

    def toggle_lock(self):
        """
        Toggles the lock state of the sensors, making them movable or fixed.
        """
        self.lock_sensors = not self.lock_sensors
        logging.info(f"Sensors {'locked' if self.lock_sensors else 'unlocked'}.")
        for sensor in self.sensors.values():
            sensor.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, not self.lock_sensors)

    def print_sensor_positions(self):
        """
        Displays the current positions of all sensors.
        """
        positions = self.get_sensor_positions_stage()
        logging.info(f"Sensor Positions: {positions}")
        QMessageBox.information(self, "Sensor Positions", self.format_sensor_positions(positions))

    def format_sensor_positions(self, positions):
        """
        Formats sensor positions for display.
        """
        formatted = ""
        for sensor_id, pos in positions.items():
            feet_x, inches_x, feet_y, inches_y = self.convert_to_feet_inches_stage(pos[0], pos[1])
            formatted += f"Sensor {sensor_id}: {feet_x}' {inches_x:.2f}\" , {feet_y}' {inches_y:.2f}\"\n"
        return formatted

    def get_sensor_positions_stage(self):
        """
        Retrieves the current positions of all sensors in the stage coordinate system.
        """
        sensor_positions = {}
        for sensor_id, rect in self.sensors.items():
            pos = rect.scenePos()  # Get actual position in scene
            stage_pos = self.map_scene_to_stage(pos)
            sensor_positions[sensor_id] = (stage_pos.x(), stage_pos.y())
        return sensor_positions

    def reset_positions(self):
        """
        Resets all sensors to their default positions.
        """
        default_positions = {
            1: (100, 100),
            2: (700, 100),
            3: (100, 500),
            4: (700, 500),
        }
        for sensor_id, rect in self.sensors.items():
            rect.setPos(*default_positions[sensor_id])
        logging.info("Sensor positions have been reset.")

    def convert_to_feet_inches_stage(self, x, y):
        """
        Converts stage-relative coordinates to feet and inches based on the scale factor.
        """
        # Assuming scale_factor is inches per foot
        real_x_inches = x * self.scale_factor
        real_y_inches = y * self.scale_factor

        real_x_feet = int(real_x_inches // 12)
        real_x_remaining_inches = real_x_inches % 12

        real_y_feet = int(real_y_inches // 12)
        real_y_remaining_inches = real_y_inches % 12

        return (real_x_feet, real_x_remaining_inches, real_y_feet, real_y_remaining_inches)

    def calculate_stage_transform(self):
        """
        Calculates the transformation matrix to map scene coordinates to stage coordinates.
        Origin is set to the first stage corner, and axes are aligned based on the first two corners.
        """
        if len(self.stage_corners) < 2:
            logging.error("Insufficient stage corners to calculate transformation.")
            return

        p0 = QtCore.QPointF(*self.stage_corners[0])  # Origin
        p1 = QtCore.QPointF(*self.stage_corners[1])  # Defines the x-axis

        # Create a line from p0 to p1
        line = QtCore.QLineF(p0, p1)
        angle = -line.angle()  # Negative to rotate the line to align with the scene's x-axis

        # Create transformation: translate to origin, rotate
        transform = QtGui.QTransform()
        transform.translate(-p0.x(), -p0.y())
        transform.rotate(angle)
        self.stage_transform = transform
        logging.info(f"Stage transform calculated with angle {angle} degrees.")

    def map_scene_to_stage(self, point):
        """
        Maps a QPointF from scene coordinates to stage coordinates.
        """
        return self.stage_transform.map(point)

    def map_stage_to_scene(self, point):
        """
        Maps a QPointF from stage coordinates to scene coordinates.
        """
        inverted, invertible = self.stage_transform.inverted()
        if invertible:
            return inverted.map(point)
        else:
            logging.error("Stage transform is not invertible.")
            return point

    def eventFilter(self, source, event):
        """
        Handles mouse press events for coordinate display and stage corner setting.
        """
        if event.type() == QtCore.QEvent.MouseButtonPress and source is self.view.viewport():
            mouse_pos = event.pos()
            scene_pos = self.view.mapToScene(mouse_pos)
            logging.info(f"Mouse clicked at scene position: ({scene_pos.x()}, {scene_pos.y()})")

            if self.setting_stage_corners:
                if len(self.corner_markers) < 4:
                    # Create a new corner marker
                    marker = CornerMarker(scene_pos.x(), scene_pos.y())
                    marker.moved.connect(self.update_stage_polygon)
                    self.scene.addItem(marker)
                    self.corner_markers.append(marker)
                    self.stage_corners.append((scene_pos.x(), scene_pos.y()))
                    logging.info(
                        f"Stage corner {len(self.corner_markers)} set at: ({scene_pos.x()}, {scene_pos.y()})"
                    )
                    self.progress_label.setText(f"Status: Stage corner {len(self.corner_markers)} set.")

                    if len(self.corner_markers) == 4:
                        self.setting_stage_corners = False
                        self.set_stage_corners_button.setChecked(False)
                        self.set_stage_corners_button.setText("Edit Stage Corners")
                        self.create_stage_polygon()
                        self.calculate_stage_transform()
                        self.adjust_sensors_based_on_stage()
                        self.progress_label.setText("Status: Stage corners set successfully.")
                        logging.info("All four stage corners have been set.")
                else:
                    # All four corners are already set, so do nothing on click
                    self.progress_label.setText("Status: Drag the red markers to adjust stage corners.")
            else:
                if hasattr(self, "stage_transform") and self.stage_transform != QtGui.QTransform():
                    # Convert scene position to stage coordinates
                    stage_point = self.map_scene_to_stage(scene_pos)
                    feet_x, inches_x, feet_y, inches_y = self.convert_to_feet_inches_stage(stage_point.x(), stage_point.y())
                    coord_str = f"Clicked at: {feet_x}' {inches_x:.2f}\" , {feet_y}' {inches_y:.2f}\""
                    self.progress_label.setText(f"Status: {coord_str}")
                    logging.info(coord_str)
                else:
                    # If stage_transform is not set, fallback to scene coordinates
                    if self.scale_factor:
                        feet_x, inches_x, feet_y, inches_y = self.convert_to_feet_inches(scene_pos.x(), scene_pos.y())
                        coord_str = f"Clicked at: {feet_x}' {inches_x:.2f}\" , {feet_y}' {inches_y:.2f}\""
                        self.progress_label.setText(f"Status: {coord_str}")
                        logging.info(coord_str)

        return super().eventFilter(source, event)

    def create_stage_polygon(self):
        """
        Creates a polygon representing the stage based on the set corners.
        """
        if len(self.stage_corners) != 4:
            logging.error("Insufficient stage corners to create polygon.")
            return

        if self.stage_polygon:
            self.scene.removeItem(self.stage_polygon)

        polygon = QtGui.QPolygonF([QPointF(x, y) for x, y in self.stage_corners])
        self.stage_polygon = QtWidgets.QGraphicsPolygonItem(polygon)
        pen = QPen(QColor("green"))
        pen.setWidth(1)
        self.stage_polygon.setPen(pen)
        self.stage_polygon.setBrush(QBrush(QColor(0, 255, 0, 2)))  # Semi-transparent
        self.stage_polygon.setZValue(0.5)  # Above ground plan but below markers
        self.scene.addItem(self.stage_polygon)
        logging.info("Stage polygon created.")

    def update_stage_polygon(self):
        """
        Updates the stage polygon based on the current positions of the corner markers.
        """
        # Update the stage_corners list based on marker positions
        self.stage_corners = [(marker.pos().x(), marker.pos().y()) for marker in self.corner_markers]
        logging.debug("Stage corners updated from markers.")
        self.create_stage_polygon()
        self.calculate_stage_transform()
        self.adjust_sensors_based_on_stage()

    def adjust_sensors_based_on_stage(self):
        """
        Adjusts sensor positions based on the stage's coordinate system.
        Example adjustment: Align sensors according to the new coordinate system.
        """
        if len(self.stage_corners) != 4:
            logging.warning("Cannot adjust sensors without four stage corners.")
            return

        # Currently, this function does not automatically move sensors.
        # Sensors are positioned by the user, but their coordinates are now relative to the stage.
        # If automatic adjustment is needed, implement it here.

        logging.info("Sensors are now positioned relative to the stage coordinate system.")

    # Optional: Display coordinate axes on the stage
    def display_coordinate_axes(self):
        """
        Displays the X and Y axes on the stage for better visualization.
        """
        # Remove existing axes if any
        for item in self.scene.items():
            if isinstance(item, QtWidgets.QGraphicsLineItem) and item.data(0) == "axis":
                self.scene.removeItem(item)

        # X-axis from origin to (100, 0) in stage coordinates
        origin = QtCore.QPointF(0, 0)
        x_axis_end = QtCore.QPointF(100, 0)
        y_axis_end = QtCore.QPointF(0, 100)

        # Map to scene coordinates
        origin_scene = self.map_stage_to_scene(origin)
        x_end_scene = self.map_stage_to_scene(x_axis_end)
        y_end_scene = self.map_stage_to_scene(y_axis_end)

        # Create X-axis line
        x_axis = QtWidgets.QGraphicsLineItem(QtCore.QLineF(origin_scene, x_end_scene))
        x_axis.setPen(QPen(QColor("blue"), 2))
        x_axis.setData(0, "axis")
        self.scene.addItem(x_axis)

        # Create Y-axis line
        y_axis = QtWidgets.QGraphicsLineItem(QtCore.QLineF(origin_scene, y_end_scene))
        y_axis.setPen(QPen(QColor("red"), 2))
        y_axis.setData(0, "axis")
        self.scene.addItem(y_axis)

        logging.info("Coordinate axes displayed on the stage.")

    # Call display_coordinate_axes after setting stage corners
    def create_stage_polygon(self):
        """
        Creates a polygon representing the stage based on the set corners.
        """
        if len(self.stage_corners) != 4:
            logging.error("Insufficient stage corners to create polygon.")
            return

        if self.stage_polygon:
            self.scene.removeItem(self.stage_polygon)

        polygon = QtGui.QPolygonF([QPointF(x, y) for x, y in self.stage_corners])
        self.stage_polygon = QtWidgets.QGraphicsPolygonItem(polygon)
        pen = QPen(QColor("green"))
        pen.setWidth(2)
        self.stage_polygon.setPen(pen)
        self.stage_polygon.setBrush(QBrush(QColor(0, 255, 0, 50)))  # Semi-transparent
        self.stage_polygon.setZValue(0.5)  # Above ground plan but below markers
        self.scene.addItem(self.stage_polygon)
        logging.info("Stage polygon created.")

        # Display coordinate axes
        self.display_coordinate_axes()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    # Create the application
    app = QtWidgets.QApplication(sys.argv)
    gui = SensorGUI()
    gui.show()

    # Execute the application
    sys.exit(app.exec_())
