from enum import Enum
import numpy as np
from EOS import EOS
from gevent import sleep
import logging


class Phase(Enum):
    SETUP = "setup"
    EXPLORE = "explore"
    OPTIMIZE = "optimize"
    COMPLETE = "complete"
    FAILED = "failed"

class Navigator:
    def __init__(self, eos_ip="192.168.1.105", eos_port=8000, gui=None, sensor_data=None, lock=None):
        self.gui = gui
        self.eos = EOS(eos_ip, eos_port)
        self.current_phase = Phase.SETUP
        self.pan = 0.0
        self.tilt = 0.0
        self.best_intensity = -1
        self.target_sensor = 1
        self.target_sensor_previous_intensity = -1
        self.sensor_baselines = {}
        self.sensor_data = sensor_data
        self.lock = lock

    def send_light_command(self, pan_move, tilt_move, use_degrees=True):
        # Send pan/tilt updates to EOS
        self.eos.set_pan(1, self.pan, pan_move, "r1", use_degrees)
        self.eos.set_tilt(1, self.tilt, tilt_move, "r1", use_degrees)
        self.pan += pan_move
        self.tilt += tilt_move
        logging.debug(f"Sent pan_move: {pan_move}, tilt_move: {tilt_move}. New pan: {self.pan}, New tilt: {self.tilt}")

    def setup_phase(self):
        logging.info("Entering SETUP phase.")
        self.eos.set_pan(1, 0, 0, "r1", use_degrees=True)
        self.eos.set_tilt(1, 0, 0, "r1", use_degrees=True)
        self.eos.set_intensity(1, 100)
        sleep(5)  # Reduced sleep for quicker updates
        # set baselines
        self.sensor_baselines = self.get_new_data()
        logging.info(f"Sensor baselines: {self.sensor_baselines}")

        self.best_intensity = self.get_new_data().get(self.target_sensor, {}).get("intensity", 0)
        logging.debug(f"Setup complete. Baseline intensity: {self.best_intensity}")

        return Phase.EXPLORE

    def explore_phase(self):
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
                if intensity > self.sensor_baselines.get(self.target_sensor, {}).get("intensity", 0) + 10000000:
                    return Phase.OPTIMIZE

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



    def calculate_weighted_centroid(self):
        sensor_data = self.get_new_data()

        # for debugging
        for sensor_id, sensor in sensor_data.items():
            logging.debug(f"Sensor {sensor_id}: {sensor}")

        total_intensity = sum(sensor["intensity"] for sensor in sensor_data.values())
        if total_intensity == 0:
            logging.warning("Total intensity is 0. Cannot calculate weighted centroid.")
            return None

        centroid_x = sum(sensor["intensity"] * sensor["x"] for sensor in sensor_data.values()) / sum(sensor["intensity"] for sensor in sensor_data.values())
        centroid_y = sum(sensor["intensity"] * sensor["y"] for sensor in sensor_data.values()) / sum(sensor["intensity"] for sensor in sensor_data.values())

        logging.info(f"Calculated weighted centroid: ({centroid_x}, {centroid_y})")

        return (centroid_x, centroid_y)

    def map_gui_to_angles(self, centroid):
        gui_width, gui_height = self.gui.get_gui_dimensions()
        pan_min, pan_max = self.eos.get_pan_range("r1")
        tilt_min, tilt_max = self.eos.get_tilt_range("r1")

        centroid_x, centroid_y = centroid

        # clamp centroid to GUI dimensions
        centroid_x= max(0, min(gui_width, centroid_x))
        centroid_y = max(0, min(gui_height, centroid_y))

        # normalise coordinates (0 to 1)
        norm_x = centroid_x / gui_width
        norm_y = centroid_y / gui_height

        #map normalised coordinates to pan and tilt values

        # TODO: determine of the eos map value to range works like the code below it.
        # pan = self.eos.map_value_to_range(norm_x, pan_min, pan_max)
        # tilt = self.eos.map_value_to_range(norm_y, tilt_min, tilt_max)

        pan = norm_x * (pan_max - pan_min) + pan_min
        tilt = (1 - norm_y) * (tilt_max - tilt_min) + tilt_min

        logging.debug(f"Mapped centroid to pan: {pan}, tilt: {tilt}")
        return pan, tilt



    def optimize_phase(self):
        logging.info("Entering OPTIMIZE phase.")
        max_iterations = 100
        iteration = 0
        tolerance = 0.1

        while iteration < max_iterations:
            iteration += 1
            sensor_data = self.get_new_data()
            self.sensor_data = sensor_data

            logging.debug(f"Iteration {iteration}. Sensor data: {sensor_data}")

            centroid = self.calculate_weighted_centroid()
            logging.info(f"Calculated centroid: {centroid}")

            if centroid is None:
                logging.warning("Failed to calculate centroid. Exiting OPTIMIZE phase.")
                return Phase.FAILED

            target_pan, target_tilt = self.map_gui_to_angles(centroid)

            pan_move = target_pan - self.pan
            tilt_move = target_tilt - self.tilt

            logging.debug(f"Pan move: {pan_move}, tilt move: {tilt_move}")

            if abs(pan_move) < tolerance and abs(tilt_move) < tolerance:
                logging.info("Optimization converged wtihin tolerance.")
                break

            self.send_light_command(pan_move, tilt_move, use_degrees=True)

            # wait for sensors to update and light to move
            sleep(1)

            updated_sensor_data = self.get_new_data()
            current_intensity = updated_sensor_data.get(self.target_sensor, {}).get("intensity", 0)
            logging.debug(f"Iteration {iteration}: Pan: {self.pan}, Tilt: {self.tilt}, Intensity: {current_intensity}")

            # Has intensity of target sensor improved?
            if current_intensity > self.best_intensity:
                self.best_intensity = current_intensity
                self.target_sensor_previous_intensity = current_intensity
                logging.info(f"New best intensity: {self.best_intensity}")
            else:
                logging.info(f"Intensity did not improve. Stopping optimization.")
                # undo the last move
                self.send_light_command(-pan_move, -tilt_move, use_degrees=True)
                break

        final_intensity = updated_sensor_data.get(self.target_sensor, {}).get("intensity", 0)
        logging.info(f"Optimization complete after {iteration} iterations. Final intensity: {final_intensity}")

        if final_intensity >= self.best_intensity:
            logging.info("Optimization successful.")
            return Phase.COMPLETE
        else:
            logging.warning("Optimization failed.")
            return Phase.FAILED


    def get_new_data(self):
        new_sensor_data = {}

        with self.lock:
            raw_sensor_data = self.sensor_data.copy()  # sensor_id: intensity or sensor_id: dict

        logging.debug(f"Raw sensor data: {raw_sensor_data}")

        if self.gui is not None:
            sensor_positions = self.gui.get_sensor_positions()  # sensor_id: (x, y)
            for sensor_id, data in raw_sensor_data.items():
                if sensor_id in sensor_positions:
                    # Determine if 'data' is a dict or a numerical value
                    if isinstance(data, dict):
                        intensity = data.get("intensity", 0)
                    else:
                        intensity = data  # Assuming 'data' is intensity

                    new_sensor_data[sensor_id] = {
                        "intensity": intensity,
                        "x": sensor_positions[sensor_id][0],
                        "y": sensor_positions[sensor_id][1],
                    }
                    logging.debug(f"Sensor {sensor_id} Position: ({sensor_positions[sensor_id][0]}, {sensor_positions[sensor_id][1]}), Intensity: {intensity}")
                else:
                    logging.warning(f"Sensor ID {sensor_id} not found in GUI positions.")
        else:
            logging.warning("GUI is not defined. Cannot map sensor positions.")

        logging.debug(f"Retrieved new sensor data: {new_sensor_data}")
        return new_sensor_data

    def execute(self):
        logging.debug(f"Executing phase: {self.current_phase}")
        if self.current_phase == Phase.SETUP:
            self.current_phase = self.setup_phase()
        elif self.current_phase == Phase.EXPLORE:
            self.current_phase = self.explore_phase()
        elif self.current_phase == Phase.OPTIMIZE:
            self.current_phase = self.optimize_phase()

        return {
            "current_phase": self.current_phase.name,
            "pan": self.pan,
            "tilt": self.tilt,
            "target_sensor": self.target_sensor,
        }
