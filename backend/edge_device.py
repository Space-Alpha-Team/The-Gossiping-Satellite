# backend/edge_device.py
# CHẠY TRÊN PORT 8000 (Gateway giao tiếp với Frontend)

import asyncio
import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os
import random
import json
import base64
import time

app = FastAPI()

# Cấu hình CORS để Frontend (React) có thể gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CẤU HÌNH ---
# Địa chỉ của "Bộ não" AI (chạy ở port 8001)
AI_SERVICE_URL = "http://localhost:8001"
# Thư mục chứa ảnh giả lập vệ tinh chụp được
IMAGE_FOLDER = "satellite_images"

# Biến trạng thái tạm (không bắt buộc, dùng để debug)
edge_state = {
    "last_report": None
}

async def satellite_orbit_simulation(websocket: WebSocket):
    """
    Hàm giả lập hoạt động của vệ tinh:
    1. Bay qua vùng trời (Lặp vô tận)
    2. Chụp ảnh (Lấy random từ folder)
    3. Gửi sang AI Service phân tích
    4. Nếu có biến -> Gửi cảnh báo Text + Heatmap về Trái Đất
    """
    
    # Kiểm tra folder ảnh, nếu chưa có thì tạo và báo lỗi
    if not os.path.exists(IMAGE_FOLDER):
        os.makedirs(IMAGE_FOLDER)
        print(f"📁 Created folder '{IMAGE_FOLDER}'. Please add images to it!")
        
    images = [f for f in os.listdir(IMAGE_FOLDER) if f.endswith(('.jpg', '.png', '.jpeg'))]
    
    if not images:
        error_msg = {"type": "system", "text": f"⚠️ SYSTEM ALERT: No images found in '{IMAGE_FOLDER}'."}
        await websocket.send_text(json.dumps(error_msg))
        # Chờ người dùng copy ảnh vào rồi thử lại sau
        await asyncio.sleep(10) 
        return

    print("🛰️  SATELLITE ORBIT SIMULATION: ONLINE")

    while True:
        # 1. Giả lập chụp ảnh (Chọn ngẫu nhiên 1 ảnh)
        img_name = random.choice(images)
        img_path = os.path.join(IMAGE_FOLDER, img_name)
        
        print(f"📸 [EDGE] Scanning sector: {img_name}")

        try:
            # 2. Gửi ảnh sang AI Service (Port 8001) để xử lý
            # Lưu ý: Edge Device KHÔNG xử lý nặng, nó đẩy việc đó cho AI Service (mô phỏng chip AI chuyên dụng)
            with open(img_path, 'rb') as f:
                response = requests.post(f"{AI_SERVICE_URL}/internal/analyze", files={'file': f})
                
            if response.status_code == 200:
                data = response.json()
                report = data.get("text_report", "NO DATA")
                
                # 3. Logic: Chỉ gửi báo cáo nếu KHÔNG PHẢI là "SAFE"
                # (Tiết kiệm băng thông vệ tinh)
                if "SAFE" not in report and "ERROR" not in report:
                    edge_state["last_report"] = report
                    
                    # Đóng gói gói tin truyền về Trái Đất
                    # Gói tin này RẤT NHẸ (chỉ text và mảng số), không chứa ảnh
                    payload = {
                        "type": "report",
                        "text": report,
                        "detected": data.get("detected_data", {}),
                        "bandwidth_usage": len(report) + 500, # Ước lượng size bao gồm cả heatmap
                        "image_available_size": data.get("processed_size", 0),
                        
                        # --- DỮ LIỆU MỚI: HEATMAP ---
                        "heatmap": data.get("heatmap"),   # Ma trận dự đoán hướng lan
                        "grid_size": data.get("grid_size") # Kích thước lưới
                    }
                    
                    # Gửi qua WebSocket
                    await websocket.send_text(json.dumps(payload))
                    print(f"📡 [EDGE -> EARTH] Alert sent! (Predictive Heatmap included)")
                else:
                    print(f"✅ [EDGE] Area Safe. No transmission needed.")
            else:
                print(f"❌ [EDGE] AI Service Error: {response.status_code}")

        except Exception as e:
            print(f"❌ [EDGE] Connection Failed (Is ai_service.py running on 8001?): {e}")
            # Gửi thông báo lỗi về web để dễ debug
            try:
                await websocket.send_text(json.dumps({"type": "system", "text": "⚠️ LINK ERROR: Cannot connect to AI Brain."}))
            except:
                pass

        # Giả lập thời gian bay sang vùng khác (5 giây)
        await asyncio.sleep(5)


@app.websocket("/ws/satellite-stream")
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint để Frontend kết nối WebSocket"""
    await websocket.accept()
    try:
        await satellite_orbit_simulation(websocket)
    except WebSocketDisconnect:
        print("🔌 Ground station disconnected")


@app.get("/request-image")
def get_image_proxy():
    """
    API này được gọi khi người dùng bấm nút 'DOWNLOAD VISUAL EVIDENCE'.
    Edge Device sẽ đóng vai trò trung gian, lấy ảnh từ AI Service về trả cho Frontend.
    """
    print("📥 [EARTH -> EDGE] Requesting High-Res Visual...")
    
    try:
        # Gọi sang AI Service (Port 8001) để lấy ảnh gốc đang lưu trong RAM
        resp = requests.get(f"{AI_SERVICE_URL}/internal/latest-image")
        
        if resp.status_code == 200:
            # Chuyển đổi bytes sang base64 để React hiển thị được ngay
            b64_img = base64.b64encode(resp.content).decode('utf-8')
            print("🚀 [EDGE -> EARTH] Image Transmitted successfully!")
            return {"image": f"data:image/jpeg;base64,{b64_img}"}
        else:
            return {"error": "AI Service could not provide image (Maybe overwritten?)"}
            
    except Exception as e:
        return {"error": f"Failed to fetch from AI Service: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    print("🛰️  EDGE DEVICE GATEWAY RUNNING ON PORT 8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)