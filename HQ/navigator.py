from enum import Enum
import numpy as np
from EOS import EOS  # Ensure EOS module is correctly imported
from gevent import sleep
import logging
from collections import deque
from threading import Lock

# Configure logging at the beginning of your main script
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class Phase(Enum):
    SETUP = "setup"
    LOCATE = "locate"
    OPTIMIZE = "optimize"
    COMPLETE = "complete"
    FAILED = "failed"

class Navigator:
    def __init__(self, eos_ip="192.168.1.105", eos_port=8000, gui=None, sensor_data=None, lock=None):
        self.gui = gui
        self.eos = EOS(eos_ip, eos_port)
        self.current_phase = Phase.SETUP
        self.pan = 0.0  # Current pan angle
        self.tilt = 0.0  # Current tilt angle
        self.best_intensity = -1
        self.target_sensor = 1  # ID of the target sensor
        self.sensor_baselines = {}
        self.sensor_data = sensor_data if sensor_data is not None else {}
        self.lock = lock if lock is not None else Lock()

        # parameters for locate phase
        self.target_sensor_previous_intensity = -1


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
            self.sensor_history = {sensor_id: deque(maxlen=self.history_length) for sensor_id in sensor_ids}
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
        initial_pan, initial_tilt = -80, 0
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
        self.best_intensity = self.sensor_baselines.get(self.target_sensor, {}).get("intensity", 0)
        self.eos.set_intensity(1, 100)
        logging.debug(f"Setup complete. Baseline intensity: {self.best_intensity}")

        return Phase.LOCATE

    def locate_phase(self):
        # move in expanding concentric circles until the taret sensor picks up significant changes
        logging.info("Entering EXPLORE phase.")

        # Move the light in a spiral pattern
        max_tilt = self.eos.get_tilt_range("r1")[1]
        min_pan, max_pan = self.eos.get_pan_range("r1")
        pan_move_step = 5
        tilt_move_step = 10



        if self.target_sensor_previous_intensity == -1:
            self.target_sensor_previous_intensity = self.get_new_data().get(self.target_sensor, {}).get("intensity", 0)

        self.send_light_command(min_pan, 0, use_degrees=True)


        scan_pan = min_pan
        scan_tilt = 0
        direction = 1
        give_up_tilt = 85
        found = False
        while not found:
            # set tilt
            for i in range(0, max_pan, pan_move_step):
                self.eos.set_pan(1,0,scan_pan, "r1", use_degrees=True)
                self.eos.set_tilt(1,0,scan_tilt, "r1", use_degrees=True)
                self.pan = scan_pan
                self.tilt = scan_tilt
                sleep(0.2)
                intensity = self.get_new_data().get(self.target_sensor, {}).get("intensity", 0)
                if intensity > self.sensor_baselines.get(self.target_sensor, {}).get("intensity", 0) + 1000000:
                    return Phase.OPTIMIZE
                else:
                    logging.info(f"Intensity: {intensity}, Baseline: {self.sensor_baselines.get(self.target_sensor, {}).get('intensity', 0)}")

                self.target_sensor_previous_intensity = intensity
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
            if (abs(scan_tilt) > give_up_tilt):
                logging.info("Giving up")
                self.eos.set_intensity(1, 0)
                self.eos.set_pan(1, 0, 0, "r1", use_degrees=True)
                self.eos.set_tilt(1, 0, 0, "r1", use_degrees=True)
                return Phase.FAILED

        return Phase.OPTIMIZE

    def optimize_phase(self):
        """
        Implements the centroid-based algorithm to focus the light on the target sensor.
        Utilizes all sensors' data to compute the centroid and adjusts pan and tilt accordingly.
        """
        logging.info("Entering LOCATE phase.")
        steps = 0
        max_baseline_checks = 100  # Define how many consecutive baseline checks to allow
        baseline_checks = 0

        while steps < self.max_steps:
            # Check if sensor data is close to baseline
            if self.is_close_to_baseline():
                logging.warning(f"Step {steps}: Sensor intensities are close to baseline. Skipping adjustments.")
                baseline_checks += 1
                if baseline_checks >= max_baseline_checks:
                    logging.error("Sensor data has been close to baseline for too many consecutive steps. Failing locate phase.")
                    return Phase.FAILED
                sleep(1)
                steps += 1
                continue
            else:
                baseline_checks = 0  # Reset counter if not close to baseline

            current_centroid = self.compute_centroid()
            target_pos = self.gui.get_sensor_positions()[self.target_sensor]
            distance_to_target = self.distance(current_centroid, target_pos)
            logging.debug(f"Step {steps}: Current Centroid: {current_centroid}, Distance to Target: {distance_to_target:.2f}")

            # Check if within tolerance
            if distance_to_target <= self.tolerance:
                logging.info(f"Centroid is within tolerance ({self.tolerance}).")
                return Phase.COMPLETE

            # Calculate direction vector towards target
            direction_vector = np.array(target_pos) - np.array(current_centroid)
            distance = np.linalg.norm(direction_vector)
            if distance == 0:
                logging.debug("Centroid is exactly at the target position.")
                return Phase.COMPLETE
            direction_unit_vector = direction_vector / distance

            # Determine movement based on direction
            pan_move = direction_unit_vector[0] * self.step_size
            tilt_move = direction_unit_vector[1] * self.step_size

            # Apply movement
            self.send_light_command(pan_move, tilt_move)
            sleep(0.5)  # Wait for system to stabilize

            # Recompute centroid after movement
            new_centroid = self.compute_centroid()
            new_distance_to_target = self.distance(new_centroid, target_pos)
            logging.debug(f"After Move: New Centroid: {new_centroid}, New Distance to Target: {new_distance_to_target:.2f}")

            # Check if the move brought us closer
            if new_distance_to_target < distance_to_target - self.tolerance:
                logging.info(f"Moved towards target. New Distance: {new_distance_to_target:.2f}")
                self.best_intensity = self.get_weighted_intensity()
            else:
                # Revert move if no improvement
                self.send_light_command(-pan_move, -tilt_move)
                logging.debug("No improvement. Reverting move.")

            # Adjust step size dynamically for finer adjustments
            if steps > 0 and steps % 50 == 0 and self.step_size > self.min_step_size:
                self.step_size = max(self.min_step_size, self.step_size - self.step_decrement)
                logging.info(f"Reducing step_size to {self.step_size} degrees for finer adjustments.")

            steps += 1
            sleep(1)  # Wait for system to stabilize

        logging.warning("Reached maximum number of steps without completing locate phase.")
        return Phase.FAILED

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

    def compute_centroid(self):
        """
        Computes the intensity-weighted centroid of the light based on all sensors' data.
        """
        new_data = self.get_new_data()
        total_intensity = sum(data['intensity'] for data in new_data.values())
        if total_intensity == 0:
            logging.warning("Total intensity is zero. Centroid cannot be computed.")
            return (0, 0)

        centroid_x = sum(data['x'] * data['intensity'] for data in new_data.values()) / total_intensity
        centroid_y = sum(data['y'] * data['intensity'] for data in new_data.values()) / total_intensity
        centroid = (centroid_x, centroid_y)
        logging.debug(f"Computed Centroid: {centroid}")
        return centroid

    def get_weighted_intensity(self):
        """
        Calculates the weighted sum of intensities from all sensors.
        Weights are based on the inverse square of the distance to the target sensor.
        """
        new_data = self.get_new_data()
        weighted_intensity = 0.0
        for sensor_id, data in new_data.items():
            weight = self.calculate_weight(sensor_id)
            sensor_intensity = data.get("intensity", 0)
            contribution = sensor_intensity * weight
            weighted_intensity += contribution
            logging.debug(f"Sensor {sensor_id}: Intensity={sensor_intensity}, Weight={weight:.4f}, Weighted Contribution={contribution:.4f}")
        logging.debug(f"Total Weighted Intensity: {weighted_intensity:.4f}")
        return weighted_intensity

    def calculate_weight(self, sensor_id):
        """
        Calculates the weight for a sensor based on its distance to the target sensor.
        Uses inverse square of the distance to reduce the influence of far sensors.
        """
        try:
            target_pos = self.gui.get_sensor_positions()[self.target_sensor]
            sensor_pos = self.gui.get_sensor_positions()[sensor_id]
            distance = self.distance(sensor_pos, target_pos)
            if distance == 0:
                return 1.0  # Maximum weight if at the same position
            return 1.0 / (distance ** 2)  # Inverse square weighting
        except KeyError as e:
            logging.error(f"Sensor ID {sensor_id} not found in GUI positions: {e}")
            return 0.0  # No contribution if sensor position is unknown
        except Exception as e:
            logging.error(f"Error calculating weight for sensor {sensor_id}: {e}")
            return 0.0

    def get_new_data(self):
        """
        Retrieves and filters new sensor data.
        Applies a moving average filter to each sensor's intensity to reduce noise.
        """
        new_sensor_data = {}

        with self.lock:
            raw_sensor_data = self.sensor_data.copy()  # sensor_id: intensity or sensor_id: dict

        logging.debug(f"Raw sensor data: {raw_sensor_data}")

        if self.gui is not None:
            try:
                sensor_positions = self.gui.get_sensor_positions()  # sensor_id: (x, y)
            except Exception as e:
                logging.error(f"Failed to get sensor positions from GUI: {e}")
                return new_sensor_data

            for sensor_id, data in raw_sensor_data.items():
                if sensor_id in sensor_positions:
                    # Determine if 'data' is a dict or a numerical value
                    if isinstance(data, dict):
                        intensity = data.get("intensity", 0)
                    else:
                        intensity = data  # Assuming 'data' is intensity

                    # Update sensor history with new intensity
                    if sensor_id in self.sensor_history:
                        self.sensor_history[sensor_id].append(intensity)
                        # Calculate moving average
                        avg_intensity = np.mean(self.sensor_history[sensor_id])
                    else:
                        logging.warning(f"Sensor ID {sensor_id} has no history initialized.")
                        avg_intensity = intensity  # Use raw intensity if history not initialized

                    new_sensor_data[sensor_id] = {
                        "intensity": avg_intensity,
                        "x": sensor_positions[sensor_id][0],
                        "y": sensor_positions[sensor_id][1],
                    }
                    logging.debug(f"Sensor {sensor_id} Position: ({sensor_positions[sensor_id][0]}, {sensor_positions[sensor_id][1]}), Averaged Intensity: {avg_intensity:.2f}")
                else:
                    logging.warning(f"Sensor ID {sensor_id} not found in GUI positions.")
        else:
            logging.warning("GUI is not defined. Cannot map sensor positions.")

        logging.debug(f"Retrieved new sensor data: {new_sensor_data}")
        return new_sensor_data

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
        elif self.current_phase == Phase.OPTIMIZE:
            self.current_phase = self.optimize_phase()

        status = {
            "current_phase": self.current_phase.name,
            "pan": self.pan,
            "tilt": self.tilt,
            "target_sensor": self.target_sensor,
        }
        logging.info(f"Current Status: {status}")
        return status

    def distance(self, pos1, pos2):
        """
        Calculates Euclidean distance between two positions.
        """
        return np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
