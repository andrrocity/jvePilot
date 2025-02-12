from cereal import car
from opendbc.can.parser import CANParser
from opendbc.can.can_define import CANDefine
from selfdrive.config import Conversions as CV
from selfdrive.car.interfaces import CarStateBase
from selfdrive.car.chrysler.values import DBC, STEER_THRESHOLD
from common.op_params import opParams

ButtonType = car.CarState.ButtonEvent.Type

class CarState(CarStateBase):
  def __init__(self, CP):
    super().__init__(CP)
    self.op_params = opParams()
    can_define = CANDefine(DBC[CP.carFingerprint]['pt'])
    self.shifter_values = can_define.dv["GEAR"]['PRNDL']
    self.prevResumeCruiseButton = False
    self.prevAccelCruiseButton = False
    self.prevDecelCruiseButton = False
    self.accCancelButton = False
    self.accFollowDecButton = False
    self.accFollowIncButton = False

  def update(self, cp, cp_cam):

    ret = car.CarState.new_message()

    self.frame = int(cp.vl["EPS_STATUS"]['COUNTER'])

    ret.doorOpen = any([cp.vl["DOORS"]['DOOR_OPEN_FL'],
                        cp.vl["DOORS"]['DOOR_OPEN_FR'],
                        cp.vl["DOORS"]['DOOR_OPEN_RL'],
                        cp.vl["DOORS"]['DOOR_OPEN_RR']])
    ret.seatbeltUnlatched = cp.vl["SEATBELT_STATUS"]['SEATBELT_DRIVER'] == 1 or cp.vl["SEATBELT_STATUS"]['SEATBELT_DRIVER'] == 2 # 1 or 2 means unbuckled. 

    ret.brakePressed = cp.vl["BRAKE_2"]['BRAKE_PRESSED_2'] == 5  # human-only
    ret.brake = 0
    ret.brakeLights = ret.brakePressed
    ret.gas = cp.vl["ACCEL_GAS_134"]['ACCEL_134']
    ret.gasPressed = ret.gas > 1e-5

    ret.espDisabled = (cp.vl["TRACTION_BUTTON"]['TRACTION_OFF'] == 1)

    ret.wheelSpeeds.fl = cp.vl['WHEEL_SPEEDS']['WHEEL_SPEED_FL']
    ret.wheelSpeeds.rr = cp.vl['WHEEL_SPEEDS']['WHEEL_SPEED_RR']
    ret.wheelSpeeds.rl = cp.vl['WHEEL_SPEEDS']['WHEEL_SPEED_RL']
    ret.wheelSpeeds.fr = cp.vl['WHEEL_SPEEDS']['WHEEL_SPEED_FR']
    ret.vEgoRaw = (cp.vl['SPEED_1']['SPEED_LEFT'] + cp.vl['SPEED_1']['SPEED_RIGHT']) / 2.
    ret.vEgo, ret.aEgo = self.update_speed_kf(ret.vEgoRaw)
    ret.standstill = not ret.vEgoRaw > 0.001

    ret.leftBlinker = cp.vl["STEERING_LEVERS"]['TURN_SIGNALS'] == 1
    ret.rightBlinker = cp.vl["STEERING_LEVERS"]['TURN_SIGNALS'] == 2
    ret.steeringAngleDeg = cp.vl["STEERING"]['STEER_ANGLE'] + cp.vl["STEERING"]['STEER_ANGLE_HIGH_PRECISION']
    ret.steeringRateDeg = cp.vl["STEERING"]['STEERING_RATE']
    ret.gearShifter = self.parse_gear_shifter(self.shifter_values.get(cp.vl['GEAR']['PRNDL'], None))

    ret.cruiseState.enabled = cp.vl["ACC_2"]['ACC_STATUS_2'] == 7  # ACC is green.
    ret.cruiseState.available = ret.cruiseState.enabled  # FIXME: for now same as enabled
    ret.cruiseState.speed = cp.vl["DASHBOARD"]['ACC_SPEED_CONFIG_KPH'] * CV.KPH_TO_MS
    # CRUISE_STATE is a three bit msg, 0 is off, 1 and 2 are Non-ACC mode, 3 and 4 are ACC mode, find if there are other states too
    #ret.cruiseState.nonAdaptive = cp.vl["DASHBOARD"]['CRUISE_STATE'] in [1, 2]

    ret.steeringTorque = cp.vl["EPS_STATUS"]["TORQUE_DRIVER"]
    ret.steeringTorqueEps = cp.vl["EPS_STATUS"]["TORQUE_MOTOR"]
    ret.steeringPressed = abs(ret.steeringTorque) > STEER_THRESHOLD
    steer_state = cp.vl["EPS_STATUS"]["LKAS_STATE"]
    ret.steerError = False #steer_state == 4 or steer_state == 0 #and ret.vEgo > self.CP.minSteerSpeed)

    ret.genericToggle = bool(cp.vl["STEERING_LEVERS"]['HIGH_BEAM_FLASH'])

    accConfig = cp.vl["DASHBOARD"]['ACC_DISTANCE_CONFIG_2']
    if accConfig == 0:
      ret.leadDistanceRadarRatio = self.op_params.get('lead_distance_ratio_1bar')
    elif accConfig == 1:
      ret.leadDistanceRadarRatio = self.op_params.get('lead_distance_ratio_2bars')
    elif accConfig == 2:
      ret.leadDistanceRadarRatio = self.op_params.get('lead_distance_ratio_3bars')
    else:
      ret.leadDistanceRadarRatio = self.op_params.get('lead_distance_ratio_4bars')

    self.lkas_counter = cp_cam.vl["LKAS_COMMAND"]['COUNTER']
    self.lkas_car_model = cp_cam.vl["LKAS_HUD"]['CAR_MODEL']
    self.lkas_status_ok = cp_cam.vl["LKAS_HEARTBIT"]['LKAS_STATUS_OK']

    # Track buttons
    self.buttonCounter = int(cp.vl["WHEEL_BUTTONS"]['COUNTER'])

    self.resumeCruiseButton = bool(cp.vl["WHEEL_BUTTONS"]['ACC_RESUME'])
    self.resumeCruiseButtonChanged = (self.prevResumeCruiseButton != self.resumeCruiseButton)
    self.prevResumeCruiseButton = self.resumeCruiseButton

    self.accelCruiseButton = bool(cp.vl["WHEEL_BUTTONS"]['ACC_SPEED_INC'])
    self.accelCruiseButtonChanged = (self.prevAccelCruiseButton != self.accelCruiseButton)
    self.prevAccelCruiseButton = self.accelCruiseButton

    self.decelCruiseButton = bool(cp.vl["WHEEL_BUTTONS"]['ACC_SPEED_DEC'])
    self.decelCruiseButtonChanged = (self.prevDecelCruiseButton != self.decelCruiseButton)
    self.prevDecelCruiseButton = self.decelCruiseButton

    self.accCancelButton = bool(cp.vl["WHEEL_BUTTONS"]['ACC_CANCEL'])
    self.accFollowDecButton = bool(cp.vl["WHEEL_BUTTONS"]['ACC_FOLLOW_DEC'])
    self.accFollowIncButton = bool(cp.vl["WHEEL_BUTTONS"]['ACC_FOLLOW_INC'])

    return ret

  @staticmethod
  def get_can_parser(CP):
    signals = [
      # sig_name, sig_address, default
      ("PRNDL", "GEAR", 0),
      ("DOOR_OPEN_FL", "DOORS", 0),
      ("DOOR_OPEN_FR", "DOORS", 0),
      ("DOOR_OPEN_RL", "DOORS", 0),
      ("DOOR_OPEN_RR", "DOORS", 0),
      ("BRAKE_PRESSED_2", "BRAKE_2", 0),
      ("ACCEL_134", "ACCEL_GAS_134", 0),
      ("SPEED_LEFT", "SPEED_1", 0),
      ("SPEED_RIGHT", "SPEED_1", 0),
      ("WHEEL_SPEED_FL", "WHEEL_SPEEDS", 0),
      ("WHEEL_SPEED_RR", "WHEEL_SPEEDS", 0),
      ("WHEEL_SPEED_RL", "WHEEL_SPEEDS", 0),
      ("WHEEL_SPEED_FR", "WHEEL_SPEEDS", 0),
      ("STEER_ANGLE", "STEERING", 0),
      ("STEER_ANGLE_HIGH_PRECISION", "STEERING", 0),
      ("STEERING_RATE", "STEERING", 0),
      ("TURN_SIGNALS", "STEERING_LEVERS", 0),
      ("ACC_STATUS_2", "ACC_2", 0),
      ("HIGH_BEAM_FLASH", "STEERING_LEVERS", 0),
      ("ACC_SPEED_CONFIG_KPH", "DASHBOARD", 0),
      ("CRUISE_STATE", "DASHBOARD", 0),
      ("TORQUE_DRIVER", "EPS_STATUS", 0),
      ("TORQUE_MOTOR", "EPS_STATUS", 0),
      ("LKAS_STATE", "EPS_STATUS", 1),
      ("COUNTER", "EPS_STATUS", -1),
      ("TRACTION_OFF", "TRACTION_BUTTON", 0),
      ("SEATBELT_DRIVER", "SEATBELT_STATUS", 0),
      ("COUNTER", "WHEEL_BUTTONS", -1),
      ("ACC_RESUME", "WHEEL_BUTTONS", 0),
      ("ACC_CANCEL", "WHEEL_BUTTONS", 0),
      ("ACC_SPEED_INC", "WHEEL_BUTTONS", 0),
      ("ACC_SPEED_DEC", "WHEEL_BUTTONS", 0),
      ("ACC_FOLLOW_INC", "WHEEL_BUTTONS", 0),
      ("ACC_FOLLOW_DEC", "WHEEL_BUTTONS", 0),
      ("ACC_DISTANCE_CONFIG_2", "DASHBOARD", 0),
    ]

    checks = [
      # sig_address, frequency
      ("BRAKE_2", 50),
      ("EPS_STATUS", 100),
      ("SPEED_1", 100),
      ("WHEEL_SPEEDS", 50),
      ("STEERING", 100),
      ("ACC_2", 50),
      ("GEAR", 50),
      ("WHEEL_BUTTONS", 50),
      ("ACCEL_GAS_134", 50),
      ("DASHBOARD", 15),
      ("STEERING_LEVERS", 10),
      ("SEATBELT_STATUS", 2),
      ("DOORS", 1),
      ("TRACTION_BUTTON", 1),
    ]

    return CANParser(DBC[CP.carFingerprint]['pt'], signals, checks, 0)

  @staticmethod
  def get_cam_can_parser(CP):
    signals = [
      # sig_name, sig_address, default
      ("COUNTER", "LKAS_COMMAND", -1),
      ("CAR_MODEL", "LKAS_HUD", -1),
      ("LKAS_STATUS_OK", "LKAS_HEARTBIT", -1)
    ]
    checks = [
      ("LKAS_COMMAND", 100),
      ("LKAS_HEARTBIT", 10),
      ("LKAS_HUD", 4),
    ]

    return CANParser(DBC[CP.carFingerprint]['pt'], signals, checks, 2)
