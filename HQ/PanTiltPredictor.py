import numpy as np
from scipy.optimize import minimize

class PanTiltPredictor:
    def __init__(self, four_points):
        """
        Initialize the predictor with four reference points.

        Parameters:
        - four_points: List of four tuples, each containing:
            (x_i, y_i, pan_i, tilt_i)
            where:
                x_i, y_i: Coordinates of the point on stage in feet (float)
                pan_i: Pan angle in degrees (-270 to 270)
                tilt_i: Tilt angle in degrees (0-90)
        """
        if len(four_points) != 4:
            raise ValueError("Exactly four reference points are required.")

        # Map all pan_i to 0-360 for internal consistency
        self.four_points = [
            (x, y, self._map_to_0_360(pan_i), tilt_i)
            for (x, y, pan_i, tilt_i) in four_points
        ]
        self.light_position = self._find_light_position()

    @staticmethod
    def _map_to_0_360(angle):
        """Map angle from -270 to 270 to 0-360."""
        return angle + 360 if angle < 0 else angle

    @staticmethod
    def _map_to_negative_270_270(angle):
        """Map angle from 0-360 back to -270 to 270."""
        return angle - 360 if angle > 270 else angle

    @staticmethod
    def _compute_pan_tilt(Lx, Ly, h, x, y):
        """
        Compute pan and tilt angles from light position to a target point.

        Parameters:
        - Lx, Ly, h: Coordinates of the light.
        - x, y: Coordinates of the target point.

        Returns:
        - pan: Pan angle in degrees (0-360).
        - tilt: Tilt angle in degrees (0-90).
        """
        dx = x - Lx
        dy = y - Ly
        distance = np.sqrt(dx**2 + dy**2)

        # Compute pan using arctan2, result in degrees [0, 360)
        pan = np.degrees(np.arctan2(dy, dx)) % 360

        # Compute tilt using arctan (distance / height), result in degrees [0, 90]
        tilt = np.degrees(np.arctan(distance / h))

        return pan, tilt

    def _find_light_position(self):
        """
        Determine the light's position (Lx, Ly, h) using the four reference points.

        Returns:
        - Tuple containing (Lx, Ly, h) in feet.
        """
        def error_function(params):
            Lx, Ly, h = params
            total_error = 0
            for (x, y, pan_obs, tilt_obs) in self.four_points:
                pan_calc, tilt_calc = self._compute_pan_tilt(Lx, Ly, h, x, y)
                # Convert pan angles to radians for vector representation
                pan_obs_rad = np.radians(pan_obs)
                pan_calc_rad = np.radians(pan_calc)
                # Compute vector components
                cos_obs = np.cos(pan_obs_rad)
                sin_obs = np.sin(pan_obs_rad)
                cos_calc = np.cos(pan_calc_rad)
                sin_calc = np.sin(pan_calc_rad)
                # Compute pan error as squared Euclidean distance between vectors
                pan_error = (cos_calc - cos_obs)**2 + (sin_calc - sin_obs)**2
                # Compute tilt error
                tilt_error = (tilt_calc - tilt_obs)**2
                # Accumulate total error
                total_error += pan_error + tilt_error
            return total_error

        # Initial guess: center of the stage and an arbitrary height
        x_coords = [p[0] for p in self.four_points]
        y_coords = [p[1] for p in self.four_points]
        initial_Lx = (max(x_coords) + min(x_coords)) / 2
        initial_Ly = (max(y_coords) + min(y_coords)) / 2
        initial_h = 10.0  # Initial guess for height in feet

        initial_guess = [initial_Lx, initial_Ly, initial_h]

        # Define bounds to ensure meaningful optimization
        # Assuming the light is above the stage, set reasonable bounds
        stage_min_x = min(x_coords) - 10
        stage_max_x = max(x_coords) + 10
        stage_min_y = min(y_coords) - 10
        stage_max_y = max(y_coords) + 10
        h_min = 1.0   # Minimum height
        h_max = 100.0 # Maximum height

        bounds = [
            (stage_min_x, stage_max_x),  # Lx bounds
            (stage_min_y, stage_max_y),  # Ly bounds
            (h_min, h_max)               # h bounds
        ]

        # Perform optimization to minimize the error function
        result = minimize(
            error_function,
            initial_guess,
            method='L-BFGS-B',
            bounds=bounds,
            options={'ftol': 1e-12, 'maxiter': 10000}
        )

        if result.success:
            Lx, Ly, h = result.x
            if h <= 0:
                raise ValueError("Computed height is non-positive. Please check the input data.")
            return Lx, Ly, h
        else:
            raise RuntimeError("Optimization failed to determine the light position.")

    def predict_pan_tilt(self, x, y, return_original_format=True):
        """
        Predict the pan and tilt angles for a given (x, y) point.

        Parameters:
        - x, y: Coordinates of the target point in feet.
        - return_original_format: If True, outputs pan in -270 to 270 format.

        Returns:
        - Tuple containing:
            (pan in degrees, tilt in degrees [0-90])
        """
        Lx, Ly, h = self.light_position
        pan, tilt = self._compute_pan_tilt(Lx, Ly, h, x, y)

        if return_original_format:
            pan = self._map_to_negative_270_270(pan)

        return pan, tilt

    def get_light_position(self):
        """
        Get the determined position of the light.

        Returns:
        - Tuple containing (Lx, Ly, h) in feet.
        """
        return self.light_position
