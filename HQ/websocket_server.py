from flask import Flask
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)

@sock.route('/echo')
def echo(ws):
    print("Client connected")
    try:
        while True:
            message = ws.receive()
            print(f"Received message: {message}")
            ws.send(f"Echo: {message}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Client disconnected")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8765)
