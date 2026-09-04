import asyncio
import json
import websockets
import time
from datetime import datetime
from flask import Flask, jsonify
import threading
import sys
import io

# Set UTF-8 cho console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

app = Flask(__name__)

# Biến toàn cục để lưu dữ liệu tx
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
    "lich_su_cuoc": [],  # Lưu lịch sử cược
    "thong_bao": [],     # Lưu thông báo
    "last_update": None
}

def parse_tx_data(message):
    """Parse dữ liệu từ message nhận được"""
    try:
        # Log message nhận được với encoding đúng
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] NHẬN MESSAGE:")
        print(f"Raw: {message}")
        
        # Parse message JSON
        data = json.loads(message)
        print(f"Parsed: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        # Kiểm tra cấu trúc message
        if len(data) >= 2 and isinstance(data[1], dict):
            msg_data = data[1]
            cmd = msg_data.get('cmd')
            
            # Xử lý cmd 2106 - Dữ liệu tài xỉu
            if cmd == 2106 and 'bs' in msg_data:
                bs_array = msg_data['bs']
                
                print("\n" + "="*60)
                print("=== DỮ LIỆU TÀI XỈU ===")
                print("="*60)
                
                # Lấy dữ liệu từ bs array
                tai_data = bs_array[0] if len(bs_array) > 0 else {}
                xiu_data = bs_array[1] if len(bs_array) > 1 else {}
                
                # Cập nhật dữ liệu
                tx_data["so_nguoi_cuoc_tai"] = tai_data.get('bc')
                tx_data["so_tien_cuoc_tai"] = tai_data.get('v')
                tx_data["so_nguoi_cuoc_xiu"] = xiu_data.get('bc')
                tx_data["so_tien_cuoc_xiu"] = xiu_data.get('v')
                
                print(f"📊 TÀI:")
                print(f"   - Số người cược: {tx_data['so_nguoi_cuoc_tai']}")
                print(f"   - Số tiền cược: {tx_data['so_tien_cuoc_tai']:,}")
                print(f"\n📊 XỈU:")
                print(f"   - Số người cược: {tx_data['so_nguoi_cuoc_xiu']}")
                print(f"   - Số tiền cược: {tx_data['so_tien_cuoc_xiu']:,}")
                
                # Lấy kết quả xúc xắc
                if 'd1' in msg_data:
                    tx_data["xuc_xac_1"] = msg_data['d1']
                if 'd2' in msg_data:
                    tx_data["xuc_xac_2"] = msg_data['d2']
                if 'd3' in msg_data:
                    tx_data["xuc_xac_3"] = msg_data['d3']
                
                if tx_data["xuc_xac_1"] is not None:
                    print(f"\n🎲 KẾT QUẢ XÚC XẮC:")
                    print(f"   - Xúc xắc 1: {tx_data['xuc_xac_1']}")
                    print(f"   - Xúc xắc 2: {tx_data['xuc_xac_2']}")
                    print(f"   - Xúc xắc 3: {tx_data['xuc_xac_3']}")
                
                # Tính tổng và kết quả
                if tx_data["xuc_xac_1"] is not None and tx_data["xuc_xac_2"] is not None and tx_data["xuc_xac_3"] is not None:
                    tong = tx_data["xuc_xac_1"] + tx_data["xuc_xac_2"] + tx_data["xuc_xac_3"]
                    tx_data["tong"] = tong
                    
                    # Kiểm tra kết quả: Tài (tổng 11-18 hoặc 3 mặt đều 3), Xỉu (tổng 4-10)
                    if tong >= 11 or (tx_data["xuc_xac_1"] == 3 and tx_data["xuc_xac_2"] == 3 and tx_data["xuc_xac_3"] == 3):
                        tx_data["ket_qua"] = "Tài"
                    else:
                        tx_data["ket_qua"] = "Xỉu"
                    
                    print(f"\n📈 TỔNG ĐIỂM: {tong}")
                    print(f"🏆 KẾT QUẢ: {tx_data['ket_qua']}")
                
                # Lấy phiên
                if 'sid' in msg_data:
                    tx_data["phien"] = msg_data['sid']
                    print(f"\n🆔 PHIÊN: {tx_data['phien']}")
                
                # Lưu lịch sử
                history = {
                    "timestamp": datetime.now().isoformat(),
                    "phien": tx_data["phien"],
                    "xuc_xac": [tx_data["xuc_xac_1"], tx_data["xuc_xac_2"], tx_data["xuc_xac_3"]],
                    "tong": tx_data["tong"],
                    "ket_qua": tx_data["ket_qua"],
                    "tai": {"nguoi": tx_data["so_nguoi_cuoc_tai"], "tien": tx_data["so_tien_cuoc_tai"]},
                    "xiu": {"nguoi": tx_data["so_nguoi_cuoc_xiu"], "tien": tx_data["so_tien_cuoc_xiu"]}
                }
                tx_data["lich_su_cuoc"].insert(0, history)
                # Giữ lại 50 lịch sử gần nhất
                tx_data["lich_su_cuoc"] = tx_data["lich_su_cuoc"][:50]
                
                tx_data["last_update"] = datetime.now().isoformat()
                print("\n" + "="*60)
                
            # Xử lý cmd 2108 - Thông báo
            elif cmd == 2108:
                mgs = msg_data.get('mgs', '')
                c = msg_data.get('c', 0)
                tst = msg_data.get('tst', 0)
                fu = msg_data.get('fu', '')
                
                print("\n" + "="*60)
                print("=== THÔNG BÁO ===")
                print(f"📢 Nội dung: {mgs}")
                print(f"🔢 Mã: {c}")
                print(f"⏰ Thời gian: {datetime.fromtimestamp(tst/1000).strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"🔑 Fu: {fu}")
                print("="*60)
                
                # Lưu thông báo
                notification = {
                    "timestamp": datetime.now().isoformat(),
                    "time": tst,
                    "message": mgs,
                    "code": c,
                    "fu": fu
                }
                tx_data["thong_bao"].insert(0, notification)
                tx_data["thong_bao"] = tx_data["thong_bao"][:20]
                
            # Xử lý cmd 10000 - Dữ liệu game
            elif cmd == 10000:
                if 'Js' in msg_data:
                    print("\n" + "="*60)
                    print("=== DỮ LIỆU GAME (cmd 10000) ===")
                    print(f"📦 Có {len(msg_data['Js'])} game items")
                    # Hiển thị 5 item đầu tiên
                    for i, item in enumerate(msg_data['Js'][:5]):
                        print(f"  {i+1}. Game {item.get('gid')} - {item.get('gn', 'Unknown')}: {item.get('b')} x {item.get('J'):,}")
                    if len(msg_data['Js']) > 5:
                        print(f"  ... và {len(msg_data['Js'])-5} items khác")
                    print("="*60)
            
            # Các cmd khác
            else:
                print(f"\n📌 Message cmd {cmd} từ {data[2] if len(data) > 2 else 'unknown'}")
                
        # Xử lý message ping/pong
        elif len(data) >= 1 and data[0] == 8:
            print(f"\n💓 Ping/Pong message")
            
        # Log các message khác
        else:
            print(f"\n📝 Message khác: {data}")
            
    except json.JSONDecodeError as e:
        print(f"❌ Lỗi parse JSON: {e}")
        print(f"Raw message: {message}")
    except Exception as e:
        print(f"❌ Lỗi xử lý dữ liệu: {e}")
        import traceback
        traceback.print_exc()

async def send_messages(websocket):
    """Gửi các message định kỳ"""
    try:
        # Message khởi tạo
        init_message = [1, "MiniGame", "quapitjz1", "Hung2010a", {
            "info": json.dumps({
                "ipAddress": "2405:4802:4e51:e130:4caf:e983:fa23:e5ee",
                "wsToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJnZW5kZXIiOjAsImNhblZpZXdTdGF0IjpmYWxzZSwiZGlzcGxheU5hbWUiOiJkc2pqdTE0OGMiLCJib3QiOjAsImlzTWVyY2hhbnQiOmZhbHNlLCJ2ZXJpZmllZEJhbmtBY2NvdW50IjpmYWxzZSwicGxheUV2ZW50TG9iYnkiOmZhbHNlLCJjdXN0b21lcklkIjo2ODc2Nzg0OCwiYWZmSWQiOiJzdW4ud2luIiwiYmFubmVkIjpmYWxzZSwiYnJhbmQiOiI3ODkuY2x1YiIsImVtYWlsIjoiIiwidGltZXN0YW1wIjoxNzc4NzU0MTI0OTEwLCJsb2NrR2FtZXMiOltdLCJhbW91bnQiOjAsImxvY2tDaGF0IjpmYWxzZSwicGhvbmVWZXJpZmllZCI6ZmFsc2UsImlwQWRkcmVzcyI6IjI0MDU6NDgwMjo0ZTUxOmUxMzA6NGNhZjplOTgzOmZhMjM6ZTVlZSIsIm11dGUiOmZhbHNlLCJhdmF0YXIiOiJodHRwczovL2FwaS54ZXVpLmlvL2ltYWdlcy9hdmF0YXIvYXZhdGFyXzA2LnBuZyIsInBsYXRmb3JtSWQiOjQsInVzZXJJZCI6ImE3MDY4ZTI1LWVkMjQtNDlhZC1iNGRiLTJhMDdjMTMyZmMzMSIsImVtYWlsVmVyaWZpZWQiOm51bGwsInJlZ1RpbWUiOjE3Nzg3NTQxMDYzMjEsInBob25lIjoiIiwiZGVwb3NpdCI6ZmFsc2UsInVzZXJuYW1lIjoiUzhfcXVhcGl0anoxIn0.2Q3jEHgeR8kSlfpejCcy9ui7HDn8SwcvrcKxNNWjycU",
                "locale": "vi",
                "userId": "a7068e25-ed24-49ad-b4db-2a07c132fc31",
                "username": "S8_quapitjz1",
                "timestamp": 1778754124921,
                "refreshToken": "debf5309d7ea447ba2db47e2a86e7467.4aa5c4314aad4e5baf273eaa14e66207"
            }),
            "signature": "65DBF77A74171E1065B3E6AAD6EDD1F42BD3AB550DF07A9048D95BE5008000869416E3BCB85562ECC68B1517D8690DDC4C1ACEFE652BBAD8DBD933564C757C05A7A1E2B907AB4FC31A09ACBF49B0AEDF467E58E8DF12BAAF91629E31C61CEDD98249DF0E64944C70AA68CD3F6C74E7A23482A793339664C410817157E8186B76"
        }]
        
        print(f"\n{'='*60}")
        print(f"📤 GỬI MESSAGE KHỞI TẠO:")
        print(json.dumps(init_message, indent=2, ensure_ascii=False))
        await websocket.send(json.dumps(init_message))
        await asyncio.sleep(1)
        
        # Message taixiuCommonPlugin cmd 2100
        tx_cmd = [6, "MiniGame", "taixiuCommonPlugin", {"cmd": 2100}]
        print(f"\n📤 GỬI CMD 2100 (Đăng ký nhận dữ liệu tài xỉu):")
        print(json.dumps(tx_cmd, indent=2, ensure_ascii=False))
        await websocket.send(json.dumps(tx_cmd))
        await asyncio.sleep(1)
        
        # Message lobbyPlugin cmd 10001
        lobby_cmd = [6, "MiniGame", "lobbyPlugin", {"cmd": 10001}]
        print(f"\n📤 GỬI CMD 10001 (Lấy dữ liệu lobby):")
        print(json.dumps(lobby_cmd, indent=2, ensure_ascii=False))
        await websocket.send(json.dumps(lobby_cmd))
        
        print("\n" + "="*60)
        print("✅ BẮT ĐẦU VÒNG LẶP GỬI MESSAGE ĐỊNH KỲ (mỗi 5 giây)")
        print("="*60)
        
        # Vòng lặp gửi message định kỳ mỗi 5 giây
        count = 0
        while True:
            await asyncio.sleep(5)
            count += 1
            
            # Message Simms
            simms_msg = [7, "Simms", 2, 0, {"id": 0}]
            print(f"\n📤 [{datetime.now().strftime('%H:%M:%S')}] GỬI SIMMS LẦN {count}:")
            print(json.dumps(simms_msg, indent=2, ensure_ascii=False))
            await websocket.send(json.dumps(simms_msg))
            
            # Message taixiuCommonPlugin cmd 2100
            tx_cmd = [6, "MiniGame", "taixiuCommonPlugin", {"cmd": 2100}]
            print(f"📤 [{datetime.now().strftime('%H:%M:%S')}] GỬI CMD 2100 LẦN {count}:")
            print(json.dumps(tx_cmd, indent=2, ensure_ascii=False))
            await websocket.send(json.dumps(tx_cmd))
            
            print(f"✅ ĐÃ GỬI XONG LẦN {count}")
            
    except Exception as e:
        print(f"❌ Lỗi khi gửi message: {e}")
        import traceback
        traceback.print_exc()

async def websocket_client():
    """Kết nối WebSocket và xử lý message"""
    uri = "wss://websocket.atpman.net/websocket"
    
    while True:
        try:
            print(f"\n{'='*60}")
            print(f"🔌 ĐANG KẾT NỐI ĐẾN {uri}")
            print(f"{'='*60}")
            
            async with websockets.connect(uri) as websocket:
                print(f"✅ Đã kết nối thành công!")
                
                # Tạo task gửi message
                send_task = asyncio.create_task(send_messages(websocket))
                
                # Nhận và xử lý message
                try:
                    async for message in websocket:
                        parse_tx_data(message)
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"\n⚠️ Kết nối đã đóng: {e}")
                    print("🔄 Đang thử kết nối lại sau 5 giây...")
                    send_task.cancel()
                    await asyncio.sleep(5)
                    
        except Exception as e:
            print(f"\n❌ Lỗi kết nối: {e}")
            print("🔄 Đang thử kết nối lại sau 5 giây...")
            await asyncio.sleep(5)

@app.route('/api/tx', methods=['GET'])
def get_tx_data():
    """API endpoint để lấy dữ liệu TX hiện tại"""
    return jsonify({
        "current": {
            "phien": tx_data["phien"],
            "xuc_xac": [tx_data["xuc_xac_1"], tx_data["xuc_xac_2"], tx_data["xuc_xac_3"]],
            "tong": tx_data["tong"],
            "ket_qua": tx_data["ket_qua"],
            "tai": {
                "so_nguoi": tx_data["so_nguoi_cuoc_tai"],
                "so_tien": tx_data["so_tien_cuoc_tai"]
            },
            "xiu": {
                "so_nguoi": tx_data["so_nguoi_cuoc_xiu"],
                "so_tien": tx_data["so_tien_cuoc_xiu"]
            }
        },
        "last_update": tx_data["last_update"]
    })

@app.route('/api/tx/history', methods=['GET'])
def get_tx_history():
    """API endpoint để lấy lịch sử TX"""
    limit = request.args.get('limit', 20, type=int)
    return jsonify({
        "history": tx_data["lich_su_cuoc"][:limit],
        "total": len(tx_data["lich_su_cuoc"])
    })

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    """API endpoint để lấy thông báo"""
    limit = request.args.get('limit', 10, type=int)
    return jsonify({
        "notifications": tx_data["thong_bao"][:limit],
        "total": len(tx_data["thong_bao"])
    })

def run_flask():
    """Chạy Flask server"""
    from flask import request
    print(f"\n{'='*60}")
    print(f"🌐 FLASK SERVER ĐANG CHẠY:")
    print(f"   - http://127.0.0.1:9941/api/tx (Dữ liệu hiện tại)")
    print(f"   - http://127.0.0.1:9941/api/tx/history (Lịch sử)")
    print(f"   - http://127.0.0.1:9941/api/notifications (Thông báo)")
    print(f"{'='*60}\n")
    app.run(host='0.0.0.0', port=1234, debug=False, use_reloader=False)

async def main():
    """Main function"""
    # Chạy Flask trong thread riêng
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Chạy WebSocket client
    await websocket_client()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("🛑 ĐÃ DỪNG CHƯƠNG TRÌNH")
        print("="*
