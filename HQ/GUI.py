import tkinter as tk

class SensorGUI:
    def __init__(self, master, eos=None, recalibrate_state=None):
        self.master = master
        self.eos = eos
        self.master.title("Sensor Positioning")

        self.canvas_width = 800
        self.canvas_height = 600
        self.canvas = tk.Canvas(self.master, width=self.canvas_width, height=self.canvas_height, bg="white")
        self.canvas.pack()

        self.sensors = {}
        self.create_sensor(1, 100, 100)
        self.create_sensor(2, 700, 100)
        self.create_sensor(3, 100, 500)
        self.create_sensor(4, 700, 500)

        self.print_button = tk.Button(self.master, text="Print Sensor Positions", command=self.print_sensor_positions)
        self.print_button.pack(pady=10)

        self.reset_button = tk.Button(self.master, text="Reset Sensor Positions", command=self.reset_positions)
        self.reset_button.pack(pady=10)

        self.lock_button = tk.Button(self.master, text="Toggle Lock", command=self.toggle_lock)
        self.lock_button.pack(pady=10)

        self.recalibrate_button = tk.Button(self.master, text="Recalibrate", command=self.recalibrate)
        self.recalibrate_button.pack(pady=10)

        self.lock_sensors = False
        self.canvas.bind("<Button-1>", self.on_click)

    def create_sensor(self, sensor_id, x, y):
        rect_size = 50
        rect = self.canvas.create_rectangle(
            x, y, x + rect_size, y + rect_size, fill="lightblue", tags=f"sensor_{sensor_id}"
        )
        text = self.canvas.create_text(
            x + rect_size / 2, y + rect_size / 2, text=str(sensor_id), tags=f"sensor_{sensor_id}"
        )

        self.canvas.tag_bind(f"sensor_{sensor_id}", "<Button-1>", self.start_drag)
        self.canvas.tag_bind(f"sensor_{sensor_id}", "<B1-Motion>", self.drag)

        self.sensors[sensor_id] = rect

    def recalibrate(self):
        # TODO: Implement recalibration logic
        pass

    def toggle_lock(self):
        self.lock_sensors = not self.lock_sensors
        print(f"Sensors {'locked' if self.lock_sensors else 'unlocked'}.")

    def on_click(self, event):
        if self.lock_sensors:
            self.move(event.x, event.y)

    def move(self, x, y):
        print(f"Move triggered at ({x}, {y}).")
        sensor_positions = self.get_sensor_positions()
        self.eos.move_to_point(x,y, sensor_positions[1], sensor_positions[2], sensor_positions[3], sensor_positions[4], "r1")

    def start_drag(self, event):
        if not self.lock_sensors:
            self.drag_data = {
                "x": event.x,
                "y": event.y,
                "tags": self.canvas.gettags(tk.CURRENT),
            }

    def drag(self, event):
        if not self.lock_sensors:
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            for tag in self.drag_data["tags"]:
                if tag.startswith("sensor_"):
                    self.canvas.move(tag, dx, dy)
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

    def print_sensor_positions(self):
        pass

    def get_sensor_positions(self):
        sensor_positions = {}
        for sensor_id, rect in self.sensors.items():
            coords = self.canvas.coords(rect)
            sensor_positions[sensor_id] = (coords[0], coords[1])
        return sensor_positions

    def get_gui_dimensions(self):
        return self.canvas_width, self.canvas_height

    def get_sensor_ids(self):
        return list(self.sensors.keys())

    def reset_positions(self):
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
