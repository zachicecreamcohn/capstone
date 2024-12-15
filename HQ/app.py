import json
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from collections import defaultdict
from gevent import sleep, spawn
from gevent.lock import Semaphore
from navigator import Navigator, Phase

class LightControlApp:
    def __init__(self, debounce_interval=0.2):
        self.sensor_data = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        self.buffers = defaultdict(list)
        self.lock = Semaphore()
        self.debounce_interval = debounce_interval
        self.navigator_state = None
        self.navigator = None
        spawn(self.debounce_loop)
        spawn(self.navigator_loop)

    def add_sensor_reading(self, sensor_ID, intensity):
        sensor_ID = int(sensor_ID)  # Convert to integer
        intensity = float(intensity)  # Normalize intensity
        with self.lock:
            if sensor_ID in self.sensor_data:
                self.buffers[sensor_ID].append(intensity)

    def debounce_loop(self):
        while True:
            with self.lock:
                for sensor_ID, buffer in self.buffers.items():
                    if buffer:
                        avg_intensity = sum(buffer) / len(buffer)
                        self.sensor_data[sensor_ID] = avg_intensity
                        self.buffers[sensor_ID] = []
                        print(f"Updated intensity of sensor {sensor_ID}: {avg_intensity}")

                # Log the current intensity of sensor 1 only once after updates
                print(f"Current intensity of sensor 1 (debounced): {self.sensor_data[1]}")

            sleep(self.debounce_interval)

    def navigator_loop(self):
        while True:
            with self.lock:
                print(f"Sensor data before passing to Navigator: {self.sensor_data}")
                sensor_data_copy = self.sensor_data.copy()

            if self.navigator is None:
                self.navigator = Navigator(sensor_data_copy, persisted_state=self.navigator_state)
            else:
                self.navigator.sensors_data = sensor_data_copy

            self.navigator_state = self.navigator.execute()

            if self.navigator_state["current_phase"] == Phase.COMPLETE.name:
                print(f"Navigator completed: pan={self.navigator_state['pan']}, tilt={self.navigator_state['tilt']}")
                break
            elif self.navigator_state["current_phase"] == Phase.EXPLORATORY_FAILED.name:
                print("Exploratory phase failed")
                break

            # Avoid redundant logging by consolidating `Current intensity` logs
            print(f"Phase : {self.navigator_state['current_phase']}")

            sleep(self.debounce_interval)

    def websocket_handler(self, environ, start_response):
        ws = environ.get('wsgi.websocket')
        if ws is None:
            start_response('400 Bad Request', [('Content-Type', 'text/plain')])
            return [b'WebSocket connection expected']

        while True:
            try:
                message = ws.receive()
                if message is None:
                    print("No message received. Closing connection.")
                    break

                json_data = json.loads(message)
                if "sensorId" in json_data and "value" in json_data:
                    sensor_ID = int(json_data["sensorId"])
                    value = float(json_data["value"])
                    print(f"Received sensor reading: sensorId={sensor_ID}, value={value}")
                    self.add_sensor_reading(sensor_ID, value)
                else:
                    print("Invalid data format. Expected {'sensorId': 1, 'value': 0.5}")
                    ws.send(json.dumps({"error": "Invalid data format. Expected {'sensorId': 1, 'value': 0.5}"}))
            except json.JSONDecodeError:
                ws.send(json.dumps({"error": "Invalid JSON format"}))
            except Exception as e:
                ws.send(json.dumps({"error": f"Server error: {str(e)}"}))

        return []

if __name__ == '__main__':
    app = LightControlApp(debounce_interval=0.2)
    server = pywsgi.WSGIServer(('0.0.0.0', 8765), app.websocket_handler, handler_class=WebSocketHandler)

    print("WebSocket server running on ws://0.0.0.0:8765")
    server.serve_forever()
