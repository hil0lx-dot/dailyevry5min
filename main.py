import os, json, time, threading, websocket, requests, random
from flask import Flask

app = Flask('')
@app.route('/')
def home(): return "🛰️ Sentinel True-Random: Active"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- CONFIG ---
GUILD_ID = "777271906486976512"
VC_ONE_ID = "1494048330379034674"
VC_TWO_ID = "1489088008576700466"
VC_THREE_ID = "1388555164708900955"

tokens = {
    "Sentinel-1": {"token": os.getenv("TOKEN_ONE"), "channel": VC_ONE_ID, "mobile": False, "spam": True},
    "Sentinel-2": {"token": os.getenv("TOKEN_TWO"), "channel": VC_TWO_ID, "mobile": False, "spam": False},
    "Sentinel-3": {"token": os.getenv("TOKEN_THREE"), "channel": VC_THREE_ID, "mobile": True, "spam": False}
}

def daily_spammer():
    token = tokens["Sentinel-1"]["token"]
    if not token: return
    header = {"Authorization": token.strip()}
    while True:
        try:
            requests.post(f"https://discord.com/api/v9/channels/{VC_ONE_ID}/messages",
                          headers=header, json={"content": "daily"})
            time.sleep(300) 
        except: time.sleep(10)

def vc_locker(token, channel_id, name, is_mobile):
    if not token: return

    while True:
        try:
            ws = websocket.WebSocket()
            ws.connect('wss://gateway.discord.gg/?v=9&encoding=json', timeout=15)
            
            properties = {
                "$os": "android" if is_mobile else "windows",
                "$browser": "Discord Android" if is_mobile else "Chrome",
                "$device": "phone" if is_mobile else "pc"
            }

            ws.send(json.dumps({
                "op": 2, 
                "d": {
                    "token": token.strip(), 
                    "properties": properties,
                    "presence": {"status": "online", "afk": False}
                }
            }))

            join_payload = {
                "op": 4, "d": {
                    "guild_id": GUILD_ID, "channel_id": channel_id,
                    "self_mute": True, "self_deaf": True,
                    "self_video": False, "self_stream": not is_mobile
                }
            }

            last_heartbeat = 0
            
            while True:
                msg = ws.recv()
                if not msg: break
                data = json.loads(msg)
                
                if data.get('op') == 10:
                    ws.send(json.dumps(join_payload))

                if time.time() - last_heartbeat > 30:
                    # --- THE CHANCE TO DISCONNECT ---
                    # 1 in 150 chance every 30 seconds (~ once every 75 minutes on average)
                    if random.randint(1, 150) == 7:
                        print(f"🎲 {name}: Random disconnect triggered for wavy line.")
                        break # Breaks the loop to disconnect
                    
                    ws.send(json.dumps({"op": 1, "d": data.get('s')}))
                    last_heartbeat = time.time()

            ws.close()
            # Wait a random 7 minutes (approx 420 seconds)
            time.sleep(random.randint(400, 480))

        except:
            time.sleep(20)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    for name, data in tokens.items():
        if data["token"]:
            threading.Thread(target=vc_locker, args=(data["token"], data["channel"], name, data["mobile"])).start()
            if data["spam"]:
                threading.Thread(target=daily_spammer, daemon=True).start()
            time.sleep(random.randint(5, 15))
    while True: time.sleep(1)
        
