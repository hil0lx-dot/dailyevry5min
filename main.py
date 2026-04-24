import os, json, time, threading, websocket, requests
from flask import Flask

# --- FLASK WEB SERVER (For Railway Persistence) ---
app = Flask('')
@app.route('/')
def home(): return "🛰️ Sentinel Dual-Lock: Active"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- CONFIG ---
GUILD_ID = os.getenv("GUILD")
CHANNEL_ID = os.getenv("CHANNEL")

# Token Dictionary
tokens = {
    "Sentinel 1": os.getenv("TOKEN_ONE"),
    "Sentinel 2": os.getenv("TOKEN_TWO")
}

# --- 2-HOUR MESSAGE FUNCTION (FOR BOTH ACCOUNTS) ---
def send_periodic_msg(token, name):
    while True:
        if token:
            url = f"https://discord.com/api/v9/channels/{CHANNEL_ID}/messages"
            headers = {"Authorization": token.strip(), "Content-Type": "application/json"}
            payload = {"content": "d"}
            try:
                res = requests.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    print(f"📅 Message 'd' sent by {name}.")
                else:
                    print(f"⚠️ {name} failed to send message: {res.text}")
            except Exception as e:
                print(f"⚠️ {name} message error: {e}")
        
        # Wait 5 min (300 seconds)
        time.sleep(300) 

def vc_locker(token, name):
    if not token:
        print(f"⚠️ {name} token missing.")
        return

    while True:
        try:
            ws = websocket.WebSocket()
            ws.connect('wss://gateway.discord.gg/?v=9&encoding=json', timeout=15)
            
            # 1. IDENTIFY (No Playing Status)
            ws.send(json.dumps({
                "op": 2, 
                "d": {
                    "token": token.strip(), 
                    "properties": {"$os": "windows", "$browser": "Chrome", "$device": ""},
                    "presence": {
                        "status": "online", 
                        "afk": False,
                        "activities": [] # Deleted playing status
                    }
                }
            }))

            # JOIN PAYLOAD
            join_payload = {
                "op": 4, 
                "d": {
                    "guild_id": GUILD_ID, 
                    "channel_id": CHANNEL_ID,
                    "self_mute": True, 
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
                    print(f"✅ {name} connected as {d['user']['username']}")

                if t == "VOICE_STATE_UPDATE":
                    if d.get('user_id') == user_id:
                        if d.get('channel_id') != CHANNEL_ID:
                            print(f"🔄 {name} rejoining in 1s...")
                            time.sleep(1)
                            ws.send(json.dumps(join_payload))

