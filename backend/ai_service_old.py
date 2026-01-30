# backend/ai_service.py
# CHẠY TRÊN PORT 8001
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import Response
from ultralytics import YOLO
from groq import Groq
import cv2
import numpy as np
import base64
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Load Models
vision_model = YOLO('yolov8n.pt')
try:
    client = Groq(api_key=os.getenv("GROK_API_KEY"))
except:
    client = None
    print("⚠️ Warning: Groq API Key not found or invalid.")

# --- KHO LƯU TRỮ ẢNH TẠI SERVER (RAM) ---
# Tại đây chúng ta lưu bức ảnh cuối cùng đã được xử lý
SERVER_STORAGE = {
    "latest_image_bytes": None  # Lưu dạng bytes để trả về cho nhanh
}

@app.post("/internal/analyze")
async def analyze_image_service(file: UploadFile = File(...)):
    # 1. Đọc ảnh raw từ Edge gửi lên
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 2. Xử lý Vision (YOLO)
    results = vision_model(img, conf=0.1)
    result = results[0]
    
    detected = {}
    for box in result.boxes:
        name = result.names[int(box.cls[0])]
        detected[name] = detected.get(name, 0) + 1
        
    # 3. Vẽ Box và LƯU ẢNH TẠI SERVER (Không trả về Edge ngay)
    annotated_frame = result.plot()
    _, buffer = cv2.imencode('.jpg', annotated_frame)
    
    # >> LƯU VÀO KHO <<
    SERVER_STORAGE["latest_image_bytes"] = buffer.tobytes()
    
    # 4. Tạo báo cáo Text (Groq)
    if not detected:
        report_text = "SAFE - No objects detected."
    else:
        if client:
            prompt = f"Objects: {detected}. Write a 10-word military alert. Format: [ALERT] msg."
            try:
                chat = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.1-8b-instant",
                )
                report_text = chat.choices[0].message.content
            except Exception as e:
                report_text = f"AI ERROR: {str(e)}"
        else:
            report_text = f"DETECTED: {detected} (Groq AI Unavailable)"

    # 5. CHỈ TRẢ VỀ TEXT VÀ METADATA (Siêu nhẹ)
    # Edge Device sẽ nhận gói tin này, cực kỳ tiết kiệm băng thông
    return {
        "text_report": report_text,
        "detected_data": detected,
        "original_size": len(contents),      # Size ảnh gốc
        "processed_size": len(buffer),       # Size ảnh đã vẽ (đang lưu ở Server)
        "image_available": True              # Cờ báo hiệu "Server đang giữ ảnh nè"
    }

@app.get("/internal/latest-image")
def get_stored_image():
    """API để Edge Device gọi khi cần lấy ảnh"""
    if SERVER_STORAGE["latest_image_bytes"]:
        # Trả về trực tiếp dòng bytes của ảnh
        return Response(content=SERVER_STORAGE["latest_image_bytes"], media_type="image/jpeg")
    return {"error": "No image stored"}

if __name__ == "__main__":
    import uvicorn
    print("🧠 AI BRAIN SERVICE RUNNING ON PORT 8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)