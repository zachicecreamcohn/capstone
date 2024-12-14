import json
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler

class LightControlApp:
    def __init__(self):
        self.sensor_data = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        self.light_state = {"pan": 50.0, "tilt": 50.0}  # Start at home position

    def update_sensor_data(self, sensor_ID, intensity):
        """Update the app's sensor data."""
        if sensor_ID in self.sensor_data:
            self.sensor_data[sensor_ID] = intensity
            print(f"Sensor {sensor_ID} updated with intensity: {intensity}")
        else:
            print(f"Sensor {sensor_ID} not found in sensor data.")

    def websocket_handler(self, environ, start_response):
        """Handle WebSocket connections."""
        ws = environ.get('wsgi.websocket')  # Get the WebSocket object from environ
        if ws is None:
            # If the request is not a valid WebSocket upgrade, return an error
            start_response('400 Bad Request', [('Content-Type', 'text/plain')])
            return [b'WebSocket connection expected']

        # Process WebSocket messages
        while True:
            try:
                message = ws.receive()  # Receive a message from the client
                if message is None:
                    break  # Client disconnected

                json_data = json.loads(message)
                if "sensorID" in json_data and "intensity" in json_data:
                    self.update_sensor_data(json_data["sensorID"], json_data["intensity"])
                else:
                    # Send an error message if data format is invalid
                    ws.send(json.dumps({"error": "Invalid data format. Expected {'sensorID': 1, 'intensity': 0.5}"}))
            except json.JSONDecodeError:
                ws.send(json.dumps({"error": "Invalid JSON format"}))
            except Exception as e:
                ws.send(json.dumps({"error": f"Server error: {str(e)}"}))

        # Ensure we return an empty iterable to satisfy WSGI spec
        return []


if __name__ == '__main__':
    # Initialize the application
    app = LightControlApp()

    # Create the WebSocket server using gevent
    server = pywsgi.WSGIServer(('0.0.0.0', 8765), app.websocket_handler, handler_class=WebSocketHandler)

    print("WebSocket server running on ws://0.0.0.0:8765")
    server.serve_forever()
