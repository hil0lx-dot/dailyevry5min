import os, json, time, threading, websocket, requests, random
from flask import Flask

app = Flask('')
@app.route('/')
def home(): return "🛰️ Sentinel Smooth-Wavy: Active"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURATION ---
GUILD_ID = "777271906486976512"

# SENTINEL 1: Token 1 (Daily Spam + VC Lock)
VC_ONE_ID = "1494048330379034674"
TOKEN_ONE = os.getenv("TOKEN_ONE")

# SENTINEL 2: Token 2 (Silent Lock - UPDATED CHANNEL)
VC_TWO_ID = "1465180321124454486"
TOKEN_TWO = os.getenv("TOKEN_TWO")

# SENTINEL 3: Token 3 (Mobile Status + VC Lock)
VC_THREE_ID = "1388555164708900955"
TOKEN_THREE = os.getenv("TOKEN_THREE")

tokens = {
    "Sentinel-1": {"token": TOKEN_ONE, "channel": VC_ONE_ID, "mobile": False, "spam": True},
    "Sentinel-2": {"token": TOKEN_TWO, "channel": VC_TWO_ID, "mobile": False, "spam": False},
    "Sentinel-3": {"token": TOKEN_THREE, "channel": VC_THREE_ID, "mobile": True, "spam": False}
}

# --- DAILY SPAMMER (Only for Token 1) ---
def daily_spammer():
    if not TOKEN_ONE: return
    header = {"Authorization": TOKEN_ONE.strip()}
    while True:
        try:
            requests.post(f"https://discord.com/api/v9/channels/{VC_ONE_ID}/messages",
                          headers=header, json={"content": "daily"})
            time.sleep(300) 
        except: time.sleep(10)

# --- MAIN VC LOCKER FUNCTION ---
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
            last_dice_roll = 0
            
            while True:
                msg = ws.recv()
                if not msg: break
                data = json.loads(msg)
                
                if data.get('op') == 10:
                    ws.send(json.dumps(join_payload))

                # Dice roll for "Wavy Line" (Check every 60s, 1 in 400 chance)
                if time.time() - last_dice_roll > 60:
                    if random.randint(1, 400) == 77:
                        print(f"📉 {name}: Brief disconnect triggered for Statbot wavy look.")
                        break 
                    last_dice_roll = time.time()

                if time.time() - last_heartbeat > 30:
                    ws.send(json.dumps({"op": 1, "d": data.get('s')}))
                    # Re-send join payload occasionally to ensure bot stays in VC
                    if random.random() > 0.5:
                        ws.send(json.dumps(join_payload))
                    last_heartbeat = time.time()

            ws.close()
            time.sleep(random.randint(400, 450)) # Offline for ~7 mins

        except:
            time.sleep(20)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    for name, data in tokens.items():
        if data["token"]:
            threading.Thread(target=vc_locker, args=(data["token"], data["channel"], name, data["mobile"])).start()
            if data["spam"]:
                threading.Thread(target=daily_spammer, daemon=True).start()
            time.sleep(random.randint(10, 20))
    while True: time.sleep(1)
        
