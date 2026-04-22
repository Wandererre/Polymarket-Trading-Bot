import tkinter as tk
import websocket
import requests
import json
import threading
import time
from collections import deque

class TrinityUltimate:
    def __init__(self, root):
        self.root = root
        self.root.title("TRINITY COMMAND CENTER")
        self.root.geometry("400x500") # Wider for dual view
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#050505")

        # --- SETTINGS ---
        self.SWARM_WINDOW = 3.0       
        self.SCAN_RANGE = 500.0       # Scan deep, let logic filter
        self.ICEBERG_THRESHOLD = 5.0  

        # --- STATE ---
        self.trades = deque() 
        self.best_bid = 0.0
        self.best_ask = 0.0
        self.bid_vol_absorbed = 0.0
        self.ask_vol_absorbed = 0.0
        self.bid_visible = 1.0
        self.ask_visible = 1.0

        # --- UI LAYOUT ---

        # 1. SWARM (Full Width)
        tk.Label(root, text="MARKET SWARM (Aggression)", fg="#444", bg="#050505", font=("Arial", 8, "bold")).pack(pady=(10, 0))
        self.lbl_swarm_idx = tk.Label(root, text="0.00", fg="#444", bg="#050505", font=("Arial", 35, "bold"))
        self.lbl_swarm_idx.pack()

        tk.Frame(root, height=1, bg="#222").pack(fill="x", padx=10, pady=5)

        # 2. DUAL MAGNETS (Split View)
        # Container
        mag_frame = tk.Frame(root, bg="#050505")
        mag_frame.pack(fill="x", padx=5)

        # LEFT: SMART (Gravity)
        frame_smart = tk.Frame(mag_frame, bg="#050505", width=190)
        frame_smart.pack(side="left", fill="y", expand=True)
        tk.Label(frame_smart, text="⚡ PROXIMITY (Gravity)", fg="#666", bg="#050505", font=("Arial", 7)).pack()
        
        self.lbl_smart_up = tk.Label(frame_smart, text="$00,000", fg="#ff3333", bg="#050505", font=("Arial", 14, "bold"))
        self.lbl_smart_up.pack(pady=(2,0))
        self.lbl_smart_up_d = tk.Label(frame_smart, text="Vol:0", fg="#555", bg="#050505", font=("Courier", 8))
        self.lbl_smart_up_d.pack()

        self.lbl_smart_down = tk.Label(frame_smart, text="$00,000", fg="#00ff00", bg="#050505", font=("Arial", 14, "bold"))
        self.lbl_smart_down.pack(pady=(5,0))
        self.lbl_smart_down_d = tk.Label(frame_smart, text="Vol:0", fg="#555", bg="#050505", font=("Courier", 8))
        self.lbl_smart_down_d.pack()

        # Divider
        tk.Frame(mag_frame, width=1, bg="#222").pack(side="left", fill="y", padx=5)

        # RIGHT: STABLE (Massive)
        frame_stable = tk.Frame(mag_frame, bg="#050505", width=190)
        frame_stable.pack(side="right", fill="y", expand=True)
        tk.Label(frame_stable, text="🧱 MASSIVE (Volume)", fg="#666", bg="#050505", font=("Arial", 7)).pack()

        self.lbl_stable_up = tk.Label(frame_stable, text="$00,000", fg="#ff3333", bg="#050505", font=("Arial", 14, "bold"))
        self.lbl_stable_up.pack(pady=(2,0))
        self.lbl_stable_up_d = tk.Label(frame_stable, text="Vol:0", fg="#555", bg="#050505", font=("Courier", 8))
        self.lbl_stable_up_d.pack()

        self.lbl_stable_down = tk.Label(frame_stable, text="$00,000", fg="#00ff00", bg="#050505", font=("Arial", 14, "bold"))
        self.lbl_stable_down.pack(pady=(5,0))
        self.lbl_stable_down_d = tk.Label(frame_stable, text="Vol:0", fg="#555", bg="#050505", font=("Courier", 8))
        self.lbl_stable_down_d.pack()

        tk.Frame(root, height=1, bg="#222").pack(fill="x", padx=10, pady=10)

        # 3. ICEBERGS (Full Width)
        tk.Label(root, text="HIDDEN VOLUME", fg="#444", bg="#050505", font=("Arial", 8, "bold")).pack()
        
        self.lbl_ice_ask = tk.Label(root, text="ASK: 1.0x", fg="#444", bg="#050505", font=("Courier", 12, "bold"))
        self.lbl_ice_ask.pack()
        self.lbl_ice_bid = tk.Label(root, text="BID: 1.0x", fg="#444", bg="#050505", font=("Courier", 12, "bold"))
        self.lbl_ice_bid.pack(pady=(0, 5))

        # Status
        self.lbl_status = tk.Label(root, text="SYSTEM ACTIVE", fg="#00ff00", bg="#050505", font=("Arial", 6))
        self.lbl_status.pack(side="bottom")

        # --- ENGINES ---
        threading.Thread(target=self.engine_swarm, daemon=True).start()
        threading.Thread(target=self.engine_magnets_dual, daemon=True).start()
        threading.Thread(target=self.engine_iceberg_trades, daemon=True).start()
        threading.Thread(target=self.engine_iceberg_depth, daemon=True).start()
        
        self.update_ui()

    def update_ui(self):
        # SWARM
        now = time.time()
        while self.trades and self.trades[0][0] < (now - self.SWARM_WINDOW):
            self.trades.popleft()
        buy_cnt = sum(1 for t in self.trades if not t[1])
        sell_cnt = sum(1 for t in self.trades if t[1])
        total = buy_cnt + sell_cnt
        score = 0.0
        if total > 0:
            raw = (buy_cnt - sell_cnt) / self.SWARM_WINDOW
            score = raw / 20.0
            if score > 1.0: score = 1.0
            if score < -1.0: score = -1.0
        
        s_clr = "#444"
        if score > 0.4: s_clr = "#00ff00"
        elif score < -0.4: s_clr = "#ff0033"
        self.lbl_swarm_idx.config(text=f"{score:+.2f}", fg=s_clr)

        # ICEBERG
        ask_ratio = self.ask_vol_absorbed / self.ask_visible if self.ask_visible > 0 else 0
        a_txt = f"ASK: {ask_ratio:.1f}x"; a_clr = "#444"
        if ask_ratio > self.ICEBERG_THRESHOLD: a_clr = "#ff3333"
        
        bid_ratio = self.bid_vol_absorbed / self.bid_visible if self.bid_visible > 0 else 0
        b_txt = f"BID: {bid_ratio:.1f}x"; b_clr = "#444"
        if bid_ratio > self.ICEBERG_THRESHOLD: b_clr = "#00ff00"
            
        self.lbl_ice_ask.config(text=a_txt, fg=a_clr)
        self.lbl_ice_bid.config(text=b_txt, fg=b_clr)
        self.root.after(100, self.update_ui)

    def engine_swarm(self):
        def on_msg(ws, message):
            try:
                data = json.loads(message)
                self.trades.append((time.time(), data['m']))
            except: pass
        while True:
            try:
                ws = websocket.WebSocketApp("wss://stream.binance.com:9443/ws/btcusdt@aggTrade", on_message=on_msg)
                ws.run_forever()
            except: pass
            time.sleep(1)

    # --- DUAL MAGNET ENGINE ---
    def engine_magnets_dual(self):
        while True:
            try:
                url = "https://api.binance.com/api/v3/depth?symbol=BTCUSDT&limit=1000"
                data = requests.get(url, timeout=2).json()
                bids = [[float(x[0]), float(x[1])] for x in data['bids']]
                asks = [[float(x[0]), float(x[1])] for x in data['asks']]
                price = (bids[0][0] + asks[0][0]) / 2

                # INIT VARS
                smart_ask_s = -1; smart_ask_p = 0; smart_ask_v = 0
                stable_ask_v = -1; stable_ask_p = 0
                
                smart_bid_s = -1; smart_bid_p = 0; smart_bid_v = 0
                stable_bid_v = -1; stable_bid_p = 0

                # SCAN ASKS (UP)
                for p, v in asks:
                    dist = p - price
                    if dist > self.SCAN_RANGE: break
                    
                    # STABLE LOGIC (Max Vol)
                    if v > stable_ask_v: stable_ask_v = v; stable_ask_p = p
                    
                    # SMART LOGIC (Gravity)
                    if v > 1.0: # Ignore noise
                        score = v / (dist + 1.0)
                        if score > smart_ask_s: smart_ask_s = score; smart_ask_p = p; smart_ask_v = v

                # SCAN BIDS (DOWN)
                for p, v in bids:
                    dist = price - p
                    if dist > self.SCAN_RANGE: break
                    
                    # STABLE LOGIC
                    if v > stable_bid_v: stable_bid_v = v; stable_bid_p = p
                    
                    # SMART LOGIC
                    if v > 1.0:
                        score = v / (dist + 1.0)
                        if score > smart_bid_s: smart_bid_s = score; smart_bid_p = p; smart_bid_v = v

                # UPDATE UI (Thread safe-ish)
                # Smart (Left)
                self.lbl_smart_up.config(text=f"${smart_ask_p:,.0f}")
                self.lbl_smart_up_d.config(text=f"Vol:{smart_ask_v:.0f}")
                self.lbl_smart_down.config(text=f"${smart_bid_p:,.0f}")
                self.lbl_smart_down_d.config(text=f"Vol:{smart_bid_v:.0f}")

                # Stable (Right)
                self.lbl_stable_up.config(text=f"${stable_ask_p:,.0f}")
                self.lbl_stable_up_d.config(text=f"Vol:{stable_ask_v:.0f}")
                self.lbl_stable_down.config(text=f"${stable_bid_p:,.0f}")
                self.lbl_stable_down_d.config(text=f"Vol:{stable_bid_v:.0f}")

            except: pass
            time.sleep(1)

    def engine_iceberg_depth(self):
        def on_msg(ws, message):
            try:
                data = json.loads(message)
                new_bid = float(data['b']); new_ask = float(data['a'])
                if new_bid != self.best_bid: self.best_bid = new_bid; self.bid_vol_absorbed = 0.0
                if new_ask != self.best_ask: self.best_ask = new_ask; self.ask_vol_absorbed = 0.0
                self.bid_visible = float(data['B']); self.ask_visible = float(data['A'])
            except: pass
        while True:
            try:
                ws = websocket.WebSocketApp("wss://stream.binance.com:9443/ws/btcusdt@bookTicker", on_message=on_msg)
                ws.run_forever()
            except: pass
            time.sleep(1)

    def engine_iceberg_trades(self):
        def on_msg(ws, message):
            try:
                data = json.loads(message)
                p = float(data['p']); q = float(data['q']); is_sell = data['m']
                if is_sell: 
                    if abs(p - self.best_bid) < 1.0: self.bid_vol_absorbed += q
                else: 
                    if abs(p - self.best_ask) < 1.0: self.ask_vol_absorbed += q
            except: pass
        while True:
            try:
                ws = websocket.WebSocketApp("wss://stream.binance.com:9443/ws/btcusdt@trade", on_message=on_msg)
                ws.run_forever()
            except: pass
            time.sleep(1)

if __name__ == "__main__":
    root = tk.Tk()
    app = TrinityUltimate(root)
    root.mainloop()