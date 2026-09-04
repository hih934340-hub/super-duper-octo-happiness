from flask import Flask, jsonify
from flask_cors import CORS
import requests
import os
import threading
import time
import logging
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PORT = int(os.getenv('PORT', 2930))
SELF_URL = os.getenv('SELF_URL', f'http://localhost:{PORT}')

# Cấu trúc dữ liệu mặc định
latest_result = {
    "phien": 0,
    "xuc_xac_1": 0,
    "xuc_xac_2": 0,
    "xuc_xac_3": 0,
    "tong": 0,
    "ket_qua": "",
    "md5_enc": "",
    "md5_dec": "",
    "so_nguoi_cuoc_tai": 0,
    "tong_tien_cuoc_tai": "0 ₫",
    "so_nguoi_cuoc_xiu": 0,
    "tong_tien_cuoc_xiu": "0 ₫"
}

API_TARGET_URL = 'https://jakpotgwab.geightdors.net/glms/v1/notify/taixiu?platform_id=b5&gid=vgmn_101'

def format_currency(amount):
    """Định dạng số tiền với dấu phẩy và ký hiệu ₫"""
    if amount is None:
        return "0 ₫"
    return f"{amount:,} ₫"

def update_result(game_data):
    """Cập nhật kết quả mới nhất từ dữ liệu game"""
    sid = game_data.get("sid")
    d1 = game_data.get("d1")
    d2 = game_data.get("d2")
    d3 = game_data.get("d3")
    md5 = game_data.get("md5", "")
    rs = game_data.get("rs", "")
    
    # Kiểm tra dữ liệu hợp lệ
    if d1 is None or d2 is None or d3 is None:
        logger.warning(f"⚠️ dữ liệu không hợp lệ: d1={d1}, d2={d2}, d3={d3}")
        return
    
    # Lấy thông tin cược
    bs_list = game_data.get("bs", [])
    so_nguoi_cuoc_tai = 0
    tong_tien_cuoc_tai = 0
    so_nguoi_cuoc_xiu = 0
    tong_tien_cuoc_xiu = 0
    
    for bet in bs_list:
        eid = bet.get("eid")
        bc = bet.get("bc", 0)
        v = bet.get("v", 0)
        if bc is None:
            bc = 0
        if v is None:
            v = 0
        if eid == 1:
            so_nguoi_cuoc_tai = bc
            tong_tien_cuoc_tai = v
        elif eid == 2:
            so_nguoi_cuoc_xiu = bc
            tong_tien_cuoc_xiu = v
    
    total = d1 + d2 + d3
    result = "tài" if total > 10 else "xỉu"
    
    latest_result.update({
        "phien": sid if sid is not None else latest_result["phien"],
        "xuc_xac_1": d1,
        "xuc_xac_2": d2,
        "xuc_xac_3": d3,
        "tong": total,
        "ket_qua": result,
        "md5_enc": md5 if md5 else "",
        "md5_dec": rs if rs else "",
        "so_nguoi_cuoc_tai": so_nguoi_cuoc_tai,
        "tong_tien_cuoc_tai": format_currency(tong_tien_cuoc_tai),
        "so_nguoi_cuoc_xiu": so_nguoi_cuoc_xiu,
        "tong_tien_cuoc_xiu": format_currency(tong_tien_cuoc_xiu)
    })
    
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[🎲✅] phiên {latest_result['phien']} - {d1}-{d2}-{d3} ➜ tổng: {total}, kết quả: {result} | {time_str}")

def fetch_game_data():
    """Lấy dữ liệu từ API nguồn"""
    try:
        response = requests.get(API_TARGET_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "OK" and isinstance(data.get("data"), list) and len(data["data"]) > 0:
            game = data["data"][0]
            sid = game.get("sid")
            
            # Kiểm tra sid hợp lệ và khác phiên hiện tại
            if sid is not None and sid != latest_result["phien"]:
                update_result(game)
            elif sid is None:
                logger.warning("⚠️ sid bị null, bỏ qua cập nhật")
                
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ lỗi khi lấy dữ liệu từ api get: {e}")
    except Exception as e:
        logger.error(f"❌ lỗi xử lý dữ liệu: {e}")

def start_fetching():
    """Chạy fetch dữ liệu định kỳ"""
    def fetch_loop():
        while True:
            try:
                fetch_game_data()
            except Exception as e:
                logger.error(f"❌ lỗi trong fetch_loop: {e}")
            time.sleep(5)
    
    thread = threading.Thread(target=fetch_loop, daemon=True)
    thread.start()

@app.route("/txmd5", methods=['GET'])
def get_txmd5():
    """Endpoint trả về kết quả đã xử lý"""
    return jsonify(latest_result)

@app.route("/", methods=['GET'])
def home():
    return jsonify({
        "status": "b52 tài xỉu đang chạy",
        "phien": latest_result["phien"]
    })

# Tự động gọi chính mình mỗi 5 phút để giữ server hoạt động
def keep_alive():
    def ping_loop():
        while True:
            time.sleep(300)
            try:
                if SELF_URL and "http" in SELF_URL:
                    requests.get(f"{SELF_URL}/", timeout=5)
            except:
                pass
    
    thread = threading.Thread(target=ping_loop, daemon=True)
    thread.start()

if __name__ == "__main__":
    start_fetching()
    keep_alive()
    logger.info(f"🚀 server b52 tài xỉu đang chạy tại http://localhost:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)