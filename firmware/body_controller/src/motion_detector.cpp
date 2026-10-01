#include "motion_detector.h"

#include "motion_config.h"

#include <math.h>

static MotionReadAccel s_readAccel = nullptr;
static MotionProfile s_profile = MOTION_PROFILE_TEST_ALL;
static float s_stepSensMul = 1.0f;

static MotionVec3 baseline{};
static MotionVec3 up{};
static MotionVec3 forward{};
static MotionVec3 right{};

static uint32_t lastJumpMs = 0;
static uint32_t lastStepMs = 0;
static bool duckActive = false;
static float baselineForwardTilt = 0.0f;
static float latSmooth = 0.0f;
static float stepJerkThreshold = MOTION_STEP_JERK_FLOOR_MPS2;
static uint32_t duckAboveMs = 0;
static uint32_t duckBelowMs = 0;
static uint32_t lastDetectMs = 0;

static MotionVec3 normalize(MotionVec3 v) {
  float n = sqrtf(v.x * v.x + v.y * v.y + v.z * v.z);
  if (n < 1e-6f) {
    return {0, 0, 1};
  }
  return {v.x / n, v.y / n, v.z / n};
}

static float dot(MotionVec3 a, MotionVec3 b) {
  return a.x * b.x + a.y * b.y + a.z * b.z;
}

static MotionVec3 sub(MotionVec3 a, MotionVec3 b) {
  return {a.x - b.x, a.y - b.y, a.z - b.z};
}

static MotionVec3 scale(MotionVec3 v, float s) {
  return {v.x * s, v.y * s, v.z * s};
}

static MotionVec3 cross(MotionVec3 a, MotionVec3 b) {
  return {a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x};
}

static MotionVec3 chipForwardAxis() {
  switch (FWD_AXIS) {
    case 0:
      return {1.0f, 0.0f, 0.0f};
    case 1:
      return {0.0f, 1.0f, 0.0f};
    case 2:
      return {0.0f, 0.0f, 1.0f};
    case 3:
      return {-1.0f, 0.0f, 0.0f};
    case 4:
      return {0.0f, -1.0f, 0.0f};
    case 5:
      return {0.0f, 0.0f, -1.0f};
    default:
      return {0.0f, 0.0f, 1.0f};
  }
}

static float forwardTiltDeg(MotionVec3 a) {
  MotionVec3 g = normalize(a);
  return atan2f(dot(g, forward), dot(g, up)) * 180.0f / PI;
}

static float tiltFromNeutralDeg(MotionVec3 a) {
  float c = dot(normalize(a), up);
  if (c > 1.0f) {
    c = 1.0f;
  }
  if (c < -1.0f) {
    c = -1.0f;
  }
  return acosf(c) * 180.0f / PI;
}

static float lateralInstant(MotionVec3 a) {
  MotionVec3 d = sub(a, baseline);
  MotionVec3 dHoriz = sub(d, scale(up, dot(d, up)));
  float lat = dot(dHoriz, right);
#if INVERT_SIDESTEP
  lat = -lat;
#endif
  return lat;
}

void motionSetReadAccel(MotionReadAccel fn) {
  s_readAccel = fn;
}

void motionSetProfile(MotionProfile profile) {
  s_profile = profile;
}

MotionProfile motionGetProfile() {
  return s_profile;
}

const char *motionProfileName(MotionProfile p) {
  switch (p) {
    case MOTION_PROFILE_DINO:
      return "DINO (jump+duck)";
    case MOTION_PROFILE_LANE:
      return "LANE (sidestep)";
    default:
      return "TEST (all)";
  }
}

void motionAdjustStepSensitivity(float delta) {
  s_stepSensMul += delta;
  if (s_stepSensMul < 0.5f) {
    s_stepSensMul = 0.5f;
  }
  if (s_stepSensMul > 2.0f) {
    s_stepSensMul = 2.0f;
  }
}

void motionCalibrate(Stream &log) {
  if (!s_readAccel) {
    log.println("[CAL] no accel reader");
    return;
  }

  log.println();
  log.println("=== CALIBRATE: stand still, face TV ===");
  delay(500);

  MotionVec3 sum{0, 0, 0};
  const int n = MOTION_CAL_STILL_MS / 10;
  for (int i = 0; i < n; i++) {
    MotionVec3 a = s_readAccel();
    sum.x += a.x;
    sum.y += a.y;
    sum.z += a.z;
    delay(10);
  }
  baseline = {sum.x / n, sum.y / n, sum.z / n};

  up = normalize(baseline);
  MotionVec3 chipForward = chipForwardAxis();
  MotionVec3 f = sub(chipForward, scale(up, dot(chipForward, up)));
  forward = normalize(f);
  right = normalize(cross(up, forward));

  baselineForwardTilt = forwardTiltDeg(baseline);
  latSmooth = 0.0f;
  duckAboveMs = 0;
  duckBelowMs = 0;
  duckActive = false;
  lastJumpMs = 0;
  lastStepMs = 0;

  log.println("=== STILL: sidestep noise (2 s) ===");
  float maxJerk = 0.0f;
  const int n2 = MOTION_CAL_NOISE_MS / 10;
  for (int i = 0; i < n2; i++) {
    MotionVec3 a = s_readAccel();
    float lat = lateralInstant(a);
    latSmooth = (1.0f - MOTION_LAT_SMOOTH_ALPHA) * latSmooth + MOTION_LAT_SMOOTH_ALPHA * lat;
    float jerk = fabsf(lat - latSmooth);
    if (jerk > maxJerk) {
      maxJerk = jerk;
    }
    delay(10);
  }
  stepJerkThreshold = maxJerk * MOTION_STEP_NOISE_MARGIN;
  if (stepJerkThreshold < MOTION_STEP_JERK_FLOOR_MPS2) {
    stepJerkThreshold = MOTION_STEP_JERK_FLOOR_MPS2;
  }
  if (stepJerkThreshold > MOTION_STEP_JERK_CEIL_MPS2) {
    stepJerkThreshold = MOTION_STEP_JERK_CEIL_MPS2;
  }

  log.printf("Profile: %s\n", motionProfileName(s_profile));
  log.printf("Baseline: %.2f, %.2f, %.2f  FWD_AXIS=%d\n", baseline.x, baseline.y, baseline.z, FWD_AXIS);
  log.printf("Step threshold: %.2f (noise %.2f) sens x%.2f\n", stepJerkThreshold * s_stepSensMul, maxJerk,
             s_stepSensMul);
  log.println("=== READY ===");
  log.println();
}

void motionPrintStatus(Stream &log) {
  log.printf("profile=%s stepTh=%.2f sens=x%.2f duck=%d\n", motionProfileName(s_profile),
             stepJerkThreshold * s_stepSensMul, s_stepSensMul, duckActive ? 1 : 0);
}

void motionPrintHelp(Stream &log) {
  log.println("Keys: c=calibrate  d=dino  l=lane  a=all test");
  log.println("      b/g/h=boy/girl/toggle  p=button pin levels  +=step  ?=help  #=debug");
  log.println("      Hero button GPIO5 and/or GPIO4 (release toggles boy/girl)");
}

bool motionIsDuckHeld() {
  return duckActive;
}

void motionDebugSample(const MotionVec3 &a, Stream &log) {
  MotionVec3 d = sub(a, baseline);
  float lat = lateralInstant(a);
  float fTd = forwardTiltDeg(a) - baselineForwardTilt;
  log.printf("dbg tiltOff=%.1f fTiltD=%.1f vert=%.2f lat=%.2f sens=x%.2f\n", tiltFromNeutralDeg(a), fTd,
             dot(d, up), lat, s_stepSensMul);
}

void motionUpdate(const MotionVec3 &a, MotionEvents &out) {
  out = MotionEvents{};

  const bool wantJumpDuck = s_profile == MOTION_PROFILE_TEST_ALL || s_profile == MOTION_PROFILE_DINO;
  const bool wantStep = s_profile == MOTION_PROFILE_TEST_ALL || s_profile == MOTION_PROFILE_LANE;

  uint32_t now = millis();
  uint32_t dt = now - lastDetectMs;
  if (dt > 100) {
    dt = 100;
  }
  if (dt == 0) {
    dt = 1;
  }
  lastDetectMs = now;

  MotionVec3 d = sub(a, baseline);
  float vert = dot(d, up);
  float fTiltDelta = forwardTiltDeg(a) - baselineForwardTilt;

  float latInstant = lateralInstant(a);
  latSmooth = (1.0f - MOTION_LAT_SMOOTH_ALPHA) * latSmooth + MOTION_LAT_SMOOTH_ALPHA * latInstant;
  float latJerk = latInstant - latSmooth;

  bool recentJump = (now - lastJumpMs) < MOTION_AFTER_JUMP_QUIET_MS;
  bool recentStep = (now - lastStepMs) < MOTION_AFTER_STEP_QUIET_MS;
  bool jumpLike = vert > MOTION_JUMP_VERT_BLOCK_MPS2;
  float jTh = stepJerkThreshold * s_stepSensMul;
  bool stepLike = fabsf(latJerk) > jTh && fabsf(latInstant) > MOTION_STEP_LAT_MIN_MPS2;
  float tiltOff = tiltFromNeutralDeg(a);
  bool duckPose = tiltOff > MOTION_DUCK_TILT_ON_DEG || fTiltDelta > MOTION_DUCK_FWD_ON_DEG ||
                  (fTiltDelta > 12.0f && vert < MOTION_DUCK_VERT_DROP_MPS2);
  bool duckClear = tiltOff < MOTION_DUCK_TILT_OFF_DEG && fTiltDelta < 10.0f;

  if (wantJumpDuck) {
    if (vert > MOTION_JUMP_VERT_MPS2 && (now - lastJumpMs) > MOTION_COOLDOWN_JUMP_MS) {
      lastJumpMs = now;
      duckAboveMs = 0;
      duckBelowMs = 0;
      if (duckActive) {
        duckActive = false;
        out.duckOff = true;
      }
      out.jump = true;
      return;
    }
  }

  if (wantStep) {
    bool stepAllowed =
        !duckActive && !recentJump && !jumpLike && fabsf(fTiltDelta) < MOTION_STEP_BLOCK_FWD_TILT_DEG;
    if (stepAllowed && (now - lastStepMs) > MOTION_COOLDOWN_STEP_MS) {
      float latMin = MOTION_STEP_LAT_MIN_MPS2;
      bool strongJerkR = latJerk > jTh;
      bool strongJerkL = latJerk < -jTh;
      bool latR = latInstant > latMin;
      bool latL = latInstant < -latMin;
      bool softR = latJerk > jTh * 0.82f && latInstant > latMin * 0.75f;
      bool softL = latJerk < -jTh * 0.82f && latInstant < -latMin * 0.75f;

      if ((strongJerkR && latR) || softR) {
        lastStepMs = now;
        duckAboveMs = 0;
        duckBelowMs = 0;
        out.stepRight = true;
        return;
      }
      if ((strongJerkL && latL) || softL) {
        lastStepMs = now;
        duckAboveMs = 0;
        duckBelowMs = 0;
        out.stepLeft = true;
        return;
      }
    }
  }

  if (!wantJumpDuck) {
    return;
  }

  bool blockDuck = jumpLike || recentJump;
  if (stepLike && !duckPose) {
    blockDuck = true;
  }
  if (recentStep && !duckPose) {
    blockDuck = true;
  }

  if (blockDuck) {
    if (!duckActive) {
      duckAboveMs = 0;
    }
    return;
  }

  if (!duckActive) {
    if (duckPose) {
      duckAboveMs += dt;
    } else {
      duckAboveMs = 0;
    }
    if (duckAboveMs >= MOTION_DUCK_HOLD_MS) {
      duckActive = true;
      out.duckOn = true;
    }
  } else {
    if (duckClear) {
      duckBelowMs += dt;
    } else {
      duckBelowMs = 0;
    }
    if (duckBelowMs >= MOTION_DUCK_RELEASE_MS) {
      duckActive = false;
      duckBelowMs = 0;
      out.duckOff = true;
    }
  }
}
