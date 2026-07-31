# Macropad

A wireless BLE keyboard the size of your hand.
<img width="2160" height="1082" alt="thumbnail (1)" src="https://github.com/user-attachments/assets/46accc81-fb6a-4021-981c-a8541892e624" />

This project was made for Autodesk University 2027 to assist apps without autocomplete. The Macropad uses the ESP32 core chip for latency-free Bluetooth transmission, taking sub 50ms. Features include key debouncing, a status LED indicator, a quick swap keybind changing tool, and an internal memory storage bank. Menu choices and key layouts can be configured easily using the desktop app. When a key is pressed either word, sentence, or code the phrase from your computer is sent over wifi to a local 3.5b parameter AI on the Arduino Uno Q where it is processed and sent back as a complete phrase.

## BOM

| Component | Description | Quantity | Approx Price (USD) |
| :--- | :--- | :--- | :--- |
| **ESP32 Dev Kit** | Microcontroller | 1 | $4.50 |
| **Tactile Buttons** | Tap input keys (any brand cherry mx style) | 3 | $0.30 |
| **Status LED** | Indication led for network states | 1 | $0.10 |
| **FR1 Copper Clad Sheet** | Base board for pcb | 1 | $1.00 |
| **Total Cost** | -- | -- | **~$5.90** |


---

## How it works

### 1. Keyboard Firmware
The ESP32 mimics a standard Bluetooth keyboard so your computer recognizes and trusts it. At the same time, it leaves a connection open for your Windows application to connect. This lets you rebind your gaming keys instantly without losing connection. Once sent, the new keys save directly to the onboard memory so they stick even after a reboot.

### 2. Desktop Firmware
Windows recognizes the Macropad as a standard USB device when it is plugged in. The desktop app connects directly to this active USB port and listens for the hardware footprint. Once selected, it streams your new keybind configuration data through the cable.

---
## Wiring Guide

```text
Button Wiring:
* Button 1       | GPIO 0 | GND
* Button 2       | GPIO 1 | GND
* Button 3       | GPIO 2 | GND

Battery Wiring:
* Battery (+)    | TP4056 (B+)
* Battery (-)    | TP4056 (B-)
* TP4056 (OUT-)  | ESP32 (GND)
* TP4056 (OUT+)  | Switch (Middle Pin)
* Switch (Outer) | ESP32 (VIN / 5V)

LED Wiring:
* Long Leg (+)   | ESP32 (GPIO 4)
* Short Leg (-)  | ESP32 (GND)
```


## Building & Compiling

### Arduino Firmware Setup
Ensure you have the `NimBLE-Arduino` package installed through your library manager. Compile and flash the script directly to your ESP32 board.

### Native Windows App Compilation
If you make modifications to the Python app script, re-bundle the project into an `.exe` using the system tool command:

```powershell
# Setup requirements
pip install bleak customtkinter pyinstaller

# Build into a executable
python -m PyInstaller --noconsole --onefile keybinds.py
```
Your compiled launcher will be placed cleanly inside the newly generated `/dist` directory.

Currently WIP when the Uno Q arrives I will begin coding the AI functions.
