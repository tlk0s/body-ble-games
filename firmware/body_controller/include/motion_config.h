#pragma once

// --- Mount / wiring (PlatformIO build_flags can override) ---
#ifndef FWD_AXIS
#define FWD_AXIS 2
#endif

#ifndef INVERT_SIDESTEP
#define INVERT_SIDESTEP 1
#endif

// Boot default: 0 = boy, 1 = girl (match blue vs red unit). Button press toggles at runtime.
#ifndef CONTROLLER_VARIANT
#define CONTROLLER_VARIANT 0
#endif

// Hero button: momentary to GND + internal pull-up. Use GPIO4 if you replaced the rocker on the same pads.
#ifndef PIN_HERO_BTN
#define PIN_HERO_BTN 5
#endif
#ifndef PIN_HERO_BTN_ALT
#define PIN_HERO_BTN_ALT 4
#endif
#ifndef HERO_BTN_ACTIVE_LOW
#define HERO_BTN_ACTIVE_LOW 1
#endif

// --- Timing ---
#define MOTION_CAL_STILL_MS 3000
#define MOTION_CAL_NOISE_MS 2000
#define MOTION_COOLDOWN_JUMP_MS 450
#define MOTION_COOLDOWN_STEP_MS 450
#define MOTION_AFTER_JUMP_QUIET_MS 480
#define MOTION_AFTER_STEP_QUIET_MS 450
#define MOTION_DUCK_HOLD_MS 120
#define MOTION_DUCK_RELEASE_MS 120

// --- Jump / duck / sidestep thresholds (one place to tune) ---
#define MOTION_JUMP_VERT_MPS2 2.8f
#define MOTION_JUMP_VERT_BLOCK_MPS2 1.6f

#define MOTION_STEP_JERK_FLOOR_MPS2 1.35f
#define MOTION_STEP_JERK_CEIL_MPS2 2.4f
#define MOTION_STEP_LAT_MIN_MPS2 0.65f
#define MOTION_STEP_NOISE_MARGIN 2.0f
#define MOTION_LAT_SMOOTH_ALPHA 0.15f
#define MOTION_STEP_BLOCK_FWD_TILT_DEG 24.0f

#define MOTION_DUCK_TILT_ON_DEG 14.0f
#define MOTION_DUCK_TILT_OFF_DEG 9.0f
#define MOTION_DUCK_FWD_ON_DEG 16.0f
#define MOTION_DUCK_VERT_DROP_MPS2 -0.6f
