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
        self.origin_set = False  # Flag to check if origin is set
        self.origin_point = None  # To store origin point as QPointF
        self.stage_rectangle = None  # Graphics item for stage rectangle
        self.stage_dimensions = {"width_feet": 0, "width_inches": 0, "height_feet": 0, "height_inches": 0}
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

        # Add Set Origin Button
        self.set_origin_button = QtWidgets.QPushButton("Set Origin", self)
        self.set_origin_button.setGeometry(750, 660, 200, 30)
        self.set_origin_button.clicked.connect(self.enable_origin_setting)

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

        # Add Stage Dimensions Inputs
        self.stage_width_label = QtWidgets.QLabel("Stage Width:", self)
        self.stage_width_label.setGeometry(700, 700, 80, 30)

        self.stage_width_feet = QtWidgets.QLineEdit(self)
        self.stage_width_feet.setGeometry(790, 700, 50, 30)
        self.stage_width_feet.setPlaceholderText("Feet")

        self.stage_width_inches = QtWidgets.QLineEdit(self)
        self.stage_width_inches.setGeometry(850, 700, 50, 30)
        self.stage_width_inches.setPlaceholderText("Inches")

        self.stage_height_label = QtWidgets.QLabel("Stage Height:", self)
        self.stage_height_label.setGeometry(910, 700, 80, 30)

        self.stage_height_feet = QtWidgets.QLineEdit(self)
        self.stage_height_feet.setGeometry(990, 700, 50, 30)
        self.stage_height_feet.setPlaceholderText("Feet")

        self.stage_height_inches = QtWidgets.QLineEdit(self)
        self.stage_height_inches.setGeometry(1050, 700, 50, 30)
        self.stage_height_inches.setPlaceholderText("Inches")

        self.set_stage_button = QtWidgets.QPushButton("Set Stage Dimensions", self)
        self.set_stage_button.setGeometry(700, 740, 200, 30)
        self.set_stage_button.clicked.connect(self.set_stage_dimensions)

        # Add Toggle Background Edit Mode Button
        self.toggle_bg_edit_button = QtWidgets.QPushButton("Toggle Background Edit Mode", self)
        self.toggle_bg_edit_button.setGeometry(10, 740, 200, 30)
        self.toggle_bg_edit_button.setCheckable(True)
        self.toggle_bg_edit_button.clicked.connect(self.toggle_background_edit)

        # Add Background Scale Input
        self.bg_scale_label = QtWidgets.QLabel("Background Scale (%):", self)
        self.bg_scale_label.setGeometry(220, 740, 150, 30)

        self.bg_scale_input = QtWidgets.QLineEdit(self)
        self.bg_scale_input.setGeometry(380, 740, 100, 30)
        self.bg_scale_input.setPlaceholderText("e.g., 100")

        self.set_bg_scale_button = QtWidgets.QPushButton("Set Scale", self)
        self.set_bg_scale_button.setGeometry(490, 740, 100, 30)
        self.set_bg_scale_button.clicked.connect(self.set_background_scale)

    def toggle_background_edit(self, checked):
        """
        Toggles background edit mode, allowing the ground plan to be moved and scaled.
        """
        if hasattr(self, "ground_plan") and self.ground_plan:
            if checked:
                self.ground_plan.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
                self.ground_plan.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
                self.view.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
                self.progress_label.setText("Status: Background edit mode enabled. Move or scale the background.")
                logging.info("Background edit mode enabled.")
            else:
                self.ground_plan.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
                self.ground_plan.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
                self.view.setDragMode(QtWidgets.QGraphicsView.NoDrag)
                self.progress_label.setText("Status: Background edit mode disabled.")
                logging.info("Background edit mode disabled.")

    def set_background_scale(self):
        """
        Sets the scale of the background image based on the input percentage.
        """
        if not hasattr(self, "ground_plan") or not self.ground_plan:
            QMessageBox.warning(self, "No Background", "Please upload a ground plan first.")
            return

        try:
            scale_percent = float(self.bg_scale_input.text())
            if scale_percent <= 0:
                raise ValueError("Scale must be positive.")

            scale_factor = scale_percent / 100.0
            self.ground_plan.setScale(scale_factor)

            self.progress_label.setText(f"Status: Background scaled to {scale_percent}%.")
            logging.info(f"Background scaled to {scale_percent}%.")
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid positive number for scale percentage.")
            logging.error("Invalid scale percentage input.")

    def create_sensor(self, sensor_id, x, y):
        """
        Creates a sensor represented as a movable rectangle with an ID label.
        """
        if sensor_id in self.sensors:
            logging.warning(f"Sensor {sensor_id} already exists. Skipping creation.")
            return

        rect_size = 20
        rect = QtWidgets.QGraphicsRectItem(0, 0, rect_size, rect_size)  # Local coordinates start at (0,0)
        rect.setBrush(QBrush(QColor("lightblue")))
        rect.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, not self.lock_sensors)
        rect.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        rect.setData(0, sensor_id)  # Store sensor ID
        rect.setPos(x, y)  # Set scene position
        self.scene.addItem(rect)

        text = QtWidgets.QGraphicsTextItem(str(sensor_id), rect)
        text.setDefaultTextColor(QtCore.Qt.black)

        # Center the text on the rectangle
        text.setPos((rect_size - text.boundingRect().width()) / 2, (rect_size - text.boundingRect().height()) / 2)
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
                #self.view.fitInView(self.ground_plan, QtCore.Qt.KeepAspectRatio)
                logging.info(f"Ground plan '{file_name}' uploaded and set as background.")

                # Reset stage if a new ground plan is uploaded
                self.reset_stage()
            else:
                logging.error("Failed to load the selected image.")
                QMessageBox.critical(self, "Error", "Failed to load the selected image.")

    def reset_stage(self):
        """
        Resets the stage setup.
        """
        self.origin_set = False
        self.origin_point = None
        if self.stage_rectangle:
            self.scene.removeItem(self.stage_rectangle)
            self.stage_rectangle = None
        self.stage_dimensions = {"width_feet": 0, "width_inches": 0, "height_feet": 0, "height_inches": 0}
        self.progress_label.setText("Status: Ground plan uploaded. Please set the origin and stage dimensions.")
        logging.info("Stage reset.")

    def enable_origin_setting(self):
        """
        Enables the mode to set the origin by clicking on the ground plan.
        """
        if not hasattr(self, "ground_plan"):
            QMessageBox.warning(self, "No Ground Plan", "Please upload a ground plan first.")
            return

        self.view.setCursor(QtCore.Qt.CrossCursor)
        self.origin_setting = True
        self.progress_label.setText("Status: Click on the ground plan to set the origin (top-left corner).")
        logging.info("Origin setting mode enabled.")

    def set_stage_dimensions(self):
        """
        Sets the stage dimensions based on user input and creates the stage rectangle.
        """
        if not self.origin_set:
            QMessageBox.warning(self, "Origin Not Set", "Please set the origin before setting stage dimensions.")
            return

        try:
            # Retrieve width
            width_feet = float(self.stage_width_feet.text()) if self.stage_width_feet.text() else 0
            width_inches = float(self.stage_width_inches.text()) if self.stage_width_inches.text() else 0
            # Retrieve height
            height_feet = float(self.stage_height_feet.text()) if self.stage_height_feet.text() else 0
            height_inches = float(self.stage_height_inches.text()) if self.stage_height_inches.text() else 0

            if width_feet < 0 or width_inches < 0 or height_feet < 0 or height_inches < 0:
                raise ValueError

            # Convert to total inches
            total_width_inches = width_feet * 12 + width_inches
            total_height_inches = height_feet * 12 + height_inches

            if total_width_inches <= 0 or total_height_inches <= 0:
                raise ValueError

            self.stage_dimensions = {
                "width_feet": width_feet,
                "width_inches": width_inches,
                "height_feet": height_feet,
                "height_inches": height_inches,
            }

            # Convert to scene units based on scale
            width_scene = total_width_inches / self.scale_factor
            height_scene = total_height_inches / self.scale_factor

            # Create or update the stage rectangle
            if self.stage_rectangle:
                self.scene.removeItem(self.stage_rectangle)

            self.stage_rectangle = QtWidgets.QGraphicsRectItem(
                QtCore.QRectF(0, 0, width_scene, height_scene)
            )
            self.stage_rectangle.setPen(QPen(QColor("green"), 2))
            self.stage_rectangle.setBrush(QBrush(QColor(0, 255, 0, 50)))  # Semi-transparent
            self.stage_rectangle.setPos(self.origin_point)
            self.stage_rectangle.setZValue(0.5)  # Above ground plan
            self.scene.addItem(self.stage_rectangle)

            self.progress_label.setText("Status: Stage dimensions set successfully.")
            logging.info(f"Stage dimensions set: Width={total_width_inches} inches, Height={total_height_inches} inches.")

        except ValueError:
            logging.error("Invalid stage dimension inputs.")
            QMessageBox.warning(self, "Invalid Input", "Please enter valid positive numbers for stage dimensions.")

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
            if self.origin_set and self.scale_factor > 0:
                stage_pos = pos - self.origin_point  # Relative to origin
                sensor_positions[sensor_id] = (stage_pos.x(), stage_pos.y())
            else:
                sensor_positions[sensor_id] = (pos.x(), pos.y())
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

    def convert_to_feet_inches_scene(self, x, y):
        """
        Converts scene coordinates to feet and inches based on the scale factor.
        """
        # Assuming scale_factor is inches per foot
        real_x_inches = x * self.scale_factor
        real_y_inches = y * self.scale_factor

        real_x_feet = int(real_x_inches // 12)
        real_x_remaining_inches = real_x_inches % 12

        real_y_feet = int(real_y_inches // 12)
        real_y_remaining_inches = real_y_inches % 12

        return (real_x_feet, real_x_remaining_inches, real_y_feet, real_y_remaining_inches)

    def eventFilter(self, source, event):
        """
        Handles mouse press events for coordinate display and origin setting.
        """
        if event.type() == QtCore.QEvent.MouseButtonPress and source is self.view.viewport():
            mouse_pos = event.pos()
            scene_pos = self.view.mapToScene(mouse_pos)
            logging.info(f"Mouse clicked at scene position: ({scene_pos.x()}, {scene_pos.y()})")

            if hasattr(self, "origin_setting") and self.origin_setting:
                # Set the origin
                self.origin_point = scene_pos
                self.origin_set = True
                self.origin_setting = False
                self.view.setCursor(QtCore.Qt.ArrowCursor)
                self.progress_label.setText("Status: Origin set. Enter stage dimensions.")
                logging.info(f"Origin set at: ({scene_pos.x()}, {scene_pos.y()})")
                # Optionally, mark the origin
                origin_marker = QtWidgets.QGraphicsEllipseItem(-5, -5, 10, 10)
                origin_marker.setBrush(QBrush(QColor("blue")))
                origin_marker.setPen(QPen(QColor("black")))
                origin_marker.setPos(scene_pos)
                origin_marker.setZValue(1)
                self.scene.addItem(origin_marker)
            else:
                if self.origin_set and self.stage_rectangle:
                    # Optionally, display clicked coordinates relative to origin
                    stage_point = scene_pos - self.origin_point
                    feet_x, inches_x, feet_y, inches_y = self.convert_to_feet_inches_stage(stage_point.x(), stage_point.y())
                    coord_str = f"Clicked at: {feet_x}' {inches_x:.2f}\" , {feet_y}' {inches_y:.2f}\""
                    self.progress_label.setText(f"Status: {coord_str}")
                    logging.info(coord_str)
                else:
                    if self.scale_factor:
                        feet_x, inches_x, feet_y, inches_y = self.convert_to_feet_inches_scene(scene_pos.x(), scene_pos.y())
                        coord_str = f"Clicked at: {feet_x}' {inches_x:.2f}\" , {feet_y}' {inches_y:.2f}\""
                        self.progress_label.setText(f"Status: {coord_str}")
                        logging.info(coord_str)

        return super().eventFilter(source, event)

    def set_stage_dimensions(self):
        """
        Sets the stage dimensions based on user input and creates the stage rectangle.
        """
        if not self.origin_set:
            QMessageBox.warning(self, "Origin Not Set", "Please set the origin before setting stage dimensions.")
            return

        try:
            # Retrieve width
            width_feet = float(self.stage_width_feet.text()) if self.stage_width_feet.text() else 0
            width_inches = float(self.stage_width_inches.text()) if self.stage_width_inches.text() else 0
            # Retrieve height
            height_feet = float(self.stage_height_feet.text()) if self.stage_height_feet.text() else 0
            height_inches = float(self.stage_height_inches.text()) if self.stage_height_inches.text() else 0

            if width_feet < 0 or width_inches < 0 or height_feet < 0 or height_inches < 0:
                raise ValueError

            # Convert to total inches
            total_width_inches = width_feet * 12 + width_inches
            total_height_inches = height_feet * 12 + height_inches

            if total_width_inches <= 0 or total_height_inches <= 0:
                raise ValueError

            self.stage_dimensions = {
                "width_feet": width_feet,
                "width_inches": width_inches,
                "height_feet": height_feet,
                "height_inches": height_inches,
            }

            # Convert to scene units based on scale
            width_scene = total_width_inches / self.scale_factor
            height_scene = total_height_inches / self.scale_factor

            # Create or update the stage rectangle
            if self.stage_rectangle:
                self.scene.removeItem(self.stage_rectangle)

            self.stage_rectangle = QtWidgets.QGraphicsRectItem(
                QtCore.QRectF(0, 0, width_scene, height_scene)
            )
            self.stage_rectangle.setPen(QPen(QColor("green"), 2))
            self.stage_rectangle.setBrush(QBrush(QColor(0, 255, 0, 50)))  # Semi-transparent
            self.stage_rectangle.setPos(self.origin_point)
            self.stage_rectangle.setZValue(0.5)  # Above ground plan
            self.scene.addItem(self.stage_rectangle)

            self.progress_label.setText("Status: Stage dimensions set successfully.")
            logging.info(f"Stage dimensions set: Width={total_width_inches} inches, Height={total_height_inches} inches.")

        except ValueError:
            logging.error("Invalid stage dimension inputs.")
            QMessageBox.warning(self, "Invalid Input", "Please enter valid positive numbers for stage dimensions.")

    def display_coordinate_axes(self):
        """
        Displays the X and Y axes on the stage for better visualization.
        """
        # Remove existing axes if any
        for item in self.scene.items():
            if isinstance(item, QtWidgets.QGraphicsLineItem) and item.data(0) == "axis":
                self.scene.removeItem(item)

        if not self.origin_set:
            return

        # X-axis from origin to (width, 0) in stage coordinates
        width_scene = self.stage_dimensions["width_feet"] * 12 / self.scale_factor + self.stage_dimensions["width_inches"] / self.scale_factor
        height_scene = self.stage_dimensions["height_feet"] * 12 / self.scale_factor + self.stage_dimensions["height_inches"] / self.scale_factor

        origin_scene = self.origin_point
        x_end_scene = QtCore.QPointF(origin_scene.x() + width_scene, origin_scene.y())
        y_end_scene = QtCore.QPointF(origin_scene.x(), origin_scene.y() + height_scene)

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

    def eventFilter(self, source, event):
        """
        Handles mouse press events for coordinate display and origin setting.
        """
        if event.type() == QtCore.QEvent.MouseButtonPress and source is self.view.viewport():
            mouse_pos = event.pos()
            scene_pos = self.view.mapToScene(mouse_pos)
            logging.info(f"Mouse clicked at scene position: ({scene_pos.x()}, {scene_pos.y()})")

            if hasattr(self, "origin_setting") and self.origin_setting:
                # Set the origin
                self.origin_point = scene_pos
                self.origin_set = True
                self.origin_setting = False
                self.view.setCursor(QtCore.Qt.ArrowCursor)
                self.progress_label.setText("Status: Origin set. Enter stage dimensions.")
                logging.info(f"Origin set at: ({scene_pos.x()}, {scene_pos.y()})")
                # Optionally, mark the origin
                origin_marker = QtWidgets.QGraphicsEllipseItem(-5, -5, 10, 10)
                origin_marker.setBrush(QBrush(QColor("blue")))
                origin_marker.setPen(QPen(QColor("black")))
                origin_marker.setPos(scene_pos)
                origin_marker.setZValue(1)
                self.scene.addItem(origin_marker)
            else:
                if self.origin_set and self.stage_rectangle:
                    # Optionally, display clicked coordinates relative to origin
                    stage_point = scene_pos - self.origin_point
                    feet_x, inches_x, feet_y, inches_y = self.convert_to_feet_inches_stage(stage_point.x(), stage_point.y())
                    coord_str = f"Clicked at: {feet_x}' {inches_x:.2f}\" , {feet_y}' {inches_y:.2f}\""
                    self.progress_label.setText(f"Status: {coord_str}")
                    logging.info(coord_str)
                else:
                    if self.scale_factor:
                        feet_x, inches_x, feet_y, inches_y = self.convert_to_feet_inches_scene(scene_pos.x(), scene_pos.y())
                        coord_str = f"Clicked at: {feet_x}' {inches_x:.2f}\" , {feet_y}' {inches_y:.2f}\""
                        self.progress_label.setText(f"Status: {coord_str}")
                        logging.info(coord_str)

        return super().eventFilter(source, event)

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
            if self.origin_set and self.scale_factor > 0:
                stage_pos = pos - self.origin_point  # Relative to origin
                sensor_positions[sensor_id] = (stage_pos.x(), stage_pos.y())
            else:
                sensor_positions[sensor_id] = (pos.x(), pos.y())
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

    def convert_to_feet_inches_scene(self, x, y):
        """
        Converts scene coordinates to feet and inches based on the scale factor.
        """
        # Assuming scale_factor is inches per foot
        real_x_inches = x * self.scale_factor
        real_y_inches = y * self.scale_factor

        real_x_feet = int(real_x_inches // 12)
        real_x_remaining_inches = real_x_inches % 12

        real_y_feet = int(real_y_inches // 12)
        real_y_remaining_inches = real_y_inches % 12

        return (real_x_feet, real_x_remaining_inches, real_y_feet, real_y_remaining_inches)

    def set_stage_dimensions(self):
        """
        Sets the stage dimensions based on user input and creates the stage rectangle.
        """
        if not self.origin_set:
            QMessageBox.warning(self, "Origin Not Set", "Please set the origin before setting stage dimensions.")
            return

        try:
            # Retrieve width
            width_feet = float(self.stage_width_feet.text()) if self.stage_width_feet.text() else 0
            width_inches = float(self.stage_width_inches.text()) if self.stage_width_inches.text() else 0
            # Retrieve height
            height_feet = float(self.stage_height_feet.text()) if self.stage_height_feet.text() else 0
            height_inches = float(self.stage_height_inches.text()) if self.stage_height_inches.text() else 0

            if width_feet < 0 or width_inches < 0 or height_feet < 0 or height_inches < 0:
                raise ValueError

            # Convert to total inches
            total_width_inches = width_feet * 12 + width_inches
            total_height_inches = height_feet * 12 + height_inches

            if total_width_inches <= 0 or total_height_inches <= 0:
                raise ValueError

            self.stage_dimensions = {
                "width_feet": width_feet,
                "width_inches": width_inches,
                "height_feet": height_feet,
                "height_inches": height_inches,
            }

            # Convert to scene units based on scale
            width_scene = total_width_inches / self.scale_factor
            height_scene = total_height_inches / self.scale_factor

            # Create or update the stage rectangle
            if self.stage_rectangle:
                self.scene.removeItem(self.stage_rectangle)

            self.stage_rectangle = QtWidgets.QGraphicsRectItem(
                QtCore.QRectF(0, 0, width_scene, height_scene)
            )
            self.stage_rectangle.setPen(QPen(QColor("green"), 2))
            self.stage_rectangle.setBrush(QBrush(QColor(0, 255, 0, 50)))  # Semi-transparent
            self.stage_rectangle.setPos(self.origin_point)
            self.stage_rectangle.setZValue(0.5)  # Above ground plan
            self.scene.addItem(self.stage_rectangle)

            self.display_coordinate_axes()
            self.progress_label.setText("Status: Stage dimensions set successfully.")
            logging.info(f"Stage dimensions set: Width={total_width_inches} inches, Height={total_height_inches} inches.")

        except ValueError:
            logging.error("Invalid stage dimension inputs.")
            QMessageBox.warning(self, "Invalid Input", "Please enter valid positive numbers for stage dimensions.")

    def display_coordinate_axes(self):
        """
        Displays the X and Y axes on the stage for better visualization.
        """
        # Remove existing axes if any
        for item in self.scene.items():
            if isinstance(item, QtWidgets.QGraphicsLineItem) and item.data(0) == "axis":
                self.scene.removeItem(item)

        if not self.origin_set or not self.stage_rectangle:
            return

        # X-axis from origin to (width, 0) in stage coordinates
        rect = self.stage_rectangle.rect()
        width_scene = rect.width()
        height_scene = rect.height()

        origin_scene = self.origin_point
        x_end_scene = QtCore.QPointF(origin_scene.x() + width_scene, origin_scene.y())
        y_end_scene = QtCore.QPointF(origin_scene.x(), origin_scene.y() + height_scene)

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

    def enable_origin_setting(self):
        """
        Enables the mode to set the origin by clicking on the ground plan.
        """
        if not hasattr(self, "ground_plan"):
            QMessageBox.warning(self, "No Ground Plan", "Please upload a ground plan first.")
            return

        self.view.setCursor(QtCore.Qt.CrossCursor)
        self.origin_setting = True
        self.progress_label.setText("Status: Click on the ground plan to set the origin (top-left corner).")
        logging.info("Origin setting mode enabled.")

    def set_stage_dimensions(self):
        """
        Sets the stage dimensions based on user input and creates the stage rectangle.
        """
        if not self.origin_set:
            QMessageBox.warning(self, "Origin Not Set", "Please set the origin before setting stage dimensions.")
            return

        try:
            # Retrieve width
            width_feet = float(self.stage_width_feet.text()) if self.stage_width_feet.text() else 0
            width_inches = float(self.stage_width_inches.text()) if self.stage_width_inches.text() else 0
            # Retrieve height
            height_feet = float(self.stage_height_feet.text()) if self.stage_height_feet.text() else 0
            height_inches = float(self.stage_height_inches.text()) if self.stage_height_inches.text() else 0

            if width_feet < 0 or width_inches < 0 or height_feet < 0 or height_inches < 0:
                raise ValueError

            # Convert to total inches
            total_width_inches = width_feet * 12 + width_inches
            total_height_inches = height_feet * 12 + height_inches

            if total_width_inches <= 0 or total_height_inches <= 0:
                raise ValueError

            self.stage_dimensions = {
                "width_feet": width_feet,
                "width_inches": width_inches,
                "height_feet": height_feet,
                "height_inches": height_inches,
            }

            # Convert to scene units based on scale
            width_scene = total_width_inches / self.scale_factor
            height_scene = total_height_inches / self.scale_factor

            # Create or update the stage rectangle
            if self.stage_rectangle:
                self.scene.removeItem(self.stage_rectangle)

            self.stage_rectangle = QtWidgets.QGraphicsRectItem(
                QtCore.QRectF(0, 0, width_scene, height_scene)
            )
            self.stage_rectangle.setPen(QPen(QColor("green"), 2))
            self.stage_rectangle.setBrush(QBrush(QColor(0, 255, 0, 50)))  # Semi-transparent
            self.stage_rectangle.setPos(self.origin_point)
            self.stage_rectangle.setZValue(0.5)  # Above ground plan
            self.scene.addItem(self.stage_rectangle)

            self.display_coordinate_axes()
            self.progress_label.setText("Status: Stage dimensions set successfully.")
            logging.info(f"Stage dimensions set: Width={total_width_inches} inches, Height={total_height_inches} inches.")

        except ValueError:
            logging.error("Invalid stage dimension inputs.")
            QMessageBox.warning(self, "Invalid Input", "Please enter valid positive numbers for stage dimensions.")

    def display_coordinate_axes(self):
        """
        Displays the X and Y axes on the stage for better visualization.
        """
        # Remove existing axes if any
        for item in self.scene.items():
            if isinstance(item, QtWidgets.QGraphicsLineItem) and item.data(0) == "axis":
                self.scene.removeItem(item)

        if not self.origin_set or not self.stage_rectangle:
            return

        # X-axis from origin to (width, 0) in stage coordinates
        rect = self.stage_rectangle.rect()
        width_scene = rect.width()
        height_scene = rect.height()

        origin_scene = self.origin_point
        x_end_scene = QtCore.QPointF(origin_scene.x() + width_scene, origin_scene.y())
        y_end_scene = QtCore.QPointF(origin_scene.x(), origin_scene.y() + height_scene)

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


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    # Create the application
    app = QtWidgets.QApplication(sys.argv)
    gui = SensorGUI()
    gui.show()

    # Execute the application
    sys.exit(app.exec_())
