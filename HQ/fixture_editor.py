import sys
import json
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget, QPushButton, QHBoxLayout, QMessageBox
)
from PyQt5.QtCore import pyqtSignal


class FixtureEditor(QMainWindow):

    data_saved = pyqtSignal()

    def __init__(self, file_name=".fixtures.json"):
        super().__init__()
        self.file_name = file_name
        self.data = {}

        self.setWindowTitle("Fixture Editor")
        self.resize(600, 400)

        # Main widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Table widget
        self.table = QTableWidget(0, 5)  # Rows, Columns
        self.table.setHorizontalHeaderLabels(["Channel", "Max Tilt", "Min Tilt", "Max Pan", "Min Pan"])
        self.table.setEditTriggers(QTableWidget.AllEditTriggers)

        # Buttons
        add_button = QPushButton("Add Row")
        delete_button = QPushButton("Delete Selected Row")
        save_button = QPushButton("Save")

        add_button.clicked.connect(self.add_row)
        delete_button.clicked.connect(self.delete_row)
        save_button.clicked.connect(self.save_data)

        # Layouts
        button_layout = QHBoxLayout()
        button_layout.addWidget(add_button)
        button_layout.addWidget(delete_button)
        button_layout.addWidget(save_button)

        layout = QVBoxLayout()
        layout.addWidget(self.table)
        layout.addLayout(button_layout)
        self.central_widget.setLayout(layout)

        # Load data
        self.load_data()

    def load_data(self):
        if not os.path.exists(self.file_name):
            with open(self.file_name, "w") as f:
                json.dump({}, f, indent=4)

        with open(self.file_name, "r") as f:
            try:
                self.data = json.load(f)
            except json.JSONDecodeError:
                QMessageBox.critical(self, "Error", "Invalid JSON file. Starting with empty data.")
                self.data = {}

        self.populate_table()

    def populate_table(self):
        self.table.setRowCount(0)
        for channel, values in self.data.items():
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)

            self.table.setItem(row_position, 0, QTableWidgetItem(channel))
            self.table.setItem(row_position, 1, QTableWidgetItem(str(values.get("max_tilt", ""))))
            self.table.setItem(row_position, 2, QTableWidgetItem(str(values.get("min_tilt", ""))))
            self.table.setItem(row_position, 3, QTableWidgetItem(str(values.get("max_pan", ""))))
            self.table.setItem(row_position, 4, QTableWidgetItem(str(values.get("min_pan", ""))))

    def add_row(self):
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        self.table.setItem(row_position, 0, QTableWidgetItem(str(row_position + 1)))

    def delete_row(self):
        selected_rows = self.table.selectionModel().selectedRows()
        for index in sorted(selected_rows, reverse=True):
            self.table.removeRow(index.row())

    def save_data(self):
        new_data = {}

        def safe_text(item):
            """
            Safely get text from a QTableWidgetItem.
            Returns an empty string if the item is None.
            """
            return item.text().strip() if item is not None else ""

        for row in range(self.table.rowCount()):
            channel_item = self.table.item(row, 0)
            max_tilt_item = self.table.item(row, 1)
            min_tilt_item = self.table.item(row, 2)
            max_pan_item = self.table.item(row, 3)
            min_pan_item = self.table.item(row, 4)

            if channel_item:
                channel = channel_item.text().strip()
                new_data[channel] = {
                    "max_tilt": int(safe_text(max_tilt_item)) if safe_text(max_tilt_item).lstrip('-').isdigit() else 0,
                    "min_tilt": int(safe_text(min_tilt_item)) if safe_text(min_tilt_item).lstrip('-').isdigit() else 0,
                    "max_pan": int(safe_text(max_pan_item)) if safe_text(max_pan_item).lstrip('-').isdigit() else 0,
                    "min_pan": int(safe_text(min_pan_item)) if safe_text(min_pan_item).lstrip('-').isdigit() else 0,
                }

        print("Saving Data:", new_data)  # Debugging line to see exactly what is being saved
        with open(self.file_name, "w") as f:
            json.dump(new_data, f, indent=4)

        self.data_saved.emit()
        QMessageBox.information(self, "Success", "Data saved successfully!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FixtureEditor()
    window.show()
    sys.exit(app.exec_())
