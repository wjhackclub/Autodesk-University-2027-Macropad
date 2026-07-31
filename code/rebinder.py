import threading
import queue
import customtkinter as ctk
import serial
import serial.tools.list_ports

KEYS = {
    "F1": 0x3A, "F2": 0x3B, "F3": 0x3C, "F4": 0x3D, "F5": 0x3E, "F6": 0x3F,
    "F7": 0x40, "F8": 0x41, "F9": 0x42, "F10": 0x43, "F11": 0x44, "F12": 0x45,
    "ESCAPE": 0x29, "RETURN": 0x28, "TAB": 0x2B, "BACKSPACE": 0x2A,
    "DELETE": 0x4C, "INSERT": 0x49, "HOME": 0x4A, "END": 0x4D,
    "PAGE_UP": 0x4B, "PAGE_DOWN": 0x4E, "CAPS_LOCK": 0x39,
    "UP": 0x52, "DOWN": 0x51, "LEFT": 0x50, "RIGHT": 0x4F,
    "LEFT_CTRL": 0xE0, "LEFT_SHIFT": 0xE1, "LEFT_ALT": 0xE2, "LEFT_GUI": 0xE3,
    "RIGHT_CTRL": 0xE4, "RIGHT_SHIFT": 0xE5, "RIGHT_ALT": 0xE6, "RIGHT_GUI": 0xE7,
    "SPACE": 0x2C, "MINUS": 0x2D, "EQUAL": 0x2E, "LEFTBRACE": 0x2F,
    "RIGHTBRACE": 0x30, "BACKSLASH": 0x31, "SEMICOLON": 0x33,
    "APOSTROPHE": 0x34, "GRAVE": 0x35, "COMMA": 0x36, "DOT": 0x37, "SLASH": 0x38,
}

CHARS = {
    ' ': "SPACE", '-': "MINUS", '=': "EQUAL", '[': "LEFTBRACE",
    ']': "RIGHTBRACE", '\\': "BACKSLASH", ';': "SEMICOLON",
    "'": "APOSTROPHE", '`': "GRAVE", ',': "COMMA", '.': "DOT", '/': "SLASH"
}

LETS = {chr(ord('a') + i): 0x04 + i for i in range(26)}
DIGS = {
    "1": 0x1E, "2": 0x1F, "3": 0x20, "4": 0x21, "5": 0x22,
    "6": 0x23, "7": 0x24, "8": 0x25, "9": 0x26, "0": 0x27,
}

TKS = {
    "Escape": "ESCAPE", "Return": "RETURN", "Tab": "TAB", "BackSpace": "BACKSPACE",
    "Delete": "DELETE", "Insert": "INSERT", "Home": "HOME", "End": "END",
    "Prior": "PAGE_UP", "Next": "PAGE_DOWN", "Caps_Lock": "CAPS_LOCK",
    "Up": "UP", "Down": "DOWN", "Left": "LEFT", "Right": "RIGHT",
    "Control_L": "LEFT_CTRL", "Shift_L": "LEFT_SHIFT", "Alt_L": "LEFT_ALT",
    "Control_R": "RIGHT_CTRL", "Shift_R": "RIGHT_SHIFT", "Alt_R": "RIGHT_ALT",
    "F1": "F1", "F2": "F2", "F3": "F3", "F4": "F4", "F5": "F5", "F6": "F6",
    "F7": "F7", "F8": "F8", "F9": "F9", "F10": "F10", "F11": "F11", "F12": "F12",
}

def get_kc(sym, ch):
    s_l = sym.lower() if sym else ""
    
    if sym in TKS: return KEYS[TKS[sym]], TKS[sym]
    
    TKS_P = {
        "space": "SPACE", "minus": "MINUS", "equal": "EQUAL", "bracketleft": "LEFTBRACE",
        "bracketright": "RIGHTBRACE", "backslash": "BACKSLASH", "semicolon": "SEMICOLON",
        "apostrophe": "APOSTROPHE", "quoteright": "APOSTROPHE", "grave": "GRAVE",
        "quoteleft": "GRAVE", "comma": "COMMA", "period": "DOT", "slash": "SLASH"
    }
    if s_l in TKS_P: return KEYS[TKS_P[s_l]], TKS_P[s_l]
    if s_l in LETS: return LETS[s_l], s_l.upper()
    if sym in DIGS: return DIGS[sym], sym
    
    SH_S = {
        'exclam': '1', 'at': '2', 'numbersign': '3', 'dollar': '4', 'percent': '5',
        'asciicircum': '6', 'ampersand': '7', 'asterisk': '8', 'parenleft': '9',
        'parenright': '0', 'asciitilde': 'grave', 'underscore': 'minus', 'plus': 'equal',
        'braceleft': 'bracketleft', 'braceright': 'bracketright', 'bar': 'backslash',
        'colon': 'semicolon', 'quotedbl': 'apostrophe', 'less': 'comma',
        'greater': 'period', 'question': 'slash'
    }
    if s_l in SH_S:
        b = SH_S[s_l]
        if b in DIGS: return DIGS[b], b
        if b in TKS_P: return KEYS[TKS_P[b]], TKS_P[b]

    if ch in CHARS: return KEYS[CHARS[ch]], CHARS[ch]
    return None, None

def get_lbl(c):
    if c is None: return "—"
    mods = (c >> 8) & 0xFF
    kc = c & 0xFF
    
    lbls = []
    if mods & 0x01: lbls.append("CTRL")
    if mods & 0x02: lbls.append("SHIFT")
    if mods & 0x04: lbls.append("ALT")
    if mods & 0x08: lbls.append("GUI")
    
    base = "Unk"
    for n, v in KEYS.items():
        if v == kc: base = n; break
    if base == "Unk":
        for ch, v in LETS.items():
            if v == kc: base = ch.upper(); break
    if base == "Unk":
        for ch, v in DIGS.items():
            if v == kc: base = ch; break
    if base == "Unk" and kc != 0:
        base = f"0x{kc:02X}"
    elif base == "Unk":
        base = ""
        
    if mods and base:
        return "+".join(lbls) + "+" + base
    elif mods:
        return "+".join(lbls)
    elif base:
        return base
    return "—"

class SerWrk:
    def __init__(self, q):
        self.q = q
        self.s = None
        self.th = None
        self.stp = threading.Event()
        self.poll_th = threading.Thread(target=self._poll_ports, daemon=True)
        self.poll_th.start()

    def _poll_ports(self):
        import time
        last_ports = []
        while True:
            try:
                pts = self.prts()
                if pts != last_ports:
                    last_ports = pts
                    self.q.put(("ports", pts))
            except Exception:
                pass
            time.sleep(0.5)

    @staticmethod
    def prts():
        return [p.device for p in serial.tools.list_ports.comports()]

    def con(self, p):
        threading.Thread(target=self.c_wk, args=(p,), daemon=True).start()

    def c_wk(self, p):
        self.dcon()  # Ensure any existing connection is cleanly shut down first
        
        try:
            # Use a small timeout so closing the port doesn't block
            new_s = serial.Serial(p, baudrate=115200, timeout=0.05)
        except Exception as e:
            self.q.put(("st", f"ERR: {e}"))
            return

        self.s = new_s
        self.q.put(("st", "Connected"))
        self.stp.clear()
        
        # Pass the specific new_s object into the thread to isolate reads safely
        self.th = threading.Thread(target=self.r_lp, args=(new_s,), daemon=True)
        self.th.start()
        self.q_map()

    def r_lp(self, current_s):
        # We exclusively interact with `current_s` here instead of `self.s`
        buf = b""
        while not self.stp.is_set() and current_s.is_open:
            try:
                # Read max available bytes, or wait up to 0.05s
                r = current_s.read(max(1, current_s.in_waiting))
                if r:
                    buf += r
                    while b'\n' in buf:
                        line, buf = buf.split(b'\n', 1)
                        l = line.decode(errors="ignore").strip()
                        if l:
                            self.h_ln(l)
            except Exception:
                break # Exception happens if disconnected physically or via dcon() closing the port

    def h_ln(self, l):
        pts = l.split()
        if l.startswith("MAP ") and len(pts) == 4:
            try:
                self.q.put(("map", [int(pts[i], 16) for i in range(1, 4)]))
            except ValueError:
                pass
        elif l.startswith("OK ") and len(pts) == 3:
            try:
                self.q.put(("ack", int(pts[1])))
            except ValueError:
                pass
            self.q_map()
        elif l.startswith("ERR"):
            self.q.put(("st", f"ERR: {l}"))

    def w_key(self, idx, kc):
        if not self.s or not self.s.is_open:
            self.q.put(("st", "USB not connected"))
            self.q.put(("fail", idx))
            return
        try:
            self.s.write(f"SET {idx} {kc:04X}\n".encode())
        except Exception as e:
            self.q.put(("st", f"ERR: {e}"))
            self.q.put(("fail", idx))

    def q_map(self):
        if self.s and self.s.is_open:
            try:
                self.s.write(b"GET\n")
            except Exception:
                pass

    def dcon(self):
        self.stp.set()
        
        # Grab the current serial object and unbind it from the class instance
        # This prevents race conditions if dcon is called while rapidly connecting
        old_s = self.s
        self.s = None 
        
        if old_s and old_s.is_open:
            try:
                old_s.close()
            except Exception:
                pass

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Rebinder")
        self.geometry("420x280")
        ctk.set_appearance_mode("dark")

        self.q = queue.Queue()
        self.usb = SerWrk(self.q)

        self.cmap = [None, None, None]
        self.c_idx = None
        self.last_ports = [] # Keep track of seen ports

        self.stat = ctk.CTkLabel(self, text="Disconnected", font=("Segoe UI", 14))
        self.stat.pack(pady=(15, 5))

        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(pady=5, padx=20, fill="x")

        # Initialize ComboBox with ports or "Empty"
        init_ports = self.usb.prts()
        self.last_ports = init_ports
        display_vals = init_ports if init_ports else ["Empty"]
        
        self.cbo = ctk.CTkComboBox(f, values=display_vals, width=140)
        self.cbo.pack(side="left", padx=(0, 10))
        if not init_ports:
            self.cbo.set("Empty")
        else:
            self.cbo.set(init_ports[0])

        btn_f = ctk.CTkFrame(f, fg_color="transparent")
        btn_f.pack(side="left", expand=True, fill="x")

        self.b_con = ctk.CTkButton(btn_f, text="Connect", command=self.con, width=80)
        self.b_con.pack(side="left", padx=5)

        self.b_dcon = ctk.CTkButton(btn_f, text="Disconnect", command=self.dcon, width=80)
        self.b_dcon.pack(side="left", padx=5)

        self.rws = []
        for i in range(3):
            rf = ctk.CTkFrame(self)
            rf.pack(pady=5, padx=20, fill="x")

            lbl = ctk.CTkLabel(rf, text=f"Btn {i + 1}", font=("Segoe UI", 13))
            lbl.pack(side="left", padx=10)

            kl = ctk.CTkLabel(rf, text="—", font=("Segoe UI", 13, "bold"))
            kl.pack(side="left", padx=10)

            rb = ctk.CTkButton(rf, text="Rebind", command=lambda x=i: self.s_cap(x))
            rb.pack(side="right", padx=10)

            self.rws.append({"kl": kl, "b": rb})

        self.bind("<KeyPress>", self.k_prs)
        self.bind("<KeyRelease>", self.k_rel)
        
        # Start loops
        self.after(100, self.poll)

    def _update_ports(self, current_ports):
        """Called when the background thread detects a COM port change."""
        # Auto-disconnect if the currently connected port is unplugged
        active_port = self.usb.s.port if self.usb.s else None
        if active_port and active_port not in current_ports:
            if self.stat.cget("text") != "Disconnected":
                self.dcon()
        
        # Ports have changed
        display_vals = current_ports if current_ports else ["Empty"]
        self.cbo.configure(values=display_vals)
        
        # Find newly connected ports
        new_ports = [p for p in current_ports if p not in self.last_ports]
        if new_ports:
            # Select the new COM port automatically
            self.cbo.set(new_ports[0])
        elif not current_ports:
            # Set to Empty if everything was unplugged
            self.cbo.set("Empty")
        elif self.cbo.get() not in current_ports:
            # Current selected port vanished, fallback to first available
            self.cbo.set(current_ports[0])
            
        self.last_ports = current_ports

    def con(self):
        p = self.cbo.get().strip()
        if not p or p == "Empty":
            self.stat.configure(text="Select a valid COM port")
            return
        self.stat.configure(text="Connecting...")
        self.usb.con(p)

    def clear_binds(self):
        """Clears the displayed keybinds in the UI."""
        self.cmap = [None, None, None]
        for row in self.rws:
            row["kl"].configure(text="—")
            row["b"].configure(state="normal")
        self.c_idx = None

    def dcon(self):
        self.usb.dcon()
        self.stat.configure(text="Disconnected")
        self.clear_binds()

    def s_cap(self, i):
        self.c_idx = i
        self.rws[i]["kl"].configure(text="Press...")
        self.rws[i]["b"].configure(state="disabled")

    def k_prs(self, e):
        if self.c_idx is None:
            return

        st = e.state if isinstance(e.state, int) else 0
        mod = 0
        if st & 0x0004 or "Control" in e.keysym: mod |= 0x01
        if st & 0x0001 or "Shift" in e.keysym: mod |= 0x02
        if st & 0x0008 or st & 0x20000 or "Alt" in e.keysym: mod |= 0x04
        if "Win" in e.keysym or "Super" in e.keysym: mod |= 0x08

        is_mod = any(m in e.keysym for m in ["Control", "Shift", "Alt", "Win", "Super"])
        
        if is_mod:
            temp_kc = (mod << 8)
            self.rws[self.c_idx]["kl"].configure(text=get_lbl(temp_kc) + "+...")
            return

        kc, l = get_kc(e.keysym, e.char)
        if kc is None:
            self.rws[self.c_idx]["kl"].configure(text="Unsup")
            self.rws[self.c_idx]["b"].configure(state="normal")
            self.c_idx = None
            return

        final_kc = (mod << 8) | kc
        i = self.c_idx
        self.c_idx = None
        self.rws[i]["b"].configure(state="normal")
        self.rws[i]["kl"].configure(text=f"{get_lbl(final_kc)} (...)")
        self.usb.w_key(i, final_kc)

    def k_rel(self, e):
        if self.c_idx is None:
            return
        is_mod = any(m in e.keysym for m in ["Control", "Shift", "Alt", "Win", "Super"])
        if is_mod:
            mc = 0
            if "Control" in e.keysym: mc = 0xE0
            elif "Shift" in e.keysym: mc = 0xE1
            elif "Alt" in e.keysym: mc = 0xE2
            elif "Win" in e.keysym or "Super" in e.keysym: mc = 0xE3
            
            if mc:
                i = self.c_idx
                self.c_idx = None
                self.rws[i]["b"].configure(state="normal")
                self.rws[i]["kl"].configure(text=f"{get_lbl(mc)} (...")
                self.usb.w_key(i, mc)

    def poll(self):
        try:
            while True:
                k, p = self.q.get_nowait()
                if k == "st":
                    self.stat.configure(text=p)
                elif k == "ports":
                    self._update_ports(p)
                elif k == "map":
                    self.cmap = p
                    for i, c in enumerate(p):
                        self.rws[i]["kl"].configure(text=get_lbl(c))
                elif k == "fail":
                    cl = get_lbl(self.cmap[p]) if self.cmap[p] is not None else "—"
                    self.rws[p]["kl"].configure(text=cl)
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def cls(self):
        self.usb.dcon()
        self.destroy()

if __name__ == "__main__":
    a = App()
    a.protocol("WM_DELETE_WINDOW", a.cls)
    a.mainloop()