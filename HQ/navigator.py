from enum import Enum
import json
import numpy as np
from gevent import sleep
import logging
from collections import deque
from threading import Lock

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class Phase(Enum):
    SETUP = "setup"
    LOCATE = "locate"
    COMPLETE = "complete"
    CALCULATE = "calculate"
    FAILED = "failed"

class Navigator:
    def __init__(self, eos=None, gui=None, sensor_data=None, lock=None):
        self.gui = gui
        self.eos = eos
        self.current_phase = Phase.SETUP
        self.pan = 0.0  # Current pan angle
        self.tilt = 0.0  # Current tilt angle
        self.best_intensity = -1
        self.sensor_baselines = {}
        self.sensor_data = sensor_data if sensor_data is not None else {}
        self.lock = lock if lock is not None else Lock()
        self.sensor_history = {}


        # Parameters for centroid-based navigation
        self.initial_step_size = 15.0  # degrees
        self.step_size = self.initial_step_size  # Current step size
        self.min_step_size = 0.1  # Minimum step size for fine adjustments
        self.step_decrement = 0.5  # How much to reduce step size after certain steps
        self.max_steps = 1500  # Prevent infinite loops
        self.tolerance = 2.0  # Centroid distance tolerance (units consistent with sensor positions)

        # Threshold to determine if sensor data is close to baseline
        self.baseline_threshold = 0.1  # Adjust as needed

        # Parameters for moving average filter
        self.history_length = 5  # Number of samples for moving average
        self.sensor_history = {}
        if self.gui:
            sensor_ids = self.gui.get_sensor_ids()
            self.sensor_history = {sensor_id: [] for sensor_id in sensor_ids}
        else:
            logging.error("GUI object is not provided. Sensor history cannot be initialized.")

        # Mechanical constraints (adjust as per your hardware specifications)
        self.min_pan, self.max_pan = self.eos.get_pan_range("r1")
        self.min_tilt, self.max_tilt = self.eos.get_tilt_range("r1")

    def send_light_command(self, pan_move, tilt_move, use_degrees=True):
        """
        Sends pan and tilt commands to the EOS controller and updates current angles.
        Ensures that the new angles are within mechanical constraints.
        """
        # Calculate proposed new angles
        proposed_pan = self.pan + pan_move
        proposed_tilt = self.tilt + tilt_move

        # Clamp angles within mechanical limits
        proposed_pan = max(self.min_pan, min(self.max_pan, proposed_pan))
        proposed_tilt = max(self.min_tilt, min(self.max_tilt, proposed_tilt))

        # Calculate actual movement after clamping
        actual_pan_move = proposed_pan - self.pan
        actual_tilt_move = proposed_tilt - self.tilt

        # Send commands only if there's a change
        if actual_pan_move != 0 or actual_tilt_move != 0:
            try:
                self.eos.set_pan(1, self.pan, actual_pan_move, "r1", use_degrees)
                self.eos.set_tilt(1, self.tilt, actual_tilt_move, "r1", use_degrees)
                self.pan = proposed_pan
                self.tilt = proposed_tilt
                logging.debug(f"Sent pan_move: {actual_pan_move}, tilt_move: {actual_tilt_move}. New pan: {self.pan}, New tilt: {self.tilt}")

            except Exception as e:
                logging.error(f"Failed to send pan/tilt commands: {e}")
        else:
            logging.debug("Pan and tilt moves are within mechanical limits. No movement sent.")

    def setup_phase(self):
        """
        Initializes the system by resetting pan and tilt, setting intensity,
        and establishing sensor baselines.
        """
        logging.info("Entering SETUP phase.")
        initial_pan, initial_tilt = 0, 0
        self.send_light_command(initial_pan, initial_tilt)
        try:
            self.eos.set_intensity(1, 0)  # Set light intensity to a known value
            logging.debug("Set light intensity to 0.")
        except Exception as e:
            logging.error(f"Failed to set light intensity: {e}")

        sleep(5)  # Wait for system to stabilize

        # Set baselines using moving average filter
        self.sensor_baselines = self.get_new_data()
        logging.info(f"Sensor baselines: {self.sensor_baselines}")

        # Initialize best_intensity based on target sensor
        self.eos.set_intensity(1, 100)
        logging.debug(f"Setup complete. Baseline intensity: {self.best_intensity}")

        return Phase.LOCATE

    def locate_phase(self):
        # move in expanding concentric circles until the taret sensor picks up significant changes
        logging.info("Entering EXPLORE phase.")

        # Move the light in a spiral pattern
        max_tilt = self.eos.get_tilt_range("r1")[1]
        min_pan, max_pan = self.eos.get_pan_range("r1")
        pan_move_step = 1
        tilt_move_step = 1

        self.send_light_command(min_pan, 0, use_degrees=True)


        scan_pan = min_pan
        scan_tilt = 0
        direction = 1
        max_scan_tilt = 85
        while True:
            # set tilt
            for i in range(0, max_pan, pan_move_step):
                self.eos.set_pan(1,0,scan_pan, "r1", use_degrees=True)
                self.eos.set_tilt(1,0,scan_tilt, "r1", use_degrees=True)
                self.pan = scan_pan
                self.tilt = scan_tilt
                sleep(0.02)

                # get the intensity data for each sensor and store it in history with the pan/tilt values
                sensor_data = self.get_new_data()
                for sensor_id, intensity in sensor_data.items():
                    if sensor_id not in self.sensor_history:
                        self.sensor_history[sensor_id] = []
                    self.sensor_history[sensor_id].append({"intensity": intensity, "pan": scan_pan, "tilt": scan_tilt, "direction": direction})

                scan_pan += pan_move_step * direction


            if direction == 1 and scan_pan >= max_pan:
                direction = -1
                scan_pan = max_pan
                scan_tilt += tilt_move_step
                if scan_tilt > max_tilt:
                    break
            elif direction == -1 and scan_pan <= min_pan:
                direction = 1
                scan_pan = min_pan
                scan_tilt += tilt_move_step
                if scan_tilt > max_tilt:
                    break
            if (abs(scan_tilt) > max_scan_tilt):
                logging.info("End of scan")
                self.eos.set_intensity(1, 0)
                self.eos.set_pan(1, 0, 0, "r1", use_degrees=True)
                self.eos.set_tilt(1, 0, 0, "r1", use_degrees=True)
                break


        # write the entire deque to a file
        with open("sensor_history.json", "w") as f:
            json.dump(self.sensor_history, f)
        # Calculate centroid of sensor datae
        return Phase.CALCULATE

    def calculate_phase(self):
        """
        Looks through the entire history of sensor data and calculates the
        pan/tilt values that correspond to the highest intensity for each sensor.
        """
        logging.info("Entering CALCULATE phase.")
        for sensor_id, history in self.sensor_history.items():
            max_intensity = -1
            best_pan = 0
            best_tilt = 0
            best_direction = 1
            for record in history:
                intensity = record["intensity"]
                pan = record["pan"]
                tilt = record["tilt"]
                if intensity > max_intensity:
                    max_intensity = intensity
                    best_pan = pan
                    best_tilt = tilt
                    best_direction = record["direction"]
            logging.info(f"Sensor {sensor_id} max intensity: {max_intensity} at pan: {best_pan}, tilt: {best_tilt}")
            corrected_pan = self.predict_corrected_pan_nonlinear(best_pan, best_tilt, best_direction)
            self.eos.set_sensor_data(sensor_id, corrected_pan, best_tilt, best_direction)

        logging.info("Calculated best pan/tilt for each sensor.")

        for sensor_id in self.sensor_history:
            logging.info(f"Sensor {sensor_id}: {self.eos.get_sensor_data(sensor_id)}")

        with open("sensor_history.json", "w") as f:
            json.dump(self.sensor_history, f, indent=4)


        return Phase.COMPLETE

    def is_close_to_baseline(self):
        """
        Checks if all sensor intensities are close to their baseline values.
        Returns True if all sensors are within the baseline threshold, else False.
        """
        current_data = self.get_new_data()
        for sensor_id, data in self.sensor_baselines.items():
            current_intensity = current_data.get(sensor_id, {}).get("intensity", 0)
            baseline_intensity = data.get("intensity", 0)
            if abs(current_intensity - baseline_intensity) > self.baseline_threshold:
                logging.debug(f"Sensor {sensor_id} intensity {current_intensity} is not close to baseline {baseline_intensity}.")
                return False
        logging.debug("All sensor intensities are close to their baselines.")
        return True


    def get_new_data(self):
        with self.lock:
            new_data = self.sensor_data.copy()

        return new_data

    def execute(self):
        """
        Executes the current phase and transitions to the next phase.
        Returns the current status of the navigator.
        """
        logging.debug(f"Executing phase: {self.current_phase}")
        if self.current_phase == Phase.SETUP:
            self.current_phase = self.setup_phase()
        elif self.current_phase == Phase.LOCATE:
            self.current_phase = self.locate_phase()
        elif self.current_phase == Phase.CALCULATE:
            self.current_phase = self.calculate_phase()

        status = {
            "current_phase": self.current_phase.name,
            "pan": self.pan,
            "tilt": self.tilt,
        }
        logging.info(f"Current Status: {status}")
        return status

    def distance(self, pos1, pos2):
        """
        Calculates Euclidean distance between two positions.
        """
        return np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

    def predict_corrected_pan_nonlinear(self, actual_pan, tilt, direction):
        """
        Predict the corrected pan value using the refined nonlinear model.

        Parameters:
        - actual_pan (float): The actual pan value.
        - tilt (float): The tilt value.
        - direction (int): The direction of motion (1 for forward, -1 for backward).

        Returns:
        - float: The predicted corrected pan value.
        """
        k1 = 1.5728
        k2 = -0.0187
        k3 = 0.0000630

        # Compute the predicted corrected pan
        overshoot_adjustment = (k1 * tilt + k2 * tilt**2 + k3 * tilt * actual_pan) * direction
        corrected_pan = actual_pan - overshoot_adjustment
        return corrected_pan
