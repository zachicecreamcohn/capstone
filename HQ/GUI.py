import tkinter as tk

class SensorGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Sensor Positioning")

        # Create the canvas
        self.canvas_width = 800
        self.canvas_height = 600
        self.canvas = tk.Canvas(self.master, width=self.canvas_width, height=self.canvas_height, bg="white")
        self.canvas.pack()

        # Create the rectangles representing the sensors
        self.sensors = {}
        self.create_sensor(1, 100, 100)
        self.create_sensor(2, 700, 100)
        self.create_sensor(3, 100, 500)
        self.create_sensor(4, 700, 500)

        # Add a button to print sensor positions
        self.print_button = tk.Button(self.master, text="Print Sensor Positions", command=self.print_sensor_positions)
        self.print_button.pack(pady=10)

        # Add a button to reset sensor positions
        self.reset_button = tk.Button(self.master, text="Reset Sensor Positions", command=self.reset_positions)
        self.reset_button.pack(pady=10)

    def create_sensor(self, sensor_id, x, y):
        # Create a rectangle with a label
        rect_size = 50
        rect = self.canvas.create_rectangle(
            x, y, x + rect_size, y + rect_size, fill="lightblue", tags=f"sensor_{sensor_id}"
        )
        text = self.canvas.create_text(
            x + rect_size / 2, y + rect_size / 2, text=str(sensor_id), tags=f"sensor_{sensor_id}"
        )

        # Make the rectangle draggable
        self.canvas.tag_bind(f"sensor_{sensor_id}", "<Button-1>", self.start_drag)
        self.canvas.tag_bind(f"sensor_{sensor_id}", "<B1-Motion>", self.drag)

        # Store sensor's rectangle and tags
        self.sensors[sensor_id] = rect

    def start_drag(self, event):
        # Record the start position of a drag and the target sensor tag
        self.drag_data = {
            "x": event.x,
            "y": event.y,
            "tags": self.canvas.gettags(tk.CURRENT),  # Get tags of the clicked item
        }

    def drag(self, event):
        # Update the position of all items in the group (rectangle + text)
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]

        # Move all items with the same tag
        for tag in self.drag_data["tags"]:
            if tag.startswith("sensor_"):
                self.canvas.move(tag, dx, dy)

        # Update drag_data coordinates
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def print_sensor_positions(self):
        # Print the current positions of all sensors
        for sensor_id, rect in self.sensors.items():
            coords = self.canvas.coords(rect)
            print(f"Sensor {sensor_id}: {coords}")

    def get_sensor_positions(self):
        # Return the current positions of all sensors
        sensor_positions = {}
        for sensor_id, rect in self.sensors.items():
            coords = self.canvas.coords(rect)
            sensor_positions[sensor_id] = (coords[0], coords[1])
        return sensor_positions

    def reset_positions(self):
        # Reset sensor positions to their default locations
        default_positions = {
            1: (100, 100),
            2: (700, 100),
            3: (100, 500),
            4: (700, 500),
        }

        for sensor_id, rect in self.sensors.items():
            x, y = default_positions[sensor_id]
            rect_size = 50
            self.canvas.coords(rect, x, y, x + rect_size, y + rect_size)
            self.canvas.coords(
                self.canvas.find_withtag(f"sensor_{sensor_id}")[1],
                x + rect_size / 2,
                y + rect_size / 2,
            )


if __name__ == "__main__":
    root = tk.Tk()
    gui = SensorGUI(root)
    root.mainloop()
