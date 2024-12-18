import sys
import json
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget, QPushButton, QHBoxLayout, QMessageBox, QComboBox, QLabel
)

from PyQt5.QtCore import pyqtSignal


class SensorsEditor(QMainWindow):

    data_saved = pyqtSignal()

    def __init__(self, active_channel=1,file_name=".sensors.json", fixtures_file=".fixtures.json"):
        super().__init__()
        self.file_name = file_name
        self.data = {}
        self.active_channel = active_channel
        self.fixtures_file = fixtures_file

        self.channels = self.get_channels()

        self.setWindowTitle("Sensors Editor")
        self.resize(600, 400)

        # Main widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Table widget
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Sensor", "Pan","Tilt"])
        self.table.setEditTriggers(QTableWidget.AllEditTriggers)





        add_button = QPushButton("Add Row")
        delete_button = QPushButton("Delete Selected Row")
        save_button = QPushButton("Save")
        channels_label = QLabel("Channels")
        self.channels_dropdown = QComboBox()
        self.channels_dropdown.currentIndexChanged.connect(self.change_channel)



        add_button.clicked.connect(self.add_row)
        delete_button.clicked.connect(self.delete_row)
        save_button.clicked.connect(self.save_data)

        # Layouts
        button_layout = QHBoxLayout()
        button_layout.addWidget(add_button)
        button_layout.addWidget(delete_button)
        button_layout.addWidget(save_button)
        button_layout.addWidget(channels_label)
        button_layout.addWidget(self.channels_dropdown)

        layout = QVBoxLayout()
        layout.addWidget(self.table)
        layout.addLayout(button_layout)
        self.central_widget.setLayout(layout)

        # Load data
        self.load_data()

    def get_channels(self):
        with open(self.fixtures_file, "r") as f:
            fixture_data = json.load(f)
            return list(fixture_data.keys())


    def load_data(self):
        if not os.path.exists(self.file_name):
            with open(self.file_name, "w") as f:
                json.dump({}, f, indent=4)

        with open(self.file_name, "r") as f:
            try:
                file_data = json.load(f)
                self.data = file_data

            except json.JSONDecodeError:
                QMessageBox.critical(self, "Error", "Invalid JSON file. Starting with empty data.")
                self.data = {}

        self.populate_table()
        self.populate_channels()

    def populate_channels(self):
        self.channels_dropdown.clear()
        self.channels_dropdown.addItems(self.channels)

    def change_channel(self, index):
        self.active_channel = self.channels_dropdown.currentText()
        self.populate_table()


    def populate_table(self):
        self.table.setRowCount(0)
        # self.data looks like:
        # {"1": {"1": {"pan": -212.624568, "tilt": 52, "direction": 1}, "2": {"pan": 54.97087, "tilt": 45, "direction": -1}, "3": {"pan": 209.142801, "tilt": 51, "direction": -1}, "4": {"pan": -33.265662000000006, "tilt": 39, "direction": -1}}}

        for sensor_id, sensor_data in self.data.get(self.active_channel, {}).items():
            # sensor id is the key for which data is the value
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            self.table.setItem(row_position, 0, QTableWidgetItem(str(sensor_id)))
            self.table.setItem(row_position, 1, QTableWidgetItem(str(sensor_data.get("pan", ""))))
            self.table.setItem(row_position, 2, QTableWidgetItem(str(sensor_data.get("tilt", ""))))

        if self.table.rowCount() == 0:
            for i in range(4):
                self.add_row()
            for row in range(self.table.rowCount()):
                self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))




    def add_row(self):
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        self.table.setItem(row_position, 0, QTableWidgetItem(str(row_position + 1)))

    def delete_row(self):
        selected_rows = self.table.selectionModel().selectedRows()
        for index in sorted(selected_rows, reverse=True):
            self.table.removeRow(index.row())

    def save_data(self):
        new_data = self.data.copy()  # Start with existing data to preserve other channels

        def safe_text(item):
            """
            Safely get text from a QTableWidgetItem.
            Returns an empty string if the item is None.
            """
            return item.text().strip() if item is not None else ""

        # Initialize the active channel in new_data if it doesn't exist
        if self.active_channel not in new_data:
            new_data[self.active_channel] = {}

        # Update the active channel's data with the current table data
        for row in range(self.table.rowCount()):
            sensor_id_item = self.table.item(row, 0)
            pan_item = self.table.item(row, 1)
            tilt_item = self.table.item(row, 2)

            if sensor_id_item:
                sensor_id = sensor_id_item.text().strip()
                pan_text = safe_text(pan_item)
                tilt_text = safe_text(tilt_item)

                # Validate and convert pan and tilt values
                pan = float(pan_text) if pan_text.lstrip('-').replace('.', '', 1).isdigit() else 0.0
                tilt = float(tilt_text) if tilt_text.lstrip('-').replace('.', '', 1).isdigit() else 0.0

                new_data[self.active_channel][sensor_id] = {
                    "pan": pan,
                    "tilt": tilt,
                }

        print("Saving Data:", new_data)  # Debugging line to see exactly what is being saved

        # Write the updated data back to the JSON file
        with open(self.file_name, "w") as f:
            json.dump(new_data, f, indent=4)

        self.data = new_data  # Update the instance's data to the new data

        self.data_saved.emit()
        QMessageBox.information(self, "Success", "Data saved successfully!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SensorsEditor()
    window.show()
    sys.exit(app.exec_())
