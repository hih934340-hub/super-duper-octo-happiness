from flask import Flask, jsonify, request
import json
import threading
import asyncio
import websockets
import os
import time
from datetime import datetime

app = Flask(__name__)

# Dữ liệu TX
tx_data = {
    "phien": None,
    "xuc_xac_1": None,
    "xuc_xac_2": None,
    "xuc_xac_3": None,
    "tong": None,
    "ket_qua": None,
    "so_nguoi_cuoc_tai": None,
    "so_tien_cuoc_tai": None,
    "so_nguoi_cuoc_xiu": None,
    "so_tien_cuoc_xiu": None,
    "lich_su_cuoc": [],
    "thong_bao": [],
    "last_update": None
}

def get_token():
    try:
        with open('token.txt', 'r', encoding='utf-8') as f:
            content = f.read()
            import re
            match = re.search(r'"wsToken":"([^"]+)"', content)
            if match:
                return match.group(1)
    except:
        pass
    return os.getenv('WS_TOKEN', '')

def get_user_info():
    try:
        with open('token.txt', 'r', encoding='utf-8') as f:
            content = f.read()
            import re
            user_match = re.search(r'"userId":"([^"]+)"', content)
            username_match = re.search(r'"username":"([^"]+)"', content)
            ip_match = re.search(r'"ipAddress":"([^"]+)"', content)
            return {
                'userId': user_match.group(1) if user_match else 'a28a0f06-e88f-44b7-a268-5f6dad949fbf',
                'username': username_match.group(1) if username_match else 'GM_quapotjz',
                'ipAddress': ip_match.group(1) if ip_match else '2405:4802:4e41:f250:504:abb9:4a0:d206'
            }
    except:
        return {
            'userId': os.getenv('USER_ID', 'a28a0f06-e88f-44b7-a268-5f6dad949fbf'),
            'username': os.getenv('USERNAME', 'GM_quapotjz'),
            'ipAddress': os.getenv('IP_ADDRESS', '2405:4802:4e41:f250:504:abb9:4a0:d206')
        }

def parse_tx_data(message):
    try:
        data = json.loads(message)
        if len(data) >= 2 and isinstance(data[1], dict):
            msg_data = data[1]
            cmd = msg_data.get('cmd')
            
            if cmd == 2106 and 'bs' in msg_data:
                bs_array = msg_data['bs']
                tai_data = bs_array[0] if len(bs_array) > 0 else {}
                xiu_data = bs_array[1] if len(bs_array) > 1 else {}
                
                tx_data["so_nguoi_cuoc_tai"] = tai_data.get('bc')
                tx_data["so_tien_cuoc_tai"] = tai_data.get('v')
                tx_data["so_nguoi_cuoc_xiu"] = xiu_data.get('bc')
                tx_data["so_tien_cuoc_xiu"] = xiu_data.get('v')
                
                if 'd1' in msg_data:
                    tx_data["xuc_xac_1"] = msg_data['d1']
                if 'd2' in msg_data:
                    tx_data["xuc_xac_2"] = msg_data['d2']
                if 'd3' in msg_data:
                    tx_data["xuc_xac_3"] = msg_data['d3']
                
                if tx_data["xuc_xac_1"] is not None:
                    tong = tx_data["xuc_xac_1"] + tx_data["xuc_xac_2"] + tx_data["xuc_xac_3"]
                    tx_data["tong"] = tong
                    tx_data["ket_qua"] = "Tài" if tong >= 11 else "Xỉu"
                
                if 'sid' in msg_data:
                    tx_data["phien"] = msg_data['sid']
                
                history = {
                    "timestamp": datetime.now().isoformat(),
                    "phien": tx_data["phien"],
                    "xuc_xac": [tx_data["xuc_xac_1"], tx_data["xuc_xac_2"], tx_data["xuc_xac_3"]],
                    "tong": tx_data["tong"],
                    "ket_qua": tx_data["ket_qua"],
                }
                tx_data["lich_su_cuoc"].insert(0, history)
                tx_data["lich_su_cuoc"] = tx_data["lich_su_cuoc"][:50]
                tx_data["last_update"] = datetime.now().isoformat()
    except Exception as e:
        print(f"Error: {e}")

async def websocket_client():
    uri = "wss://websocket.atpman.net/websocket"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                user_info = get_user_info()
                token = get_token()
                
                init_msg = [1, "MiniGame", "quapitjz1", "Hung2010a", {
                    "info": json.dumps({
                        "ipAddress": user_info['ipAddress'],
                        "wsToken": token,
                        "locale": "vi",
                        "userId": user_info['userId'],
                        "username": user_info['username'],
                        "timestamp": int(time.time() * 1000),
                    })
                }]
                await websocket.send(json.dumps(init_msg))
                await asyncio.sleep(1)
                
                tx_cmd = [6, "MiniGame", "taixiuCommonPlugin", {"cmd": 2100}]
                await websocket.send(json.dumps(tx_cmd))
                
                async def keep_alive():
                    while True:
                        await asyncio.sleep(5)
                        ping = [7, "Simms", 2, 0, {"id": 0}]
                        await websocket.send(json.dumps(ping))
                        await websocket.send(json.dumps(tx_cmd))
                
                asyncio.create_task(keep_alive())
                
                async for message in websocket:
                    parse_tx_data(message)
        except Exception as e:
            print(f"WebSocket error: {e}")
            await asyncio.sleep(5)

def start_websocket():
    """Khởi động WebSocket trong thread riêng"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(websocket_client())

@app.route('/api/tx', methods=['GET'])
def get_tx():
    return jsonify({
        "current": {
            "phien": tx_data["phien"],
            "xuc_xac": [tx_data["xuc_xac_1"], tx_data["xuc_xac_2"], tx_data["xuc_xac_3"]],
            "tong": tx_data["tong"],
            "ket_qua": tx_data["ket_qua"],
        },
        "last_update": tx_data["last_update"]
    })

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "TX WebSocket running",
        "phien": tx_data["phien"]
    })

# Khởi động WebSocket khi import
websocket_thread = threading.Thread(target=start_websocket, daemon=True)
websocket_thread.start()

if __name__ == "__main__":
    port = int(os.getenv('PORT', 1234))
    app.run(host='0.0.0.0', port=port)
