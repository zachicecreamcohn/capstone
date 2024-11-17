import numpy as np

class Navigator:
    def __init__(self, flask_backend, step_size=1.0, tolerance=0.1):
        """
        Initialize the Navigator.

        :param flask_backend: The Flask backend providing sensor data and accepting light control commands.
        :param step_size: Percentage increment for pan/tilt during exploration.
        :param tolerance: Intensity change threshold for significant detection.
        """
        self.backend = flask_backend
        self.step_size = step_size
        self.tolerance = tolerance
        self.pan = 50.0  # Start at home position
        self.tilt = 50.0
        self.sensors_data = None  # Updated with real-time sensor data
        self.target_sensor = None

    def get_sensor_data(self):
        """
        Fetch the latest sensor data from the Flask backend.
        """
        self.sensors_data = self.backend.get_sensor_data()
        return self.sensors_data

    def send_light_command(self, pan, tilt):
        """
        Send the pan and tilt command to the light fixture via the Flask backend.

        :param pan: Pan percentage (0-100).
        :param tilt: Tilt percentage (0-100).
        """
        self.backend.send_light_command(pan, tilt)
        self.pan = pan
        self.tilt = tilt

    def exploratory_phase(self):
        """
        Perform exploratory phase using concentric circles.
        """
        radius = self.tilt
        direction = 1  # Start moving pan in the increasing direction

        while True:
            # Increase tilt to expand the circle's radius
            radius += self.step_size
            if radius > 100 or radius < 0:
                break  # Stop if tilt goes out of range

            # Sweep pan from 50 to 100 or back to 50
            for pan in np.arange(50, 100 + direction, direction * self.step_size):
                self.send_light_command(pan, radius)
                self.get_sensor_data()
                if self.detect_significant_change():
                    return

            # Reverse direction of pan
            direction *= -1

    def detect_significant_change(self):
        """
        Check if there's a significant change in any sensor's intensity.
        """
        for sensor, intensity in self.sensors_data.items():
            if intensity > self.tolerance:
                self.target_sensor = sensor
                return True
        return False

    def directed_phase(self):
        """
        Perform directed phase to dynamically guide the light.
        """
        previous_intensity = -1

        while True:
            self.get_sensor_data()
            target_intensity = self.sensors_data[self.target_sensor]

            if target_intensity <= previous_intensity:
                break  # Stop if intensity does not improve

            # Adjust pan and tilt dynamically
            self.pan += self.step_size * (1 if target_intensity > previous_intensity else -1)
            self.tilt += self.step_size * (1 if target_intensity > previous_intensity else -1)

            self.send_light_command(self.pan, self.tilt)
            previous_intensity = target_intensity

    def verification_phase(self):
        """
        Perform verification phase to ensure the light is correctly pointed.
        """
        directions = [(self.step_size, 0), (-self.step_size, 0), (0, self.step_size), (0, -self.step_size)]
        initial_intensity = self.sensors_data[self.target_sensor]

        for d_pan, d_tilt in directions:
            self.send_light_command(self.pan + d_pan, self.tilt + d_tilt)
            self.get_sensor_data()
            if self.sensors_data[self.target_sensor] >= initial_intensity:
                return False  # If intensity increases, it is not pointing correctly

        return True

    def execute(self):
        """
        Execute the full algorithm.
        """
        # Phase 1: Exploratory
        self.exploratory_phase()

        # Phase 2: Directed
        self.directed_phase()

        # Phase 3: Verification
        if self.verification_phase():
            return self.pan, self.tilt  # Final position of the light
        else:
            raise Exception("Verification failed. The light is not pointing at the sensor.")
