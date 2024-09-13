from EOS import EOS
import tkinter as tk

# Set the IP and port of the OSC receiver
ip = "10.0.0.2"  # Replace with the IP of the receiving device
port = 8000  # Replace with the correct port for OSC




class LightControlGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Light Control")
        self.master.geometry("400x400")

        # Create a canvas where you can track the mouse movement
        self.canvas = tk.Canvas(master, width=400, height=400, bg="white")
        self.canvas.pack()

        # Bind mouse motion to the callback function
        self.canvas.bind("<Motion>", self.mouse_move)

        # Initialize EOS object
        self.eos = EOS(ip, port)

    def mouse_move(self, event):
        # Get mouse x, y coordinates
        x, y = event.x, event.y

        # Get canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Convert mouse position to pan and tilt values (0-100)
        pan = (x / canvas_width) * 100
        tilt = (y / canvas_height) * 100

        # Ensure pan and tilt values stay within 0-100
        pan = min(max(int(pan), 0), 100)
        tilt = min(max(int(tilt), 0), 100)

        # Display coordinates and values
        self.master.title(f"Pan: {pan}, Tilt: {tilt}")

        # Set pan and tilt based on mouse position
        self.eos.set_pan(1, pan, "r2x")
        self.eos.set_tilt(1, tilt, "r2x")

        # Optionally, you can draw something on the canvas to visualize the point
        self.canvas.delete("all")  # Clear previous drawings
        self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="red")


# Main entry point
if __name__ == "__main__":
    root = tk.Tk()
    gui = LightControlGUI(root)
    root.mainloop()
