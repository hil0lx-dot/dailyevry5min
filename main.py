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
MY_USER_ID = "1404189983807639672"

# Hardcoded Home VCs for locking
VC_ONE_ID = "1489198958759903232"
VC_TWO_ID = "1487672527370322132"
VC_THREE_ID = "1489198958759903232"

# New Target Channel for background text spamming (Sentinel-1 and Sentinel-3)
SPAM_CHANNEL_ID = "1487672527370322132"

tokens = {
    "Sentinel-1": {"token": os.getenv("TOKEN_ONE"), "channel": VC_ONE_ID, "mobile": True, "spam": True},
    "Sentinel-2": {"token": os.getenv("TOKEN_TWO"), "channel": VC_TWO_ID, "mobile": False, "spam": False},
    "Sentinel-3": {"token": os.getenv("TOKEN_THREE"), "channel": VC_THREE_ID, "mobile": True, "spam": True}
}

# --- BACKGROUND SPAMMER FUNCTION ---
def spammer_worker(token, name):
    if not token: return
    header = {"Authorization": token.strip()}
    payload = {"content": ""}
    
    while True:
        try:
            res = requests.post(
                f"https://discord.com/api/v9/channels/{SPAM_CHANNEL_ID}/messages",
                headers=header, json=payload
            )
            if res.status_code == 429:
                wait = res.json().get('retry_after', 5)
                time.sleep(wait)
            else:
                time.sleep(11)
        except:
            time.sleep(10)

# --- HELPER TO SEND TEXT RESPONSES ---
def send_chat_message(token, text_channel_id, content):
    url = f"https://discord.com/api/v9/channels/{text_channel_id}/messages"
    headers = {"Authorization": token.strip(), "Content-Type": "application/json"}
    try:
        requests.post(url, headers=headers, json={"content": content})
    except:
        pass

# --- HELPER TO INTERACT WITH BUTTONS ---
def click_confirm_button(token, msg_data):
    try:
        components = msg_data.get('components', [])
        if not components: return
        
        custom_id = None
        for row in components:
            if row.get('type') == 1:
                for item in row.get('components', []):
                    if item.get('type') == 2:
                        custom_id = item.get('custom_id')
                        break
            if custom_id: break
            
        if not custom_id: return
        
        payload = {
            "type": 3,
            "guild_id": GUILD_ID,
            "channel_id": msg_data['channel_id'],
            "message_id": msg_data['id'],
            "application_id": msg_data['author']['id'],
            "data": {
                "component_type": 2,
                "custom_id": custom_id
            }
        }
        url = "https://discord.com/api/v9/interactions"
        headers = {"Authorization": token.strip(), "Content-Type": "application/json"}
        requests.post(url, headers=headers, json=payload)
    except:
        pass

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

                # SAFE DELAY FIX: Let the handshake complete before slamming the voice channel payload
                if op == 10:
                    time.sleep(2) 
                    ws.send(json.dumps(join_payload))

                if t == "READY":
                    user_id = d['user']['id']
                    print(f"✅ {name} online.")
                    # Fallback backup join command once session state confirms active
                    time.sleep(1)
                    ws.send(json.dumps(join_payload))

                # --- REMOTE CONTROL LISTENER ---
                if t == "MESSAGE_CREATE":
                    author_id = d.get('author', {}).get('id')
                    content = d.get('content', '').strip()
                    text_channel = d.get('channel_id')
                    msg_guild_id = d.get('guild_id')

                    if msg_guild_id == GUILD_ID and author_id == MY_USER_ID:
                        if content == "daily":
                            send_chat_message(token, text_channel, "d")

                # --- SAFE BUTTON DETECTION ---
                if t in ["MESSAGE_UPDATE", "MESSAGE_CREATE"]:
                    if d and d.get('guild_id') == GUILD_ID:
                        author = d.get('author', {})
                        if author.get('bot') is True:
                            components = d.get('components')
                            if components:
                                time.sleep(0.5)
                                click_confirm_button(token, d)

                # --- SMART REJOIN LOGIC ---
                if t == "VOICE_STATE_UPDATE":
                    if d.get('user_id') == user_id:
                        new_channel = d.get('channel_id')
                        
                        if new_channel is None:
                            print(f"🚫 {name} was kicked. Rejoining {home_channel}...")
                            time.sleep(1)
                            ws.send(json.dumps(join_payload))
                        elif new_channel != home_channel:
                            print(f"📍 {name} was moved. Staying in new VC.")

                if time.time() - last_dice_roll > 60:
                    if random.randint(1, 400) == 77:
                        print(f"📉 {name}: Rare disconnect for wavy look.")
                        break 
                    last_dice_roll = time.time()

                if time.time() - last_heartbeat > 30:
                    ws.send(json.dumps({"op": 1, "d": data.get('s')}))
                    last_heartbeat = time.time()

            ws.close()
            time.sleep(random.randint(400, 450))

        except:
            time.sleep(20)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    
    for name, data in tokens.items():
        if data["token"]:
            threading.Thread(target=vc_locker, args=(data["token"], data["channel"], name, data["mobile"])).start()
            if data["spam"]:
                threading.Thread(target=spammer_worker, args=(data["token"], name), daemon=True).start()
            time.sleep(random.randint(5, 15))
            
    while True: time.sleep(1)
        
