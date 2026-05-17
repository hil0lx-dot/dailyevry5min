import os, json, time, threading, websocket, requests, random
from flask import Flask

app = Flask('')
@app.route('/')
def home(): return "🛰️ Sentinel Smart-Lock: Active"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURATION ---
GUILD_ID = "777271906486976512"

# Hardcoded Home VCs for locking
VC_ONE_ID = "1505201571577987132"
VC_TWO_ID = "1465180321124454486"
VC_THREE_ID = "1505201571577987132"

# New Target Channel for text spamming (Only for Sentinel-1 and Sentinel-3)
SPAM_CHANNEL_ID = "1487672527370322132"

tokens = {
    "Sentinel-1": {"token": os.getenv("TOKEN_ONE"), "channel": VC_ONE_ID, "mobile": False, "spam": True},
    "Sentinel-2": {"token": os.getenv("TOKEN_TWO"), "channel": VC_TWO_ID, "mobile": False, "spam": False},
    "Sentinel-3": {"token": os.getenv("TOKEN_THREE"), "channel": VC_THREE_ID, "mobile": True, "spam": True}
}

# --- BACKGROUND SPAMMER FUNCTION ---
def spammer_worker(token, name):
    if not token: return
    header = {"Authorization": token.strip()}
    payload = {"content": "bro ;-;"}
    
    while True:
        try:
            res = requests.post(
                f"https://discord.com/api/v9/channels/{SPAM_CHANNEL_ID}/messages",
                headers=header, json=payload
            )
            # Handle rate limits dynamically if they hit it
            if res.status_code == 429:
                wait = res.json().get('retry_after', 5)
                time.sleep(wait)
            else:
                time.sleep(11) # Wait 5 minutes
        except:
            time.sleep(10)

# --- MAIN VC LOCKER FUNCTION ---
def vc_locker(token, home_channel, name, is_mobile):
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
                    "guild_id": GUILD_ID, "channel_id": home_channel,
                    "self_mute": False, "self_deaf": False,
                    "self_video": False, "self_stream": not is_mobile
                }
            }

            last_heartbeat = 0
            last_dice_roll = 0
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
                    print(f"✅ {name} online.")

                # --- SMART REJOIN LOGIC ---
                if t == "VOICE_STATE_UPDATE":
                    if d.get('user_id') == user_id:
                        new_channel = d.get('channel_id')
                        
                        # REJECT KICK: If channel is None, rejoin home
                        if new_channel is None:
                            print(f"🚫 {name} was kicked. Rejoining {home_channel}...")
                            time.sleep(1)
                            ws.send(json.dumps(join_payload))
                        
                        # ACCEPT MOVE: If moved to a different ID, don't rejoin
                        elif new_channel != home_channel:
                            print(f"📍 {name} was moved. Staying in new VC.")

                # Rare disconnect for Wavy Line (1 in 400 chance every 60s)
                if time.time() - last_dice_roll > 60:
                    if random.randint(1, 400) == 77:
                        print(f"📉 {name}: Rare disconnect for wavy look.")
                        break 
                    last_dice_roll = time.time()

                if time.time() - last_heartbeat > 30:
                    ws.send(json.dumps({"op": 1, "d": data.get('s')}))
                    last_heartbeat = time.time()

            ws.close()
            time.sleep(random.randint(400, 450)) # Gap for wavy line

        except:
            time.sleep(20)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    
    for name, data in tokens.items():
        if data["token"]:
            # Start the VC Locker thread for all alts
            threading.Thread(target=vc_locker, args=(data["token"], data["channel"], name, data["mobile"])).start()
            
            # Start the Spammer thread only if "spam" is True (Sentinel-1 and Sentinel-3)
            if data["spam"]:
                threading.Thread(target=spammer_worker, args=(data["token"], name), daemon=True).start()
                
            time.sleep(random.randint(5, 15))
            
    while True: time.sleep(1)
        
