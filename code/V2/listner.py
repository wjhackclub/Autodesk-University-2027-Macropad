import time
import asyncio
import threading
import random
from datetime import datetime
import requests
import pyautogui
import keyboard
import pyperclip
import psutil
import serial
from comtypes import CLSCTX_ALL
from ctypes import cast, POINTER
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import winrt.windows.media.control as wmc

UNO_Q_IP = "10.0.0.102"
SERVER_URL = f"http://{UNO_Q_IP}:5000/process"
COM_PORT = 'COM3'
BAUD_RATE = 115200
BROWSER_SOURCES = {"chrome", "firefox", "msedge", "opera", "brave", "vivaldi", "arc"}

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {message}")

def get_volume_control():
    try:
        devices = AudioUtilities.GetDeviceEnumerator()
        interface = devices.GetDefaultAudioEndpoint(0, 1)
        volume_iface = interface.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(volume_iface, POINTER(IAudioEndpointVolume))
    except Exception as e:
        log(f"Volume Sync Error: {e}")
        return None

volume_ctrl = get_volume_control()

try:
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=0.01)
    log(f"Connected to {COM_PORT}.")
except Exception as e:
    log(f"Serial Error: {e}")
    ser = None

class MediaTracker:
    def __init__(self):
        self.song = "No Music"
        self.pos = 0.0
        self.dur = 0.0
        self.playing = 0
        self.prev_playing = 0
        self.is_browser = False

tracker = MediaTracker()

def send_to_ai(text, mode):
    log(f"-> Sending request to Uno Q | Mode: '{mode}'")
    log(f"   [SENT TEXT]: {repr(text)}")
    
    start_time = time.time()
    try:
        response = requests.post(SERVER_URL, json={'text': text, 'mode': mode}, timeout=180)
        elapsed_time = time.time() - start_time
        log(f"<- Response received in {elapsed_time:.2f}s | HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            completion = result.get('completion', '').strip()
            log(f"   [RECEIVED TEXT]: {repr(completion)}")
            return completion
        else:
            log(f"   ERROR: Server returned unexpected status code {response.status_code}")
    except requests.exceptions.Timeout:
        elapsed_time = time.time() - start_time
        log(f"   ERROR: Request timed out after {elapsed_time:.2f}s.")
    except Exception as e:
        elapsed_time = time.time() - start_time
        log(f"   ERROR: Failed to communicate after {elapsed_time:.2f}s: {e}")
        
    return ""

def run_async(task_func):
    threading.Thread(target=task_func, daemon=True).start()

def action_complete_line():
    log("-> Triggered Key 1: Complete Current Line")
    run_async(task_complete_line)

def task_complete_line():
    time.sleep(0.15)
    pyautogui.hotkey('home')
    pyautogui.hotkey('shift', 'end')
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.15)
    
    line_text = pyperclip.paste().rstrip('\r\n')
    if not line_text.strip():
        log("Line is empty. Aborting action.")
        return

    completion = send_to_ai(line_text, 'complete')
    if completion:
        pyautogui.hotkey('home')
        pyautogui.hotkey('shift', 'end')
        pyperclip.copy(completion)
        pyautogui.hotkey('ctrl', 'v')
        log("[DONE]")
    else:
        log("FAILED")

def action_fix_line():
    log("-> Triggered Key 2: Fix Bugs on Line")
    run_async(task_fix_line)

def task_fix_line():
    time.sleep(0.15)
    pyautogui.hotkey('home')
    pyautogui.hotkey('shift', 'end')
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.15)
    
    line_text = pyperclip.paste().rstrip('\r\n')
    if not line_text.strip():
        log("Line is empty. Aborting action.")
        return

    fixed_code = send_to_ai(line_text, 'fix')
    if fixed_code:
        pyautogui.hotkey('home')
        pyautogui.hotkey('shift', 'end')
        pyperclip.copy(fixed_code)
        pyautogui.hotkey('ctrl', 'v')
        log("[DONE]")
    else:
        log("FAILED")

def action_generate_program():
    log("-> Triggered Key 3: Generate Full Program")
    run_async(task_generate_program)

def task_generate_program():
    time.sleep(0.15)
    pyautogui.hotkey('home')
    pyautogui.hotkey('shift', 'end')
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.15)
    
    instruction_line = pyperclip.paste().strip()
    if not instruction_line:
        log("Line is empty. Aborting action.")
        return

    cleaned_prompt = instruction_line
    if cleaned_prompt.startswith('//'):
        cleaned_prompt = cleaned_prompt[2:].strip()
    elif cleaned_prompt.startswith('#'):
        cleaned_prompt = cleaned_prompt[1:].strip()

    program_code = send_to_ai(cleaned_prompt, 'block')
    if program_code:
        pyautogui.hotkey('home')
        pyautogui.hotkey('shift', 'end')
        pyperclip.copy(program_code)
        pyautogui.hotkey('ctrl', 'v')
        log("[DONE]")
    else:
        log("FAILED")

async def media_task():
    while True:
        try:
            manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
            session = manager.get_current_session()
            if session:
                source = session.source_app_user_model_id.lower()
                tracker.is_browser = any(b in source for b in BROWSER_SOURCES)

                props = await session.try_get_media_properties_async()
                tracker.song = props.title[:40] if props.title else "No Music"

                info = session.get_playback_info()
                tracker.prev_playing = tracker.playing
                tracker.playing = 1 if info.playback_status == 4 else 0

                if not tracker.is_browser:
                    timeline = session.get_timeline_properties()
                    pos = timeline.position.total_seconds()
                    dur = timeline.end_time.total_seconds()
                    tracker.pos = max(0.0, pos) if pos and pos == pos else 0.0
                    tracker.dur = max(0.0, dur) if dur and dur == dur else 0.0
                else:
                    tracker.pos = 0.0
                    tracker.dur = 0.0
            else:
                tracker.prev_playing = tracker.playing
                tracker.playing = 0
                tracker.is_browser = False
        except:
            tracker.prev_playing = tracker.playing
            tracker.playing = 0
            tracker.is_browser = False
        await asyncio.sleep(0.5)

h_bars = [0] * 12
bars_fading = False
cpu_cache, ram_cache = 0, 0
last_stat_time = 0

async def serial_loop():
    global cpu_cache, ram_cache, volume_ctrl, bars_fading, last_stat_time

    asyncio.ensure_future(media_task())
    next_tick = time.perf_counter()

    while True:
        now = time.perf_counter()
        if now < next_tick:
            await asyncio.sleep(next_tick - now)
        next_tick += 0.05

        if ser and ser.in_waiting > 0:
            try:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line == "CW":     keyboard.press_and_release('volume up')
                elif line == "CCW":  keyboard.press_and_release('volume down')
                elif line == "PAUSE": keyboard.press_and_release('play/pause media')
                elif line == "NEXT":  keyboard.press_and_release('next track')
                elif line == "PREV":  keyboard.press_and_release('previous track')
            except:
                pass

        current_vol = 0
        try:
            if volume_ctrl:
                current_vol = round(volume_ctrl.GetMasterVolumeLevelScalar() * 100)
            else:
                volume_ctrl = get_volume_control()
        except:
            pass

        if time.time() - last_stat_time > 2.0:
            cpu_cache = int(psutil.cpu_percent())
            ram_cache = round(psutil.virtual_memory().used / (1024**3), 1)
            last_stat_time = time.time()

        if not tracker.is_browser:
            if tracker.prev_playing == 1 and tracker.playing == 0:
                bars_fading = True

            fade_mult = 1.0
            if tracker.playing:
                bars_fading = False
                if tracker.dur > 0:
                    time_left = tracker.dur - tracker.pos
                    if tracker.pos < 3.0:    fade_mult = tracker.pos / 3.0
                    elif time_left < 3.0:   fade_mult = time_left / 3.0

            for i in range(12):
                if tracker.playing:
                    if random.random() > 0.85:
                        h_bars[i] = int(random.randint(10, 32) * fade_mult)
                    h_bars[i] = max(0, h_bars[i] - 2)
                elif bars_fading:
                    h_bars[i] = max(0, h_bars[i] - 2)
                    if all(b == 0 for b in h_bars):
                        bars_fading = False
                else:
                    h_bars[i] = 0
        else:
            for i in range(12):
                h_bars[i] = 0
            bars_fading = False

        t = time.localtime()
        playing_out = tracker.playing if not tracker.is_browser else 0

        packet = (
            f"{cpu_cache}|{ram_cache}G|{tracker.song}|"
            f"{int(tracker.pos)}|{int(tracker.dur)}|"
            f"{','.join(map(str, h_bars))}|"
            f"{t.tm_hour % 12 or 12}|{t.tm_min:02d}|"
            f"{playing_out}|{current_vol}\n"
        )
        if ser:
            try:
                ser.write(packet.encode())
            except Exception as e:
                log(f"Serial write failed: {e}")

def start_asyncio_thread():
    asyncio.run(serial_loop())

def main():
    log("=== K3Y Macro Pad & System Sync Listener Started ===")
    log(f"Target Uno Q Endpoint: {SERVER_URL}")
    log("  - Ctrl+Alt+R (Key 1): Complete current line")
    log("  - Ctrl+Alt+T (Key 2): Fix bugs on current line")
    log("  - Ctrl+Alt+Y (Key 3): Generate full program from `//` instruction")
    log("Press Ctrl+C to exit.\n")

    keyboard.add_hotkey('ctrl+alt+r', action_complete_line, suppress=True)
    keyboard.add_hotkey('ctrl+alt+t', action_fix_line, suppress=True)
    keyboard.add_hotkey('ctrl+alt+y', action_generate_program, suppress=True)

    threading.Thread(target=start_asyncio_thread, daemon=True).start()

    keyboard.wait()

if __name__ == '__main__':
    main()
