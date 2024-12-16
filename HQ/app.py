import json
import tkinter as tk
from gevent import pywsgi, sleep, spawn
from geventwebsocket.handler import WebSocketHandler
from collections import defaultdict
from gevent.lock import Semaphore
from navigator import Navigator, Phase
from GUI import SensorGUI
import logging
from EOS import EOS  # Ensure EOS module is correctly imported

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# disable debug logging for this page

class LightControlApp:
    def __init__(self, debounce_interval=0.1, debounce_enabled=True):
        self.sensor_data = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        self.buffers = defaultdict(list)
        self.lock = Semaphore()
        self.debounce_interval = debounce_interval
        self.debounce_enabled = debounce_enabled
        self.gui = None

        self.eos = EOS("192.168.1.105", 8000)
        self.gui_thread = spawn(self.run_gui)  # Run GUI in a dedicated thread

        sleep(1)  # Wait for the GUI to initialize

        self.navigator = Navigator(eos=self.eos, sensor_data=self.sensor_data, gui=self.gui, lock=self.lock)

        spawn(self.debounce_loop)  # Background task for debounce
        spawn(self.navigator_loop)  # Background task for navigator

    def run_gui(self):
        root = tk.Tk()
        self.gui = SensorGUI(root, eos=self.eos)
        try:
            root.mainloop()  # Let Tkinter manage the event loop
        except tk.TclError:
            logging.info("GUI closed.")

    def add_sensor_reading(self, sensor_ID, intensity):
        sensor_ID = int(sensor_ID)
        intensity = float(intensity)
        with self.lock:
            if self.debounce_enabled:
                self.buffers[sensor_ID].append(intensity)
            else:
                self.sensor_data[sensor_ID] = intensity

    def debounce_loop(self):
        while True:
            with self.lock:
                if self.debounce_enabled:
                    for sensor_ID, buffer in self.buffers.items():
                        if buffer:
                            avg_intensity = sum(buffer) / len(buffer)
                            self.sensor_data[sensor_ID] = avg_intensity
                            self.buffers[sensor_ID] = []
            sleep(self.debounce_interval)

    def navigator_loop(self):
        sleep(1)
        while True:
            if self.gui and self.gui.recalibrate:
                navigator_state = self.navigator.execute()
                current_phase = navigator_state["current_phase"]

                if current_phase == Phase.FAILED:
                    sleep(5)
                elif current_phase == Phase.COMPLETE:
                    for sensor_ID in self.sensor_data:
                        logging.info(f"Sensor {sensor_ID}: {self.eos.get_sensor_data(sensor_ID)}")
                else:
                    sleep(0.2)

    def websocket_handler(self, environ, start_response):
        ws = environ.get('wsgi.websocket')
        if ws is None:
            start_response('400 Bad Request', [('Content-Type', 'text/plain')])
            return [b'WebSocket connection expected']

        try:
            while True:
                message = ws.receive()
                if message is None:
                    break

                try:
                    json_data = json.loads(message)
                    if "sensorId" in json_data and "value" in json_data:
                        sensor_ID = int(json_data["sensorId"])
                        value = float(json_data["value"])
                        self.add_sensor_reading(sensor_ID, value)
                except json.JSONDecodeError:
                    ws.send(json.dumps({"error": "Invalid JSON format."}))
                except Exception as e:
                    ws.send(json.dumps({"error": f"Server error: {str(e)}"}))
        finally:
            logging.info("WebSocket connection closed.")
        return []

if __name__ == '__main__':
    app = LightControlApp(debounce_interval=0.1)
    server = pywsgi.WSGIServer(('0.0.0.0', 8765), app.websocket_handler, handler_class=WebSocketHandler)
    logging.info("WebSocket server running on ws://0.0.0.0:8765")
    server.serve_forever()
