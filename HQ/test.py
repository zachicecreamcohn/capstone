from PanTiltPredictor import PanTiltPredictor
from EOS import EOS

def feet_inches_to_feet(feet, inches):
    return feet + inches/12

# reference_point1 = (pos_x, pos_y, pan, tilt)
def predict(target_x, target_y, reference_point1: tuple, reference_point2: tuple, reference_point3: tuple, reference_point4: tuple):
    predictor = PanTiltPredictor([reference_point1, reference_point2, reference_point3, reference_point4])

    pan, tilt = predictor.predict_pan_tilt(target_x, invert_y(target_y, 12))
    return pan, tilt

def invert_y(y, max_y):
    return max_y - y

def main():
    # {"1": {"pan": 148, "tilt": 50, "direction": 1}, "2": {"pan": 54, "tilt": 39, "direction": 1}, "3": {"pan": -149, "tilt": 46, "direction": 1}, "4": {"pan": -32, "tilt": 35, "direction": 1}}

    eos=EOS("192.168.1.100", 8000)

    reference_point1 = (feet_inches_to_feet(0, 0), feet_inches_to_feet(0, 0), 148.0, 50)
    reference_point2 = (feet_inches_to_feet(16, 0), feet_inches_to_feet(0, 0), 54.0, 39)
    reference_point3 = (feet_inches_to_feet(0, 0), feet_inches_to_feet(12, 0), -149.0, 46)
    reference_point4 = (feet_inches_to_feet(16, 0), feet_inches_to_feet(12, 0), -32.0, 35)

    target_x = feet_inches_to_feet(8, 0)
    target_y = feet_inches_to_feet(6, 0)

    pan, tilt = predict(target_x, target_y, reference_point1, reference_point2, reference_point3, reference_point4)
    eos.set_pan(1, 0, pan, "r1", use_degrees=True)
    eos.set_tilt(1, 0, tilt, "r1", use_degrees=True)
    print(f"Pan: {pan}, Tilt: {tilt}")

if __name__ == "__main__":
    main()
