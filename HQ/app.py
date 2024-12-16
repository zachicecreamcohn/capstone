import json
import tkinter as tk
from gevent import pywsgi, sleep, spawn
from geventwebsocket.handler import WebSocketHandler
from collections import defaultdict
from gevent.lock import Semaphore
from navigator import Navigator, Phase
from GUI import SensorGUI
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# disable loggin for debuging
logging.disable(logging.DEBUG)
class LightControlApp:
    def __init__(self, debounce_interval=0.1, debounce_enabled=True):
        self.sensor_data = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        self.buffers = defaultdict(list)
        self.lock = Semaphore()
        self.debounce_interval = debounce_interval
        self.debounce_enabled = debounce_enabled
        self.gui = None
        spawn(self.run_gui)
        sleep(1)  # wait for gui to start
        # Pass sensor_data and lock to Navigator
        self.navigator = Navigator(sensor_data=self.sensor_data, gui=self.gui, lock=self.lock)

        spawn(self.debounce_loop)
        spawn(self.navigator_loop)

    def run_gui(self):
        root = tk.Tk()
        self.gui = SensorGUI(root)
        try:
            while True:
                root.update_idletasks()
                root.update()
                sleep(0.01)
        except tk.TclError:
            logging.info("GUI closed.")

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
            sleep(self.debounce_interval)

    def navigator_loop(self):
        sleep(1)  # Shortened wait for quicker startup
        logging.info("Navigator loop started.")

        while True:
            # Execute Navigator with access to live sensor_data
            navigator_state = self.navigator.execute()
            logging.info(f"Navigator state: {navigator_state}")

            current_phase = navigator_state["current_phase"]
            if current_phase in ["COMPLETE", "FAILED"]:
                logging.info(f"Navigator {current_phase.lower()}. Waiting for new data...")
                sleep(5)
            else:
                sleep(0.1)

    def websocket_handler(self, environ, start_response):
        ws = environ.get('wsgi.websocket')
        if ws is None:
            start_response('400 Bad Request', [('Content-Type', 'text/plain')])
            return [b'WebSocket connection expected']

        logging.info("WebSocket connection established.")
        try:
            while True:
                message = ws.receive()
                if message is None:
                    logging.info("WebSocket connection closed by client.")
                    break

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
                        ws.send(json.dumps({"error": error_msg}))
                except json.JSONDecodeError:
                    error_msg = "Invalid JSON format."
                    logging.warning(error_msg)
                    ws.send(json.dumps({"error": error_msg}))
                except Exception as e:
                    error_msg = f"Server error: {str(e)}"
                    logging.error(error_msg)
                    ws.send(json.dumps({"error": error_msg}))
        except Exception as e:
            logging.error(f"WebSocket handler error: {str(e)}")
        finally:
            logging.info("WebSocket connection handler terminating.")
        return []

if __name__ == '__main__':
    app = LightControlApp(debounce_interval=0.1)
    server = pywsgi.WSGIServer(('0.0.0.0', 8765), app.websocket_handler, handler_class=WebSocketHandler)
    logging.info("WebSocket server running on ws://0.0.0.0:8765")
    server.serve_forever()
