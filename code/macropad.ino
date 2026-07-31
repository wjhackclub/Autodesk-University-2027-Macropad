#include <HijelHID_BLEKeyboard.h>
#include <Preferences.h>
#include <NimBLEDevice.h>

#define CONFIG_SERVICE_UUID        "a1b2c3d0-0001-0001-0001-000000000001"
#define KEYMAP_WRITE_CHAR_UUID     "a1b2c3d0-0001-0001-0001-000000000002"
#define KEYMAP_READ_CHAR_UUID      "a1b2c3d0-0001-0001-0001-000000000003"

HijelHID_BLEKeyboard keyboard("Macropad", "Espressif", 100);
Preferences prefs;

const int PIN_1 = 0;
const int PIN_2 = 1;
const int PIN_3 = 2;
const int STATUS_LED_PIN = 4;

int lastState1 = HIGH;
int lastState2 = HIGH;
int lastState3 = HIGH;

unsigned long lastDebounceTime1 = 0;
unsigned long lastDebounceTime2 = 0;
unsigned long lastDebounceTime3 = 0;
const unsigned long DEBOUNCE_DELAY = 15;

unsigned long lastLedToggleTime = 0;
const unsigned long BLINK_INTERVAL = 500;
int ledState = LOW;

uint16_t keymap[3] = { KEY_F, KEY_G, KEY_F6 };

NimBLECharacteristic *keymapWriteChar;
NimBLECharacteristic *keymapReadChar;

void onPairingCompleteHandler(bool success) {
  if (success) {
    Serial.println("[APP] Pairing succeeded, restarting advertising to allow another connection");
    NimBLEDevice::startAdvertising();
  } else {
    Serial.println("[APP] Pairing failed");
  }
}

String serialBuffer = "";

void sendKey(uint16_t keycode) {
  uint8_t mod = (keycode >> 8) & 0xFF;
  uint8_t key = keycode & 0xFF;
  
  if (mod == 0) {
    keyboard.tap(key);
  } else {
    // Cast explicitly to uint8_t to resolve ambiguous overload
    if (mod & 0x01) keyboard.press((uint8_t)0xE0);
    if (mod & 0x02) keyboard.press((uint8_t)0xE1);
    if (mod & 0x04) keyboard.press((uint8_t)0xE2);
    if (mod & 0x08) keyboard.press((uint8_t)0xE3);
    
    if (key != 0) {
      keyboard.press(key);
    }
    
    delay(15);
    keyboard.releaseAll();
  }
}

void handleSerialCommand(String cmd) {
  cmd.trim();
  if (cmd.startsWith("SET ")) {
    int firstSpace = cmd.indexOf(' ');
    int secondSpace = cmd.indexOf(' ', firstSpace + 1);
    if (secondSpace == -1) {
      Serial.println("ERR malformed SET command");
      return;
    }
    String indexStr = cmd.substring(firstSpace + 1, secondSpace);
    String keyStr = cmd.substring(secondSpace + 1);
    int index = indexStr.toInt();
    if (index < 0 || index > 2) {
      Serial.println("ERR index out of range");
      return;
    }
    
    uint16_t keyCode = (uint16_t)strtol(keyStr.c_str(), nullptr, 16);
    keymap[index] = keyCode;
    saveKeymapIndex(index);
    updateReadCharacteristic();
    Serial.printf("OK %d %04X\n", index, keyCode);
  } else if (cmd == "GET") {
    Serial.printf("MAP %04X %04X %04X\n", keymap[0], keymap[1], keymap[2]);
  } else if (cmd.length() > 0) {
    Serial.println("ERR unknown command");
  }
}

void processSerialCommands() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') {
      handleSerialCommand(serialBuffer);
      serialBuffer = "";
    } else if (c != '\r') {
      serialBuffer += c;
    }
  }
}

void loadKeymap() {
  prefs.begin("macropad", true);
  keymap[0] = prefs.getUShort("key0", KEY_F);
  keymap[1] = prefs.getUShort("key1", KEY_G);
  keymap[2] = prefs.getUShort("key2", KEY_F6);
  prefs.end();
  Serial.printf("[BOOT] Loaded keymap: %04X %04X %04X\n", keymap[0], keymap[1], keymap[2]);
}

void saveKeymapIndex(uint8_t index) {
  prefs.begin("macropad", false);
  char key[8];
  snprintf(key, sizeof(key), "key%d", index);
  prefs.putUShort(key, keymap[index]);
  prefs.end();
  Serial.printf("[PREFS] Saved key%d = %04X\n", index, keymap[index]);
}

void updateReadCharacteristic() {
  uint16_t payload[3] = { keymap[0], keymap[1], keymap[2] };
  keymapReadChar->setValue((uint8_t*)payload, 6);
  Serial.printf("[CHAR] Read characteristic updated: %04X %04X %04X\n", payload[0], payload[1], payload[2]);
}

class KeymapWriteCallbacks : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic *pChar) {
    std::string value = pChar->getValue();
    Serial.printf("[WRITE] Received %d bytes\n", (int)value.length());
    
    if (value.length() == 3) {
      uint8_t index = (uint8_t)value[0];
      uint16_t keyCode = (uint8_t)value[1] | ((uint16_t)value[2] << 8);
      Serial.printf("[WRITE] index=%d keyCode=%04X\n", index, keyCode);
      
      if (index > 2) {
        Serial.println("[WRITE] Rejected: index out of range");
        return;
      }
      keymap[index] = keyCode;
      saveKeymapIndex(index);
      updateReadCharacteristic();
    } else {
      Serial.println("[WRITE] Rejected: wrong payload length");
    }
  }

  void onSubscribe(NimBLECharacteristic *pChar, ble_gap_conn_desc *desc, uint16_t subValue) {
    Serial.printf("[SUB] Client subscribe state changed: %d\n", subValue);
  }
};

void setupConfigService() {
  Serial.println("[SETUP] Getting NimBLE server instance");
  NimBLEServer *server = keyboard.getServer();
  Serial.printf("[SETUP] Server pointer: %p\n", server);

  NimBLEService *configService = server->createService(CONFIG_SERVICE_UUID);
  Serial.println("[SETUP] Config service created");

  keymapWriteChar = configService->createCharacteristic(
    KEYMAP_WRITE_CHAR_UUID,
    NIMBLE_PROPERTY::WRITE
  );
  keymapWriteChar->setCallbacks(new KeymapWriteCallbacks());
  Serial.println("[SETUP] Write characteristic created");

  keymapReadChar = configService->createCharacteristic(
    KEYMAP_READ_CHAR_UUID,
    NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
  );
  updateReadCharacteristic();
  Serial.println("[SETUP] Read characteristic created");

  configService->start();
  Serial.println("[SETUP] Config service started");

  NimBLEAdvertising *advertising = NimBLEDevice::getAdvertising();
  advertising->stop();
  delay(50);
  advertising->start();
  Serial.println("[SETUP] Advertising restarted with config service active");
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("[BOOT] Starting up");

  pinMode(PIN_1, INPUT_PULLUP);
  pinMode(PIN_2, INPUT_PULLUP);
  pinMode(PIN_3, INPUT_PULLUP);
  pinMode(STATUS_LED_PIN, OUTPUT);
  digitalWrite(STATUS_LED_PIN, ledState);

  delay(2000);

  loadKeymap();

  keyboard.setLogLevel(HIDLogLevel::Verbose);
  keyboard.onPairingComplete(onPairingCompleteHandler);

  Serial.println("[BOOT] Calling keyboard.begin()");
  keyboard.begin();
  Serial.println("[BOOT] keyboard.begin() returned");

  setupConfigService();

  Serial.println("[BOOT] Setup complete, entering loop");
}

void loop() {
  unsigned long currentMillis = millis();

  static bool wasPaired = false;
  bool isPaired = keyboard.isPaired();
  if (isPaired != wasPaired) {
    Serial.printf("[BLE] Pairing state changed: %s\n", isPaired ? "PAIRED" : "NOT PAIRED");
    wasPaired = isPaired;
  }

  if (isPaired) {
    ledState = HIGH;
    digitalWrite(STATUS_LED_PIN, ledState);
  } else {
    if (currentMillis - lastLedToggleTime >= BLINK_INTERVAL) {
      lastLedToggleTime = currentMillis;
      ledState = !ledState;
      digitalWrite(STATUS_LED_PIN, ledState);
    }
  }

  int reading1 = digitalRead(PIN_1);
  if (reading1 != lastState1) {
    if ((currentMillis - lastDebounceTime1) > DEBOUNCE_DELAY) {
      if (reading1 == LOW && isPaired) {
        Serial.printf("[BTN] Button 1 -> keycode %04X\n", keymap[0]);
        sendKey(keymap[0]);
      }
      lastState1 = reading1;
      lastDebounceTime1 = currentMillis;
    }
  }

  int reading2 = digitalRead(PIN_2);
  if (reading2 != lastState2) {
    if ((currentMillis - lastDebounceTime2) > DEBOUNCE_DELAY) {
      if (reading2 == LOW && isPaired) {
        Serial.printf("[BTN] Button 2 -> keycode %04X\n", keymap[1]);
        sendKey(keymap[1]);
      }
      lastState2 = reading2;
      lastDebounceTime2 = currentMillis;
    }
  }

  int reading3 = digitalRead(PIN_3);
  if (reading3 != lastState3) {
    if ((currentMillis - lastDebounceTime3) > DEBOUNCE_DELAY) {
      if (reading3 == LOW && isPaired) {
        Serial.printf("[BTN] Button 3 -> keycode %04X\n", keymap[2]);
        sendKey(keymap[2]);
      }
      lastState3 = reading3;
      lastDebounceTime3 = currentMillis;
    }
  }

  processSerialCommands();

  delay(5);
}