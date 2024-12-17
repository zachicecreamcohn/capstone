import json
import sys
import threading
import time
import logging
import queue
from collections import defaultdict
from threading import Lock

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal, QObject

import asyncio
import websockets

from navigator import Navigator, Phase
from GUI import SensorGUI
from EOS import EOS

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# Disable debug logging for this page
logging.getLogger().setLevel(logging.INFO)

# Define a QObject to handle signals between threads and GUI
class Communicator(QObject):
    update_label = pyqtSignal(str)

class LightControlApp:
    def __init__(self, debounce_interval=0.1, debounce_enabled=True):
        self.sensor_data = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        self.buffers = defaultdict(list)
        self.lock = Lock()
        self.debounce_interval = debounce_interval
        self.debounce_enabled = debounce_enabled
        self.gui = None

        self.eos = EOS("192.168.1.105", 8000)
        self.comm = Communicator()
        self.comm.update_label.connect(self.update_gui_label)

        # Queue for inter-thread communication
        self.progress_queue = queue.Queue()

        # Initialize Navigator with sensor_data and lock
        self.navigator = Navigator(eos=self.eos, sensor_data=self.sensor_data, gui=self.gui, lock=self.lock)

    def update_gui_label(self, message):
        if self.gui and hasattr(self.gui, 'progress_label'):
            self.gui.progress_label.setText(message)
        else:
            logging.info(f"GUI Label Update: {message}")

    def add_sensor_reading(self, sensor_ID, intensity):
        sensor_ID = int(sensor_ID)
        intensity = float(intensity)
        with self.lock:
            if self.debounce_enabled:
                self.buffers[sensor_ID].append(intensity)
                logging.debug(f"Added intensity {intensity} to buffer for sensor {sensor_ID}")
            else:
                self.sensor_data[sensor_ID] = intensity
                logging.debug(f"Set intensity {intensity} for sensor {sensor_ID}")

    def debounce_loop(self):
        while True:
            with self.lock:
                if self.debounce_enabled:
                    for sensor_ID, buffer in self.buffers.items():
                        if buffer:
                            avg_intensity = sum(buffer) / len(buffer)
                            self.sensor_data[sensor_ID] = avg_intensity
                            logging.debug(f"Debounced sensor {sensor_ID}: {avg_intensity}")
                            self.buffers[sensor_ID] = []
            time.sleep(self.debounce_interval)

    def navigator_loop(self):
        time.sleep(1)  # Shortened wait for quicker startup
        logging.info("Navigator loop started.")

        while True:
            if not self.eos.sensors_data_file_is_valid():
                # Execute Navigator with access to live sensor_data
                navigator_state = self.navigator.execute()
                logging.info(f"Navigator state: {navigator_state}")

                current_phase = navigator_state["current_phase"]
                if current_phase == Phase.FAILED:
                    logging.info(f"Navigator failed. Resetting sensor positions.")
                    time.sleep(5)
                elif current_phase == Phase.COMPLETE:
                    for sensor_ID in self.sensor_data:
                        logging.info(f"Sensor {sensor_ID}: {self.eos.get_sensor_data(sensor_ID)}")
                else:
                    time.sleep(0.2)
            else:
                time.sleep(0.2)

    async def websocket_handler(self, websocket, path):
        logging.info("WebSocket connection established.")
        try:
            async for message in websocket:
                logging.debug(f"Received message: {message}")
                try:
                    json_data = json.loads(message)
                    if "sensorId" in json_data and "value" in json_data:
                        sensor_ID = int(json_data["sensorId"])
                        value = float(json_data["value"])
                        self.add_sensor_reading(sensor_ID, value)
                        logging.debug(f"Updated sensor_data: {self.sensor_data}")
                    else:
                        error_msg = "Invalid data format."
                        logging.warning(error_msg)
                        await websocket.send(json.dumps({"error": error_msg}))
                except json.JSONDecodeError:
                    error_msg = "Invalid JSON format."
                    logging.warning(error_msg)
                    await websocket.send(json.dumps({"error": error_msg}))
                except Exception as e:
                    error_msg = f"Server error: {str(e)}"
                    logging.error(error_msg)
                    await websocket.send(json.dumps({"error": error_msg}))
        except websockets.exceptions.ConnectionClosed:
            logging.info("WebSocket connection closed by client.")
        except Exception as e:
            logging.error(f"WebSocket handler error: {str(e)}")
        finally:
            logging.info("WebSocket connection handler terminating.")

    async def websocket_server_coroutine(self):
        async with websockets.serve(self.websocket_handler, '0.0.0.0', 8765):
            logging.info("WebSocket server running on ws://0.0.0.0:8765")
            await asyncio.Future()  # Run forever

    def run_websocket_server(self):
        try:
            asyncio.run(self.websocket_server_coroutine())
        except Exception as e:
            logging.error(f"WebSocket server encountered an error: {e}")

    def start_background_threads(self):
        threading.Thread(target=self.debounce_loop, daemon=True).start()
        threading.Thread(target=self.navigator_loop, daemon=True).start()
        threading.Thread(target=self.run_websocket_server, daemon=True).start()

    def start(self):
        app = QtWidgets.QApplication(sys.argv)
        self.gui = SensorGUI(eos=self.eos)
        self.comm.update_label.connect(self.update_gui_label)
        self.gui.show()

        # Start background threads after GUI is initialized
        self.start_background_threads()

        sys.exit(app.exec_())

if __name__ == '__main__':
    app = LightControlApp(debounce_interval=0.1)
    app.start()
