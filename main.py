import os, json, time, threading, websocket, requests
from flask import Flask

# --- FLASK WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "🛰️ Triple-Sentinel Multi-VC: Active"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURATION ---
GUILD_ID = "777271906486976512"

# SENTINEL 1: Token 1 (Daily Spam + VC Lock)
VC_ONE_ID = "1494048330379034674"
TOKEN_ONE = os.getenv("TOKEN_ONE")

# SENTINEL 2: Token 2 (Silent Lock)
VC_TWO_ID = "1487672527370322132"
TOKEN_TWO = os.getenv("TOKEN_TWO")

# SENTINEL 3: Token 3 (Silent Lock - New Channel)
VC_THREE_ID = "1489292284322381956"
TOKEN_THREE = os.getenv("TOKEN_THREE")

# --- DAILY SPAMMER (Only for Token 1) ---
def daily_spammer():
    if not TOKEN_ONE: return
    header = {"Authorization": TOKEN_ONE.strip()}
    while True:
        try:
            requests.post(f"https://discord.com/api/v9/channels/{VC_ONE_ID}/messages",
                          headers=header, json={"content": "daily"})
            time.sleep(300) # 5 minutes
        except: time.sleep(10)

# --- MAIN VC LOCKER FUNCTION ---
def vc_locker(token, channel_id, name, is_mute, is_deaf, send_video):
    if not token:
        print(f"⚠️ {name} token missing. Skipping...")
        return

    while True:
        try:
            ws = websocket.WebSocket()
            ws.connect('wss://gateway.discord.gg/?v=9&encoding=json', timeout=15)
            
            # Identify
            ws.send(json.dumps({
                "op": 2, 
                "d": {
                    "token": token.strip(), 
                    "properties": {"$os": "windows", "$browser": "Chrome", "$device": ""},
                    "presence": {"status": "online", "afk": False}
                }
            }))

            join_payload = {
                "op": 4, 
                "d": {
                    "guild_id": GUILD_ID, 
                    "channel_id": channel_id,
                    "self_mute": is_mute, 
                    "self_deaf": is_deaf,
                    "self_video": send_video,
                    "self_stream": send_video
                }
            }

            last_heartbeat = 0
            user_id = None

            while True:
                msg = ws.recv()
                if not msg: break
                data = json.loads(msg)
                
                if data.get('op') == 10:
                    ws.send(json.dumps(join_payload))

                if data.get('t') == "READY":
                    user_id = data['d']['user']['id']
                    print(f"✅ {name} locked in VC: {channel_id}")

                # Rejoin if moved/kicked
                if data.get('t') == "VOICE_STATE_UPDATE":
                    if data['d'].get('user_id') == user_id:
                        if data['d'].get('channel_id') != channel_id:
                            time.sleep(3)
                            ws.send(json.dumps(join_payload))

                # Heartbeat & Refresh
                if time.time() - last_heartbeat > 30:
                    ws.send(json.dumps({"op": 1, "d": data.get('s')}))
                    ws.send(json.dumps(join_payload)) 
                    last_heartbeat = time.time()
        except:
            time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    
    # Sentinel 1: Daily Chat, No Mute, Video ON
    threading.Thread(target=vc_locker, args=(TOKEN_ONE, VC_ONE_ID, "Sentinel-1", False, False, True)).start()
    threading.Thread(target=daily_spammer, daemon=True).start()
    
    # Sentinel 2: Silent, Muted, Deafened, Video OFF
    threading.Thread(target=vc_locker, args=(TOKEN_TWO, VC_TWO_ID, "Sentinel-2", True, True, False)).start()
    
    # Sentinel 3: Silent, Muted, Deafened, Video OFF (New Channel)
    threading.Thread(target=vc_locker, args=(TOKEN_THREE, VC_THREE_ID, "Sentinel-3", True, True, False)).start()
    
    while True: time.sleep(1)
        
