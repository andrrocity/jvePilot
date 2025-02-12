#!/usr/bin/env python3
from cereal import car
from selfdrive.car.chrysler.values import CAR
from selfdrive.car import STD_CARGO_KG, scale_rot_inertia, scale_tire_stiffness, gen_empty_fingerprint
from selfdrive.car.interfaces import CarInterfaceBase

ButtonType = car.CarState.ButtonEvent.Type

class CarInterface(CarInterfaceBase):
  @staticmethod
  def compute_gb(accel, speed):
    return float(accel) / 3.0

  @staticmethod
  def get_params(candidate, fingerprint=None, car_fw=None):
    if fingerprint is None:
      fingerprint = gen_empty_fingerprint()

    ret = CarInterfaceBase.get_std_params(candidate, fingerprint)
    ret.carName = "chrysler"
    ret.safetyModel = car.CarParams.SafetyModel.chrysler

    # Chrysler port is a community feature, since we don't own one to test
    ret.communityFeature = True

    # Speed conversion:              20, 45 mph
    ret.wheelbase = 3.089  # in meters for Pacifica Hybrid 2017
    ret.steerRatio = 16.2  # Pacifica Hybrid 2017
    ret.mass = 1964. + STD_CARGO_KG  # kg curb weight Pacifica Hybrid 2017
    
    
    ### INDI TUNE ###

    # innerLoopGain is curvature gain.
    # outerLoopGain is lane centering gain.
    # timeConstant is smoothness.
    # actuatorEffectiveness is gain modulation based on accuracy of path.
    # steerActuatorDelay is how far its looking ahead.
    # steerRateCost is how eager the steering is to make sudden changes.

    ret.lateralTuning.init('indi')
    ret.lateralTuning.indi.innerLoopGainBP = [0, 20, 40]
    ret.lateralTuning.indi.innerLoopGainV = [1.5, 2.5, 2.5]
    ret.lateralTuning.indi.outerLoopGainBP = [0, 20, 40]
    ret.lateralTuning.indi.outerLoopGainV = [2.5, 3.5, 4.0]
    ret.lateralTuning.indi.timeConstantBP = [0, 20, 40]
    ret.lateralTuning.indi.timeConstantV = [0.5, 0.8, 0.8]
    ret.lateralTuning.indi.actuatorEffectivenessBP = [0, 10, 20]
    ret.lateralTuning.indi.actuatorEffectivenessV = [2.0, 3.5, 4.0]
    ret.steerActuatorDelay = 0.15
    ret.steerRateCost = 0.45
    ret.steerLimitTimer = 0.4
    
    
    ### TF PID TUNE ###

    #ret.lateralTuning.pid.kpBP, ret.lateralTuning.pid.kiBP = [[0., 9., 20.], [0., 9., 20.]]
    #ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.0125, 0.0375, 0.075], [0.0025, 0.0075, 0.0255]]
    #ret.lateralTuning.pid.kf = 0.00000000000000000000006   # full torque for 10 deg at 80mph means 0.00007818594
    #ret.steerActuatorDelay = 0.1
    #ret.steerRateCost = 0.4
    #ret.steerLimitTimer = 0.4
    
    ### STOCK TUNE ###

    #ret.lateralTuning.pid.kpBP, ret.lateralTuning.pid.kiBP = [[9., 20.], [9., 20.]]
    #ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.15, 0.30], [0.03, 0.05]]
    #ret.lateralTuning.pid.kf = 0.00006   # full torque for 10 deg at 80mph means 0.00007818594
    #ret.steerActuatorDelay = 0.1
    #ret.steerRateCost = 0.7
    #ret.steerLimitTimer = 0.4

    if candidate in (CAR.JEEP_CHEROKEE, CAR.JEEP_CHEROKEE_2019):
      ret.wheelbase = 2.91  # in meters
      ret.steerRatio = 12.7
      ret.steerActuatorDelay = 0.2  # in seconds

    if candidate in (CAR.CHRYSLER_300_2018):
        ret.wheelbase = 3.05308 # in meters
        ret.steerRatio = 15.5 # 2013 V-6 (RWD) — 15.5:1 V-6 (AWD) — 16.5:1 V-8 (RWD) — 15.5:1 V-8 (AWD) — 16.5:1
        ret.mass = 1828.0 + STD_CARGO_KG # 2013 V-6 RWD
        ret.steerActuatorDelay =  0.38

        # # ret.steerRateCost = 0.35
        
        # # ret.lateralTuning.pid.kf = 0.00006   # full torque for 10 deg at 80mph means 0.00007818594
        # ret.steerRateCost =  0.1
        # ret.steerLimitTimer = 0.8
        # ret.lateralTuning.init('indi')
        
        # ret.lateralTuning.indi.innerLoopGain = 2.65 # 2.48
        # ret.lateralTuning.indi.outerLoopGainBP = [0, 45 * 0.45, 65 * 0.45, 85 * 0.45]
        # ret.lateralTuning.indi.outerLoopGainV = [0.55, 0.73, 1.58, 1.95]
        # ret.lateralTuning.indi.timeConstant = 10.0
        # ret.lateralTuning.indi.actuatorEffectiveness =  1.55
        
    ret.centerToFront = ret.wheelbase * 0.44

    ret.minSteerSpeed = 3.8  # m/s
    if candidate in (CAR.PACIFICA_2019_HYBRID, CAR.PACIFICA_2020, CAR.JEEP_CHEROKEE_2019):
      # TODO allow 2019 cars to steer down to 13 m/s if already engaged.
      ret.minSteerSpeed = 17.5  # m/s 17 on the way up, 13 on the way down once engaged.

    # starting with reasonable value for civic and scaling by mass and wheelbase
    ret.rotationalInertia = scale_rot_inertia(ret.mass, ret.wheelbase)

    # TODO: start from empirically derived lateral slip stiffness for the civic and scale by
    # mass and CG position, so all cars will have approximately similar dyn behaviors
    ret.tireStiffnessFront, ret.tireStiffnessRear = scale_tire_stiffness(ret.mass, ret.wheelbase, ret.centerToFront)

    ret.enableCamera = True
    ret.openpilotLongitudinalControl = True

    return ret

  # returns a car.CarState
  def update(self, c, can_strings):
    # ******************* do can recv *******************
    self.cp.update_strings(can_strings)
    self.cp_cam.update_strings(can_strings)

    ret = self.CS.update(self.cp, self.cp_cam)

    ret.canValid = self.cp.can_valid and self.cp_cam.can_valid

    # speeds
    ret.steeringRateLimited = self.CC.steer_rate_limited if self.CC is not None else False

    # accel/decel button presses
    buttonEvents = []
    if self.CS.accelCruiseButton or self.CS.accelCruiseButtonChanged:
      be = car.CarState.ButtonEvent.new_message()
      be.type = ButtonType.accelCruise
      be.pressed = self.CS.accelCruiseButton
      buttonEvents.append(be)
    if self.CS.decelCruiseButton or self.CS.decelCruiseButtonChanged:
      be = car.CarState.ButtonEvent.new_message()
      be.type = ButtonType.decelCruise
      be.pressed = self.CS.decelCruiseButton
      buttonEvents.append(be)
    if self.CS.resumeCruiseButton or self.CS.resumeCruiseButtonChanged:
      be = car.CarState.ButtonEvent.new_message()
      be.type = ButtonType.resumeCruise
      be.pressed = self.CS.resumeCruiseButton
      buttonEvents.append(be)
    ret.buttonEvents = buttonEvents

    # events
    events = self.create_common_events(ret, extra_gears=[car.CarState.GearShifter.low],
                                       gas_resume_speed=2.)

    if ret.vEgo < self.CP.minSteerSpeed:
      events.add(car.CarEvent.EventName.belowSteerSpeed)

    ret.events = events.to_msg()

    # copy back carState packet to CS
    self.CS.out = ret.as_reader()

    return self.CS.out

  # pass in a car.CarControl
  # to be called @ 100hz
  def apply(self, c):

    if (self.CS.frame == -1):
      return []  # if we haven't seen a frame 220, then do not update.

    can_sends = self.CC.update(c.enabled, self.CS, c.actuators, c.cruiseControl.cancel, c.hudControl.visualAlert,
                               self.CS.out.cruiseState.speed, c.cruiseControl.targetSpeed)

    return can_sends
