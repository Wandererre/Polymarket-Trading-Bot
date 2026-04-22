import tkinter as tk
import requests
import threading
import time
import json
import websocket
import re
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs

# --- 1. CREDENTIALS ---
PRIVATE_KEY = "97ecfab9e45a1f9607410d73ab983286758ae6f2099ee32f8d8e65b1f33ac46a"      
FUNDER_ADDRESS = "0x7EE5a6B7498b8005973E0695009BC536c00D0021"   
SIG_TYPE = 2               
HOST = "https://clob.polymarket.com"

class PureSniper:
    def __init__(self, root):
        self.root = root
        self.root.title("Sniper")
        self.root.geometry("340x500") # Expanded slightly for the message log
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#050505")

        self.up_id = None
        self.down_id = None
        
        self.inventory_up = 0.0
        self.inventory_down = 0.0
        self.dynamic_fee = 0.02 # Safe fallback
        
        # UI Variables
        self.binance_str = "$0.00"
        self.target_str = "TARGET: SEARCHING..."
        self.timer_str = "00:00"
        self.timer_color = "#ffffff"
        self.status_str = "Status: Disarmed"
        self.status_color = "#888888"
        self.msg_str = "System: Waiting for orders..."

        # --- API INIT ---
        try:
            self.client = ClobClient(HOST, key=PRIVATE_KEY, chain_id=137, signature_type=SIG_TYPE, funder=FUNDER_ADDRESS)
            self.client.set_api_creds(self.client.create_or_derive_api_creds())
            print(">>> CLOB API CONNECTED")
        except Exception as e:
            pass

        # --- UI BUILD ---
        tk.Label(root, text="BINANCE LIVE", fg="#888888", bg="#050505", font=("Arial", 9)).pack(pady=(15, 0))
        self.lbl_binance = tk.Label(root, text=self.binance_str, fg="#f3ba2f", bg="#050505", font=("Arial", 28, "bold"))
        self.lbl_binance.pack()

        self.lbl_target = tk.Label(root, text=self.target_str, fg="#00ffff", bg="#050505", font=("Arial", 16, "bold"))
        self.lbl_target.pack(pady=(5, 5))

        self.lbl_timer = tk.Label(root, text=self.timer_str, fg="#ffffff", bg="#050505", font=("Courier", 45, "bold"))
        self.lbl_timer.pack(pady=5)

        self.lbl_status = tk.Label(root, text=self.status_str, fg=self.status_color, bg="#050505", font=("Arial", 10, "bold"))
        self.lbl_status.pack(pady=(0, 10))

        btn_frame = tk.Frame(root, bg="#050505")
        btn_frame.pack(fill="x", padx=15, pady=5)

        self.btn_up = tk.Button(btn_frame, text=" BUY UP ($1)", bg="#27ae60", fg="white", font=("Arial", 14, "bold"), height=2, command=lambda: self.execute("BUY", self.up_id))
        self.btn_up.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_down = tk.Button(btn_frame, text=" BUY DOWN ($1)", bg="#c0392b", fg="white", font=("Arial", 14, "bold"), height=2, command=lambda: self.execute("BUY", self.down_id))
        self.btn_down.pack(side="right", fill="x", expand=True, padx=(5, 0))

        tk.Button(root, text=" PANIC SELL ALL", bg="#f1c40f", fg="black", font=("Arial", 12, "bold"), height=2, command=self.panic).pack(fill="x", padx=15, pady=10)

        # Execution Log UI
        self.lbl_msg = tk.Label(root, text=self.msg_str, fg="#f39c12", bg="#111111", font=("Courier", 9), height=2, wraplength=300)
        self.lbl_msg.pack(fill="x", padx=15, pady=(0, 10))

        # --- ENGINES ---
        threading.Thread(target=self.engine_binance, daemon=True).start()
        threading.Thread(target=self.engine_shifter, daemon=True).start()
        threading.Thread(target=self.engine_target, daemon=True).start()
        threading.Thread(target=self.engine_timer, daemon=True).start()

        self.safe_ui_loop()

    def safe_ui_loop(self):
        self.lbl_binance.config(text=self.binance_str)
        self.lbl_target.config(text=self.target_str)
        self.lbl_timer.config(text=self.timer_str, fg=self.timer_color)
        self.lbl_status.config(text=self.status_str, fg=self.status_color)
        self.lbl_msg.config(text=self.msg_str)
        self.root.after(50, self.safe_ui_loop)

    def engine_binance(self):
        def on_msg(ws, message):
            data = json.loads(message)
            self.binance_str = f"${float(data['p']):,.2f}"
        while True:
            try:
                ws = websocket.WebSocketApp("wss://stream.binance.com:9443/ws/btcusdt@trade", on_message=on_msg)
                ws.run_forever()
            except: pass
            time.sleep(1)

    def engine_target(self):
        while True:
            if self.up_id: 
                try:
                    url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=1"
                    resp = requests.get(url, timeout=3).json()
                    open_price = float(resp[0][1]) 
                    self.target_str = f"TARGET: ${open_price:,.2f}"
                except: pass
            else:
                self.target_str = "TARGET: WAITING..."
            time.sleep(2)

    def engine_shifter(self):
        while True:
            try:
                now = int(time.time())
                current_ts = (now // 300) * 300
                exact_slug = f"btc-updown-5m-{current_ts}"
                url = f"https://gamma-api.polymarket.com/events?slug={exact_slug}"
                
                resp = requests.get(url).json()
                
                if resp and len(resp) > 0:
                    event = resp[0]
                    if 'markets' in event and len(event['markets']) > 0:
                        m = event['markets'][0]
                        
                        # NO MORE GUESSING: Grab dynamic fee directly from the API
                        self.dynamic_fee = float(m.get('takerFee', 0.02))
                        
                        raw_tokens = m.get('clobTokenIds', [])
                        if isinstance(raw_tokens, str):
                            try: raw_tokens = json.loads(raw_tokens)
                            except: pass

                        outcomes = m.get('outcomes', [])
                        if isinstance(outcomes, str):
                            try: outcomes = json.loads(outcomes)
                            except: pass

                        up_index = outcomes.index('Up') if 'Up' in outcomes else 0
                        down_index = outcomes.index('Down') if 'Down' in outcomes else 1
                        
                        if len(raw_tokens) > max(up_index, down_index):
                            self.up_id = raw_tokens[up_index]
                            self.down_id = raw_tokens[down_index]
                        
                        rem = 300 - (now % 300)
                        self.status_str = f"Status: ARMED & LOCKED ({rem}s left)"
                        self.status_color = "#00ffcc"
                else:
                    self.up_id, self.down_id = None, None
                    self.status_str = f"Waiting on Gamma API: {exact_slug}"
                    self.status_color = "#888888"
            except Exception as e:
                pass
            time.sleep(0.5) 

    def engine_timer(self):
        while True:
            now = int(time.time())
            rem = 300 - (now % 300)
            self.timer_str = f"{rem//60:02d}:{rem%60:02d}"
            self.timer_color = "#ff3333" if rem < 15 else "#ffffff"
            time.sleep(1)

    def execute(self, side, token_id):
        if not token_id: 
            self.msg_str = " Error: No market locked."
            return
        threading.Thread(target=self._post, args=(side, token_id), daemon=True).start()

    def _post(self, side, token_id):
        try:
            current_price = 0.0
            if side == "BUY":
                try:
                    p_resp = self.client.get_price(token_id, side="BUY")
                    current_price = float(p_resp.get('price') if isinstance(p_resp, dict) else p_resp)
                except: current_price = 0.50 
                if current_price <= 0: current_price = 0.01
                
                order_size = round(1.00 / current_price, 2)
                if order_size * current_price < 1.00: 
                    order_size = round(order_size + 0.01, 2)
                    
                exec_price = 0.99 
            else: 
                order_size = self.inventory_up if token_id == self.up_id else self.inventory_down
                if order_size <= 0: return
                exec_price = 0.01 
                
            order = OrderArgs(price=exec_price, size=order_size, side=side, token_id=token_id)
            self.client.create_and_post_order(order)
            
            if side == "BUY":
                # PROPER QUANTS ACCOUNT FOR SLIPPAGE: Apply the exact fee and aggressively round DOWN to leave dust instead of failing
                filled_shares = order_size * (1.0 - self.dynamic_fee)
                safe_inventory = int(filled_shares * 100) / 100.0 
                
                if token_id == self.up_id: self.inventory_up += safe_inventory
                if token_id == self.down_id: self.inventory_down += safe_inventory
                
                self.msg_str = f" BOUGHT {order_size} shares @ ~${current_price:.2f}"
            else:
                if token_id == self.up_id: self.inventory_up = 0.0
                if token_id == self.down_id: self.inventory_down = 0.0
                self.msg_str = f" SOLD {order_size} shares @ Market"
            
        except Exception as e: 
            self.msg_str = f" {side} FAILED: {str(e)[:40]}"

    def panic(self):
        self.msg_str = " INITIATING PANIC DUMP..."
        if self.up_id: self.execute("SELL", self.up_id)
        time.sleep(0.2) 
        if self.down_id: self.execute("SELL", self.down_id)

if __name__ == "__main__":
    root = tk.Tk()
    app = PureSniper(root)
    root.mainloop()