import os, json, time, threading, websocket, requests, random, re
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

# 🟢 CUSTOMIZABLE STATUS 🟢
# Options: "online", "idle", "dnd", "invisible" (for offline)
STATUS = "invisible" 

# Hardcoded Home VCs for locking (Updated: 1 and 3 match)
VC_ONE_ID = "1488606312563736646"
VC_TWO_ID = "1488606312563736646"
VC_THREE_ID = "1488606312563736646"

# Target Channel for background text spamming (Sentinel-1 and Sentinel-3)
SPAM_CHANNEL_ID = "1488606312563736646"

tokens = {
    "Sentinel-1": {"token": os.getenv("TOKEN_ONE"), "channel": VC_ONE_ID, "mobile": True, "spam": True},
    "Sentinel-2": {"token": os.getenv("TOKEN_TWO"), "channel": VC_TWO_ID, "mobile": False, "spam": False},
    "Sentinel-3": {"token": os.getenv("TOKEN_THREE"), "channel": VC_THREE_ID, "mobile": True, "spam": False}
}

# --- TRACKING STATES FOR HOT-REJOIN / MOVEMENT OVERRIDES ---
channels_state = {name: data["channel"] for name, data in tokens.items()}
leave_lockouts = {name: {"temp_leave": False, "timeout_until": 0} for name in tokens.keys()}
user_current_vc = None  # Tracks your current voice channel globally via gateways

# --- BACKGROUND SPAMMER FUNCTION ---
def spammer_worker(token, name):
    if not token: return
    header = {"Authorization": token.strip()}
    payload = {"content": "​​ 1pr "}
    
    while True:
        try:
            res = requests.post(
                f"https://discord.com/api/v9/channels/{SPAM_CHANNEL_ID}/messages",
                headers=header, json=payload
            )
            if res.status_code == 429:
                wait = res.json().get('retry_after', 1)
                time.sleep(wait)
            else:
                time.sleep(1)
        except:
            time.sleep(1)

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
def vc_locker(token, initial_home_channel, name, is_mobile):
    global user_current_vc
    if not token: return

    while True:
        try:
            # Check if this specific thread is in a 5raj 1-minute timeout block
            if leave_lockouts[name]["temp_leave"]:
                if time.time() < leave_lockouts[name]["timeout_until"]:
                    time.sleep(2)
                    continue
                else:
                    leave_lockouts[name]["temp_leave"] = False
                    print(f"⏰ 1 minute up. Rejoining target VC for {name}...")

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
                    "presence": {"status": STATUS, "afk": False} 
                }
            }))

            current_target = channels_state[name]
            join_payload = {
                "op": 4, "d": {
                    "guild_id": GUILD_ID, "channel_id": current_target,
                    "self_mute": False, "self_deaf": False,
                    "self_video": False, "self_stream": not is_mobile
                }
            }

            last_heartbeat = 0
            last_dice_roll = 0
            user_id = None
            alt_current_vc = current_target
            
            while True:
                # Force close loop connection if internal state changes dynamically (via commands)
                if channels_state[name] != current_target or leave_lockouts[name]["temp_leave"]:
                    break

                msg = ws.recv()
                if not msg: break
                data = json.loads(msg)
                
                op = data.get('op')
                t = data.get('t')
                d = data.get('d')

                if op == 10:
                    time.sleep(2) 
                    ws.send(json.dumps(join_payload))

                if t == "READY":
                    user_id = d['user']['id']
                    print(f"✅ {name} online (Status: {STATUS}).")
                    time.sleep(1)
                    ws.send(json.dumps(join_payload))

                # --- REMOTE CONTROL PARSER & TRANSLATOR ---
                if t == "MESSAGE_CREATE":
                    author_id = d.get('author', {}).get('id')
                    content = d.get('content', '').strip()
                    text_channel = d.get('channel_id')
                    msg_guild_id = d.get('guild_id')

                    if msg_guild_id == GUILD_ID and author_id == MY_USER_ID:
                        lower_content = content.lower()
                        
                        # Command: daily
                        if content == "daily":
                            send_chat_message(token, text_channel, "d")

                        # Command: 5raj (Leave for 1 min if you share the channel)
                        elif lower_content == "5raj":
                            if user_current_vc and alt_current_vc and user_current_vc == alt_current_vc:
                                print(f"🚫 {name} leaving VC for 1 minute by owner's command.")
                                leave_lockouts[name]["temp_leave"] = True
                                leave_lockouts[name]["timeout_until"] = time.time() + 60
                                
                                # Disconnect command payload
                                leave_payload = {
                                    "op": 4, "d": {
                                        "guild_id": GUILD_ID, "channel_id": None,
                                        "self_mute": False, "self_deaf": False
                                    }
                                }
                                ws.send(json.dumps(leave_payload))
                                break

                        # Command: 
                        elif lower_content.startswith("aji"):
                            # Condition A: Targeted move "aji <@id> channel_id"
                            if f"<@{user_id}>" in content or f"<@!{user_id}>" in content:
                                match = re.search(r'\d+$', content)
                                if match:
                                    target_vc = match.group()
                                    print(f"🚀 Targeted transfer for {name} -> {target_vc}")
                                    leave_lockouts[name]["temp_leave"] = False
                                    channels_state[name] = target_vc
                                    break
                            
                            # Condition B: Global recovery "aji"
                            elif lower_content == "aji":
                                if leave_lockouts[name]["temp_leave"]:
                                    print(f"🍃 Break lockout early for {name}.")
                                    leave_lockouts[name]["temp_leave"] = False
                                    break

                        # Leaderboard Utilities
                        elif lower_content == "lb chat": send_chat_message(token, text_channel, "&lb chat")
                        elif lower_content == "lb vc":   send_chat_message(token, text_channel, "&lb voice")
                        elif lower_content == "lb net":  send_chat_message(token, text_channel, "&lb networth")
                        elif lower_content == "lb xp":   send_chat_message(token, text_channel, "&lb xp")

                        # Simple Utilities
                        elif lower_content == "hidi": send_chat_message(token, text_channel, ".v hide")
                        elif lower_content == "sd":   send_chat_message(token, text_channel, ".v lock")
                        elif lower_content == "7l":   send_chat_message(token, text_channel, ".v unlock")

                        # Complex Shortcuts
                        elif lower_content == "7yd co" or lower_content.startswith("7yd co "):
                            target = content[6:].strip() if len(content) > 6 else MY_USER_ID
                            send_chat_message(token, text_channel, f".v cowner remove {target}")
                        elif lower_content == "perm" or lower_content.startswith("perm "):
                            target = content[4:].strip() if len(content) > 4 else MY_USER_ID
                            send_chat_message(token, text_channel, f".v perm {target}")
                        elif lower_content == "reject" or lower_content.startswith("reject "):
                            target = content[6:].strip() if len(content) > 6 else MY_USER_ID
                            send_chat_message(token, text_channel, f".v reject {target}")
                        elif lower_content == "co" or lower_content.startswith("co "):
                            target = content[2:].strip() if len(content) > 2 else MY_USER_ID
                            send_chat_message(token, text_channel, f".v cowner add {target}")
                        
                        # Single-Letter Text Command Shortcuts
                        elif lower_content == "a" or lower_content.startswith("a "):
                            target = content[1:].strip() if len(content) > 1 else MY_USER_ID
                            send_chat_message(token, text_channel, f"a {target}")
                        elif lower_content == "p" or lower_content.startswith("p "):
                            target = content[1:].strip() if len(content) > 1 else MY_USER_ID
                            send_chat_message(token, text_channel, f"p {target}")
                        elif lower_content == "c" or lower_content.startswith("c "):
                            target = content[1:].strip() if len(content) > 1 else MY_USER_ID
                            send_chat_message(token, text_channel, f"c {target}")
                        elif lower_content == "b" or lower_content.startswith("b "):
                            target = content[1:].strip() if len(content) > 1 else MY_USER_ID
                            send_chat_message(token, text_channel, f"b {target}")
                        elif lower_content == "r" or lower_content.startswith("r "):
                            target = content[1:].strip() if len(content) > 1 else MY_USER_ID
                            send_chat_message(token, text_channel, f"r {target}")
                        elif lower_content == "u" or lower_content.startswith("u "):
                            target = content[1:].strip() if len(content) > 1 else MY_USER_ID
                            send_chat_message(token, text_channel, f"u {target}")

                # --- SAFE BUTTON DETECTION ---
                if t in ["MESSAGE_UPDATE", "MESSAGE_CREATE"]:
                    if d and d.get('guild_id') == GUILD_ID:
                        author = d.get('author', {})
                        if author.get('bot') is True:
                            components = d.get('components')
                            if components:
                                time.sleep(0.5)
                                click_confirm_button(token, d)

                # --- SMART REJOIN / TRACKING LOGIC ---
                if t == "VOICE_STATE_UPDATE":
                    # Track your current location globally to handle 5raj isolation checks
                    if d.get('user_id') == MY_USER_ID:
                        user_current_vc = d.get('channel_id')

                    if d.get('user_id') == user_id:
                        alt_current_vc = d.get('channel_id')
                        
                        if alt_current_vc is None and not leave_lockouts[name]["temp_leave"]:
                            print(f"🚫 {name} was kicked. Rejoining {channels_state[name]}...")
                            time.sleep(1)
                            ws.send(json.dumps(join_payload))
                        elif alt_current_vc and alt_current_vc != channels_state[name]:
                            print(f"📍 {name} shifted. Syncing target VC tracking.")
                            channels_state[name] = alt_current_vc
                            current_target = alt_current_vc

                if time.time() - last_dice_roll > 60:
                    if random.randint(1, 400) == 77:
                        print(f"📉 {name}: Rare disconnect for wavy look.")
                        break 
                    last_dice_roll = time.time()

                if time.time() - last_heartbeat > 30:
                    ws.send(json.dumps({"op": 1, "d": data.get('s')}))
                    last_heartbeat = time.time()

            ws.close()
            time.sleep(random.randint(5, 10) if leave_lockouts[name]["temp_leave"] else random.randint(400, 450))

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
