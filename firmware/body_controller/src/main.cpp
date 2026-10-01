/**
 * Body BLE Games — ESP32-C3 controller (MPU-6050 + BLE notify to Pi).
 */

#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Arduino.h>
#include <Wire.h>

#include <BLE2902.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>

#include "ble_protocol.h"
#include "motion_config.h"
#include "motion_detector.h"

#ifndef PIN_SDA
#define PIN_SDA 8
#endif
#ifndef PIN_SCL
#define PIN_SCL 9
#endif

static int activeSda = PIN_SDA;
static int activeScl = PIN_SCL;
static const uint32_t SAMPLE_US = 10000;
static const uint32_t BTN_DEBOUNCE_MS = 40;

Adafruit_MPU6050 mpu;
static uint8_t mpuAddr = 0x68;
static bool useRawMpu = false;

static BLECharacteristic *g_inputChar = nullptr;
static bool g_bleConnected = false;
static uint8_t g_seq = 0;
static uint32_t g_lastBleSendMs = 0;

static bool heroGirl = false;

class BodyServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *server) override {
    g_bleConnected = true;
    Serial.println("[BLE] connected");
  }
  void onDisconnect(BLEServer *server) override {
    g_bleConnected = false;
    Serial.println("[BLE] disconnected");
    server->startAdvertising();
  }
};

static void bleInit() {
  const uint64_t mac = ESP.getEfuseMac();
  char name[24];
  snprintf(name, sizeof(name), "%s-%04X", BLE_DEVICE_NAME_PREFIX, static_cast<unsigned>(mac & 0xFFFF));

  BLEDevice::init(name);
  Serial.printf("[BLE] advertise as %s\n", name);

  BLEServer *server = BLEDevice::createServer();
  server->setCallbacks(new BodyServerCallbacks());
  BLEService *service = server->createService(BLE_SERVICE_UUID);
  g_inputChar =
      service->createCharacteristic(BLE_CHAR_INPUT_UUID, BLECharacteristic::PROPERTY_NOTIFY);
  g_inputChar->addDescriptor(new BLE2902());
  service->start();

  BLEAdvertising *adv = BLEDevice::getAdvertising();
  adv->addServiceUUID(BLE_SERVICE_UUID);
  adv->setScanResponse(true);
  adv->start();
}

static void bleSendFlags(uint8_t flags) {
  if (!g_bleConnected || g_inputChar == nullptr) {
    return;
  }
  InputPacket pkt{};
  pkt.seq = g_seq++;
  pkt.flags = flags;
  pkt.reserved = 0;
  pkt.millis_ts = millis();
  g_inputChar->setValue(reinterpret_cast<uint8_t *>(&pkt), sizeof(pkt));
  g_inputChar->notify();
  g_lastBleSendMs = millis();
}

static void bleFromMotion(const MotionEvents &ev) {
  uint8_t flags = 0;
  if (heroGirl) {
    flags |= FL_HERO_GIRL;
  }
  if (motionIsDuckHeld()) {
    flags |= FL_DUCK;
  }
  if (ev.jump) {
    flags |= FL_JUMP;
  }
  if (ev.stepLeft) {
    flags |= FL_STEP_L;
  }
  if (ev.stepRight) {
    flags |= FL_STEP_R;
  }

  static uint8_t lastBase = 0xFF;
  const uint8_t base = flags & (FL_HERO_GIRL | FL_DUCK);
  const uint8_t pulse = flags & (FL_JUMP | FL_STEP_L | FL_STEP_R);
  const bool heartbeat = millis() - g_lastBleSendMs > 180;

  if (pulse || base != lastBase || heartbeat) {
    bleSendFlags(flags);
    if (pulse) {
      bleSendFlags(flags);
    }
    lastBase = base;
  }
}

static void heroLoadDefault() {
#if CONTROLLER_VARIANT == 1
  heroGirl = true;
#else
  heroGirl = false;
#endif
}

static void printHeroIdentity() {
  Serial.println(heroGirl ? "[HERO] GIRL (pink)" : "[HERO] BOY (blue)");
}

static void onHeroChanged();

static bool heroBtnPinPressed(int gpio) {
  const int v = digitalRead(gpio);
#if HERO_BTN_ACTIVE_LOW
  return v == LOW;
#else
  return v == HIGH;
#endif
}

static bool heroBtnAnyPressed() {
  if (PIN_HERO_BTN >= 0 && heroBtnPinPressed(PIN_HERO_BTN)) {
    return true;
  }
  if (PIN_HERO_BTN_ALT >= 0 && PIN_HERO_BTN_ALT != PIN_HERO_BTN &&
      heroBtnPinPressed(PIN_HERO_BTN_ALT)) {
    return true;
  }
  return false;
}

static void printHeroBtnPins() {
  Serial.printf("[BTN] raw GPIO%d=%d GPIO%d=%d (active-%s; release toggles hero)\n", PIN_HERO_BTN,
                digitalRead(PIN_HERO_BTN), PIN_HERO_BTN_ALT, digitalRead(PIN_HERO_BTN_ALT),
#if HERO_BTN_ACTIVE_LOW
                "low");
#else
                "high");
#endif
}

static void heroBtnInitPins() {
  if (PIN_HERO_BTN >= 0) {
    pinMode(PIN_HERO_BTN, INPUT_PULLUP);
  }
  if (PIN_HERO_BTN_ALT >= 0 && PIN_HERO_BTN_ALT != PIN_HERO_BTN) {
    pinMode(PIN_HERO_BTN_ALT, INPUT_PULLUP);
  }
}

static void pollHeroButton() {
  static bool stablePressed = false;
  static bool lastRead = false;
  static uint32_t lastChangeMs = 0;

  const bool pressed = heroBtnAnyPressed();
  if (pressed != lastRead) {
    lastChangeMs = millis();
    lastRead = pressed;
  }
  if (millis() - lastChangeMs < BTN_DEBOUNCE_MS) {
    return;
  }
  if (pressed == stablePressed) {
    return;
  }
  const bool wasPressed = stablePressed;
  stablePressed = pressed;
  printHeroBtnPins();
  Serial.println(pressed ? "[BTN] down" : "[BTN] up");
  if (wasPressed && !pressed) {
    heroGirl = !heroGirl;
    onHeroChanged();
  }
}

static bool mpuWriteReg(uint8_t addr, uint8_t reg, uint8_t val) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(val);
  return Wire.endTransmission() == 0;
}

static uint8_t mpuReadReg(uint8_t addr, uint8_t reg) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) {
    return 0xFF;
  }
  if (Wire.requestFrom(addr, static_cast<uint8_t>(1)) != 1) {
    return 0xFF;
  }
  return Wire.read();
}

static int16_t mpuRead16(uint8_t addr, uint8_t reg) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) {
    return 0;
  }
  if (Wire.requestFrom(addr, static_cast<uint8_t>(2)) != 2) {
    return 0;
  }
  uint16_t hi = Wire.read();
  uint16_t lo = Wire.read();
  return static_cast<int16_t>((hi << 8) | lo);
}

static void mpuWake(uint8_t addr) {
  mpuWriteReg(addr, 0x6B, 0x00);
}

static MotionVec3 readAccelMps2() {
  if (useRawMpu) {
    constexpr float kLsbPerG = 4096.0f;
    constexpr float kG = 9.80665f;
    return {mpuRead16(mpuAddr, 0x3B) / kLsbPerG * kG, mpuRead16(mpuAddr, 0x3D) / kLsbPerG * kG,
            mpuRead16(mpuAddr, 0x3F) / kLsbPerG * kG};
  }
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);
  return {a.acceleration.x, a.acceleration.y, a.acceleration.z};
}

static MotionVec3 readAccelBridge() {
  return readAccelMps2();
}


static void printEvents(const MotionEvents &e) {
  if (e.jump) {
    Serial.println("[JUMP]");
  }
  if (e.stepLeft) {
    Serial.println("[STEP] LEFT");
  }
  if (e.stepRight) {
    Serial.println("[STEP] RIGHT");
  }
  if (e.duckOn) {
    Serial.println("[DUCK] ON");
  }
  if (e.duckOff) {
    Serial.println("[DUCK] OFF");
  }
}

static void onHeroChanged() {
  printHeroIdentity();
  bleSendFlags(heroGirl ? FL_HERO_GIRL : 0);
}

static void i2cBusBegin(int sda, int scl) {
  Wire.end();
  delay(20);
  activeSda = sda;
  activeScl = scl;
  pinMode(activeSda, INPUT_PULLUP);
  pinMode(activeScl, INPUT_PULLUP);
  Wire.begin(activeSda, activeScl);
  Wire.setClock(100000);
  Wire.setTimeOut(1000);
  delay(10);
}

static bool i2cFindMpuPins(int &outSda, int &outScl, uint8_t &outAddr) {
  static const int kPairs[][2] = {{PIN_SDA, PIN_SCL}, {6, 7}, {8, 9}, {9, 8}, {7, 6}};
  for (const auto &pair : kPairs) {
    int sda = pair[0];
    int scl = pair[1];
    if (sda == PIN_HERO_BTN || scl == PIN_HERO_BTN || sda == PIN_HERO_BTN_ALT || scl == PIN_HERO_BTN_ALT) {
      continue;
    }
    i2cBusBegin(sda, scl);
    for (uint8_t addr : {0x68u, 0x69u}) {
      Wire.beginTransmission(addr);
      if (Wire.endTransmission() == 0) {
        outSda = sda;
        outScl = scl;
        outAddr = addr;
        return true;
      }
    }
  }
  return false;
}

static void i2cScan() {
  Serial.printf("I2C scan SDA=GPIO%d SCL=GPIO%d:\n", activeSda, activeScl);
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  0x%02X\n", addr);
    }
  }
}

static bool initMpuRaw(uint8_t addr) {
  Wire.beginTransmission(addr);
  if (Wire.endTransmission() != 0) {
    return false;
  }
  mpuWake(addr);
  delay(50);
  if (mpuReadReg(addr, 0x75) == 0xFF) {
    return false;
  }
  if (!mpuWriteReg(addr, 0x1C, 0x10) || !mpuWriteReg(addr, 0x1A, 0x04)) {
    return false;
  }
  mpuAddr = addr;
  useRawMpu = true;
  return true;
}

static bool initMpuAt(uint8_t addr) {
  useRawMpu = false;
  mpuWake(addr);
  delay(50);
  if (mpu.begin(addr, &Wire)) {
    mpuAddr = addr;
    Serial.printf("MPU OK 0x%02X SDA=%d SCL=%d\n", addr, activeSda, activeScl);
    return true;
  }
  if (initMpuRaw(addr)) {
    Serial.printf("MPU OK raw 0x%02X SDA=%d SCL=%d\n", addr, activeSda, activeScl);
    return true;
  }
  return false;
}

static bool initMpu() {
  int sda = 0;
  int scl = 0;
  uint8_t addr = 0;
  if (!i2cFindMpuPins(sda, scl, addr)) {
    i2cBusBegin(PIN_SDA, PIN_SCL);
    return false;
  }
  i2cBusBegin(sda, scl);
  return initMpuAt(addr);
}

static void handleSerialChar(char c) {
  switch (c) {
    case 'c':
      motionCalibrate(Serial);
      break;
    case 'd':
      motionSetProfile(MOTION_PROFILE_DINO);
      Serial.printf("Profile: %s\n", motionProfileName(MOTION_PROFILE_DINO));
      break;
    case 'l':
      motionSetProfile(MOTION_PROFILE_LANE);
      Serial.printf("Profile: %s\n", motionProfileName(MOTION_PROFILE_LANE));
      break;
    case 'a':
      motionSetProfile(MOTION_PROFILE_TEST_ALL);
      Serial.printf("Profile: %s\n", motionProfileName(MOTION_PROFILE_TEST_ALL));
      break;
    case '+':
      motionAdjustStepSensitivity(-0.1f);
      motionPrintStatus(Serial);
      break;
    case '-':
      motionAdjustStepSensitivity(0.1f);
      motionPrintStatus(Serial);
      break;
    case '?':
      motionPrintHelp(Serial);
      break;
    case '#':
      motionDebugSample(readAccelMps2(), Serial);
      break;
    case 's':
      i2cScan();
      break;
    case 'r':
      if (initMpu()) {
        motionCalibrate(Serial);
      }
      break;
    case 'g':
      heroGirl = true;
      onHeroChanged();
      break;
    case 'b':
      heroGirl = false;
      onHeroChanged();
      break;
    case 'h':
      heroGirl = !heroGirl;
      onHeroChanged();
      break;
    case 'p':
      printHeroBtnPins();
      break;
    default:
      break;
  }
}

void setup() {
  Serial.begin(115200);
  delay(800);
  Serial.println();
  Serial.println("Body BLE controller - ESP32-C3 + MPU-6050");
  motionPrintHelp(Serial);
  Serial.printf("FWD_AXIS=%d  (edit motion_config.h / platformio.ini)\n", FWD_AXIS);

  heroBtnInitPins();
  heroLoadDefault();
  printHeroIdentity();
  printHeroBtnPins();
  Serial.println("Press hero button: expect [BTN] down/up (serial p=pin read b/g/h)");

  motionSetReadAccel(readAccelBridge);
  motionSetProfile(MOTION_PROFILE_TEST_ALL);

  i2cBusBegin(PIN_SDA, PIN_SCL);
  if (!initMpu()) {
    Serial.println("MPU not found. Keys: s=scan r=retry");
    while (true) {
      if (Serial.available()) {
        handleSerialChar(static_cast<char>(Serial.read()));
      }
      pollHeroButton();
      delay(10);
    }
  }

  if (!useRawMpu) {
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  }

  motionCalibrate(Serial);
  bleInit();
}

void loop() {
  static uint32_t lastSample = 0;
  static uint32_t lastAlive = 0;

  if (micros() - lastSample >= SAMPLE_US) {
    lastSample = micros();
    MotionEvents ev;
    motionUpdate(readAccelMps2(), ev);
    printEvents(ev);
    bleFromMotion(ev);
  }

  while (Serial.available()) {
    handleSerialChar(static_cast<char>(Serial.read()));
  }

  pollHeroButton();

  if (millis() - lastAlive > 5000) {
    lastAlive = millis();
    Serial.printf("[alive] %s — c=cal  d/l/a=profile  ?=help\n", motionProfileName(motionGetProfile()));
  }
}
