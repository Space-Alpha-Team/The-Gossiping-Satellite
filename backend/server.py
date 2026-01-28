import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from groq import Groq
import cv2
import numpy as np
import base64
import os
import random
import json
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- KHỞI TẠO ---
vision_model = YOLO('yolov8n.pt')
client = Groq(api_key=os.getenv("GROK_API_KEY"))

# Biến toàn cục lưu trạng thái hiện tại của vệ tinh
current_satellite_state = {
    "latest_image_base64": None, # Chỉ gửi khi được yêu cầu
    "latest_image_size": 0
}

# Danh sách ảnh để giả lập quét
IMAGE_FOLDER = "satellite_images"
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)
    print(f"⚠️ CẢNH BÁO: Hãy bỏ ảnh vào thư mục '{IMAGE_FOLDER}' để chạy demo!")

async def simulated_satellite_orbit(websocket: WebSocket):
    """Hàm giả lập vệ tinh bay và quét định kỳ"""
    images = [f for f in os.listdir(IMAGE_FOLDER) if f.endswith(('.jpg', '.png'))]
    
    if not images:
        await websocket.send_text(json.dumps({"type": "error", "message": "No images found in folder"}))
        return

    while True:
        # 1. Chọn ngẫu nhiên 1 vùng (ảnh) để quét
        img_name = random.choice(images)
        img_path = os.path.join(IMAGE_FOLDER, img_name)
        
        # 2. Xử lý Vision (Edge Computing trên vệ tinh)
        img = cv2.imread(img_path)
        original_size = os.path.getsize(img_path)
        
        results = vision_model(img, conf=0.1)
        result = results[0]
        print(f"🔍 DEBUG: Found {len(result.boxes)} objects in {img_name}")
        
        # Đếm vật thể
        detected = {}
        for box in result.boxes:
            name = result.names[int(box.cls[0])]
            detected[name] = detected.get(name, 0) + 1
        
        # 3. Tạo báo cáo (LLM Reasoning)
        prompt = f"Objects: {detected}. Write a 15-word military alert. Format: [LEVEL] content."
        try:
            chat = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
            )
            report_text = chat.choices[0].message.content
        except:
            report_text = "[ERROR] CONNECTION LOST"

        # 4. Lưu ảnh đã xử lý vào bộ nhớ tạm (nhưng KHÔNG GỬI NGAY)
        annotated_frame = result.plot()
        _, buffer = cv2.imencode('.jpg', annotated_frame)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        current_satellite_state["latest_image_base64"] = img_base64
        current_satellite_state["latest_image_size"] = original_size

        # 5. CHỈ GỬI TEXT REPORT (Tiết kiệm băng thông)
        payload = {
            "type": "report",
            "text": report_text,
            "detected": detected,
            "bandwidth_usage": len(report_text.encode('utf-8')), # Rất nhỏ (bytes)
            "image_available_size": original_size # Báo là có ảnh to đang chờ
        }
        
        await websocket.send_text(json.dumps(payload))
        
        # Giả lập vệ tinh bay sang vùng khác sau 10 giây
        await asyncio.sleep(10)

@app.websocket("/ws/satellite-stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        await simulated_satellite_orbit(websocket)
    except WebSocketDisconnect:
        print("Ground station disconnected")

@app.get("/request-image")
def get_high_res_image():
    """Chỉ gọi API này khi người dùng bấm nút Verify"""
    if current_satellite_state["latest_image_base64"]:
        return {
            "image": f"data:image/jpeg;base64,{current_satellite_state['latest_image_base64']}"
        }
    return {"error": "No image available"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)