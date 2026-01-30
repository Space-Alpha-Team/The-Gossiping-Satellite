# backend/edge_device.py
# CHẠY TRÊN PORT 8000
import asyncio
import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os
import random
import json
import base64

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cấu hình kết nối sang AI Service
AI_SERVICE_URL = "http://localhost:8001"
IMAGE_FOLDER = "satellite_images"

# Cache của Edge chỉ lưu text report mới nhất để đối chiếu
edge_state = {
    "last_report": None
}

async def satellite_orbit_simulation(websocket: WebSocket): 
    # Kiểm tra folder ảnh
    if not os.path.exists(IMAGE_FOLDER):
        os.makedirs(IMAGE_FOLDER)
        
    images = [f for f in os.listdir(IMAGE_FOLDER) if f.endswith(('.jpg', '.png'))]
    
    if not images:
        print(f"⚠️  WARNING: Folder '{IMAGE_FOLDER}' trống! Hãy bỏ ảnh vào.")
        return

    while True:
        # 1. Giả lập chụp ảnh
        img_name = random.choice(images)
        img_path = os.path.join(IMAGE_FOLDER, img_name)
        
        print(f"🛰️  [EDGE] Scanning: {img_name}")

        try:
            # 2. Gửi ảnh sang AI Service (Chỉ gửi đi, không mong nhận lại ảnh)
            with open(img_path, 'rb') as f:
                # Gửi POST request
                response = requests.post(f"{AI_SERVICE_URL}/internal/analyze", files={'file': f})
                
            if response.status_code == 200:
                data = response.json()
                report = data["text_report"]
                
                # Logic: Chỉ báo cáo nếu có vấn đề (Khác 'SAFE')
                if "SAFE" not in report:
                    edge_state["last_report"] = report
                    
                    # 3. Gửi Text Report về Frontend (React)
                    # Lưu ý: 'image_available_size' là để Front-end hiển thị dung lượng ước tính
                    payload = {
                        "type": "report",
                        "text": report,
                        "detected": data["detected_data"],
                        "bandwidth_usage": len(report), # Chỉ tốn vài bytes
                        "image_available_size": data["processed_size"] 
                    }
                    await websocket.send_text(json.dumps(payload))
                    print(f"📡 [EDGE -> GROUND] Alert sent: {report} (Img Size waiting: {data['processed_size']}B)")
                else:
                    print("✅ [EDGE] Status: SAFE. No transmission.")
            else:
                print("❌ [EDGE] Service Error:", response.text)

        except Exception as e:
            print(f"❌ [EDGE] Connection Failed (Is ai_service running?): {e}")

        # Nghỉ 5 giây trước khi bay sang vùng khác
        await asyncio.sleep(5)

@app.websocket("/ws/satellite-stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        await satellite_orbit_simulation(websocket)
    except WebSocketDisconnect:
        print("Ground station disconnected")

# --- API MỚI: LẤY ẢNH TỪ SERVER VỀ ---
@app.get("/request-image")
def get_image_proxy():
    print("📥 [GROUND -> EDGE] Requesting Image...")
    
    try:
        # 4. Edge Device gọi sang AI Service để lấy ảnh
        # Đây chính là lúc băng thông lớn được sử dụng
        resp = requests.get(f"{AI_SERVICE_URL}/internal/latest-image")
        
        if resp.status_code == 200:
            # Chuyển đổi bytes sang base64 để React dễ hiển thị
            b64_img = base64.b64encode(resp.content).decode('utf-8')
            print("🚀 [EDGE -> GROUND] Image Transmitted!")
            return {"image": f"data:image/jpeg;base64,{b64_img}"}
        else:
            return {"error": "AI Service could not provide image"}
            
    except Exception as e:
        return {"error": f"Failed to fetch from AI Service: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    print("🛰️  EDGE DEVICE GATEWAY RUNNING ON PORT 8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)