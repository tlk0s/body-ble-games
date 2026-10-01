#pragma once

#include <stdint.h>

#define BLE_DEVICE_NAME_PREFIX "BodyCtrl"
#define BLE_SERVICE_UUID "4fafc201-1fb5-459e-8fcc-c5c09c331914"
#define BLE_CHAR_INPUT_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

enum InputFlags : uint8_t {
  FL_JUMP = 0x01,
  FL_DUCK = 0x02,
  FL_STEP_L = 0x04,
  FL_STEP_R = 0x08,
  FL_HERO_GIRL = 0x10,
};

struct InputPacket {
  uint8_t seq;
  uint8_t flags;
  uint16_t reserved;
  uint32_t millis_ts;
} __attribute__((packed));

static_assert(sizeof(InputPacket) == 8, "InputPacket must be 8 bytes");
