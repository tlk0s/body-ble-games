#pragma once

#include <Arduino.h>

struct MotionVec3 {
  float x, y, z;
};

enum MotionProfile : uint8_t {
  MOTION_PROFILE_TEST_ALL = 0,
  MOTION_PROFILE_DINO = 1,  // jump + duck only (Chrome dino game)
  MOTION_PROFILE_LANE = 2,  // sidestep only (lane race game)
};

struct MotionEvents {
  bool jump = false;
  bool stepLeft = false;
  bool stepRight = false;
  bool duckOn = false;
  bool duckOff = false;
};

using MotionReadAccel = MotionVec3 (*)();

void motionSetReadAccel(MotionReadAccel fn);
void motionSetProfile(MotionProfile profile);
MotionProfile motionGetProfile();
const char *motionProfileName(MotionProfile p);

void motionCalibrate(Stream &log);
void motionUpdate(const MotionVec3 &accel, MotionEvents &out);
void motionPrintStatus(Stream &log);
void motionPrintHelp(Stream &log);

void motionAdjustStepSensitivity(float delta);  // + easier, - harder

void motionDebugSample(const MotionVec3 &accel, Stream &log);
