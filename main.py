import os, json, time, threading, websocket, requests
from flask import Flask

# --- FLASK WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "🛰️ Sentinel Single-Lock: Active"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- CONFIG ---
GUILD_ID = "777271906486976512"
CHANNEL_ID = "1494048330379034674" # New VC Channel ID
TOKEN = os.getenv("TOKEN_ONE")

# --- DAILY SPAMMER (Every 5 Minutes) ---
def daily_spammer():
    if not TOKEN: return
    header = {"Authorization": TOKEN.strip()}
    payload = {"content": "daily"}
    
    while True:
        try:
            # Sending "daily" to the same VC channel
            res = requests.post(
                f"https://discord.com/api/v9/channels/{CHANNEL_ID}/messages",
                headers=header, json=payload
            )
            # If rate limited, wait the required time, otherwise wait 5 minutes
            if res.status_code == 429:
                wait = res.json().get('retry_after', 5)
                time.sleep(wait)
            else:
                time.sleep(300) # 300 seconds = 5 minutes
        except Exception:
            time.sleep(10)

# --- VC LOCK & STATUS ---
def vc_locker():
    if not TOKEN:
        print("⚠️ TOKEN_ONE missing.")
        return

    while True:
        try:
            ws = websocket.WebSocket()
            ws.connect('wss://gateway.discord.gg/?v=9&encoding=json', timeout=15)
            
            # 1. IDENTIFY
            ws.send(json.dumps({
                "op": 2, 
                "d": {
                    "token": TOKEN.strip(), 
                    "properties": {"$os": "windows", "$browser": "Chrome", "$device": ""},
                    "presence": {"status": "online", "afk": False}
                }
            }))

            join_payload = {
                "op": 4, 
                "d": {
                    "guild_id": GUILD_ID, 
                    "channel_id": CHANNEL_ID,
                    "self_mute": False, 
                    "self_deaf": False,
                    "self_video": False,
                    "self_stream": True
                }
            }

            last_heartbeat = 0
            user_id = None

            while True:
                msg = ws.recv()
                if not msg: break
                data = json.loads(msg)
                
                op = data.get('op')
                t = data.get('t')
                d = data.get('d')

                if op == 10:
                    ws.send(json.dumps(join_payload))

                if t == "READY":
                    user_id = d['user']['id']
                    print(f"✅ Sentinel ['user'] connected to {CHANNEL_ID}")

                # REJOIN LOGIC (3s delay)
                if t == "VOICE_STATE_UPDATE":
                    if d.get('user_id') == user_id:
                        if d.get('channel_id') != CHANNEL_ID:
                            time.sleep(3)
                            ws.send(json.dumps(join_payload))

                # HEARTBEAT & ICON REFRESH
                if time.time() - last_heartbeat > 30:
                    ws.send(json.dumps({"op": 1, "d": data.get('s')}))
                    ws.send(json.dumps(join_payload)) 
                    last_heartbeat = time.time()

        except Exception as e:
            print(f"⚠️ Connection error: {e}. Reconnecting...")
            time.sleep(10)

if __name__ == "__main__":
    # Start the web server
    threading.Thread(target=run_web, daemon=True).start()
    
    # Start the Daily Spammer thread
    threading.Thread(target=daily_spammer, daemon=True).start()
    
    # Start the VC Locker
    vc_locker()
