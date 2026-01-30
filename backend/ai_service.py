# backend/ai_service.py
# PORT 8001
import time
import math
import random
import cv2
import numpy as np
import os
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import Response
from ultralytics import YOLO
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# --- CẤU HÌNH MÔ PHỎNG ---
GRID_SIZE = 40          # Lưới 40x40
WIND_DIRECTION = (1, -1) # Gió thổi hướng Đông Bắc (x dương, y âm)
WIND_SPEED = 0.6        # Tốc độ lan truyền

# Load Models
# Lưu ý: yolov8n mặc định không có class 'fire', nên ta sẽ dựa nhiều vào thuật toán màu
vision_model = YOLO('yolov8n.pt') 
try:
    client = Groq(api_key=os.getenv("GROK_API_KEY"))
except:
    client = None
    print("⚠️ Warning: Groq API Key not found.")

# Kho lưu trữ ảnh tạm thời
SERVER_STORAGE = {"latest_image_bytes": None}

class FirePredictor:
    def __init__(self, grid_size=40):
        self.size = grid_size

    def create_grid_from_image(self, image_shape, boxes, img_array):
        """
        Kết hợp YOLO và Thuật toán màu (Red Excess) để tìm lửa
        """
        h, w = image_shape[:2]
        grid = np.zeros((self.size, self.size), dtype=float)
        
        scale_x = self.size / w
        scale_y = self.size / h

        # 1. Lấy dữ liệu từ YOLO (Nếu có)
        # Mặc dù yolov8n hay nhận diện nhầm, nhưng cứ giữ lại logic này để mở rộng sau
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            gx1, gy1 = int(x1 * scale_x), int(y1 * scale_y)
            gx2, gy2 = int(x2 * scale_x), int(y2 * scale_y)
            # Chỉ đánh dấu nếu box có độ tin cậy cao
            if box.conf > 0.3:
                grid[gy1:gy2, gx1:gx2] = 1.0

        # 2. Thuật toán Red-Excess (QUAN TRỌNG ĐỂ BẮT MÀU LỬA)
        if img_array is not None:
            # Resize ảnh về kích thước lưới (40x40) để tính toán siêu nhanh
            small_img = cv2.resize(img_array, (self.size, self.size))
            
            # Tách kênh màu (OpenCV dùng chuẩn BGR)
            B, G, R = cv2.split(small_img)
            
            # Công thức: Pixel nào có Rất nhiều Đỏ và ít Xanh lá/Xanh dương
            # Ép kiểu float để tính toán không bị tràn số
            red_excess = 2.0 * R.astype("float") - G.astype("float") - B.astype("float")
            
            # Chuẩn hóa về 0-1
            red_excess[red_excess < 0] = 0
            # Ngưỡng màu: Giá trị này càng cao thì càng lọc kỹ (tránh nhầm mái ngói đỏ)
            # Với ảnh đám cháy vệ tinh, ngưỡng 40-50 là ổn (trên thang 255)
            fire_mask = red_excess > 40.0 
            
            # Gán vào grid
            grid[fire_mask] = 1.0
            
        return grid

    def simulate_spread(self, current_grid):
        """
        Dự đoán lan truyền với hiệu ứng ĐỘNG (PULSE) theo thời gian thực
        """
        future_grid = current_grid.copy()
        
        # Tạo hiệu ứng "Thở": Số bước lan truyền thay đổi theo thời gian
        # Giúp heatmap trên màn hình trông như đang lan ra rồi thu lại
        t = time.time()
        # Sin chạy từ -1 đến 1 -> dynamic_steps chạy từ 2 đến 8
        dynamic_steps = int(5 + 3 * math.sin(t * 4)) 
        
        # Thêm chút nhiễu gió ngẫu nhiên để lửa trông tự nhiên
        wind_jitter_x = WIND_DIRECTION[0] + random.uniform(-0.3, 0.3)
        wind_jitter_y = WIND_DIRECTION[1] + random.uniform(-0.3, 0.3)

        for _ in range(dynamic_steps):
            new_grid = future_grid.copy()
            rows, cols = future_grid.shape
            
            for r in range(rows):
                for c in range(cols):
                    if future_grid[r, c] > 0.1: # Nếu ô đang nóng
                        # Lan sang hướng gió
                        nr, nc = int(r + wind_jitter_y), int(c + wind_jitter_x)
                        
                        if 0 <= nr < rows and 0 <= nc < cols:
                            # Cộng dồn nhiệt
                            new_grid[nr, nc] += future_grid[r, c] * WIND_SPEED
            
            # Giới hạn max nhiệt là 1.0
            future_grid = np.clip(new_grid, 0, 1)
            
        return future_grid

predictor = FirePredictor(GRID_SIZE)

@app.post("/internal/analyze")
async def analyze_image_service(file: UploadFile = File(...)):
    # 1. Đọc ảnh
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 2. Chạy YOLO (Lấy metadata)
    results = vision_model(img, conf=0.1) 
    result = results[0]
    
    detected = {}
    for box in result.boxes:
        name = result.names[int(box.cls[0])]
        detected[name] = detected.get(name, 0) + 1
        
    # 3. Lưu ảnh gốc vào RAM (Để Frontend tải về)
    # Lưu ý: Ta lưu ảnh gốc chưa vẽ box của YOLO để nhìn cho rõ, 
    # vì heatmap sẽ vẽ đè lên rồi.
    _, buffer = cv2.imencode('.jpg', img)
    SERVER_STORAGE["latest_image_bytes"] = buffer.tobytes()
    
    # 4. --- CHẠY MÔ PHỎNG (CORE) ---
    # B1: Tạo lưới hiện tại từ ảnh + YOLO
    current_grid = predictor.create_grid_from_image(img.shape, result.boxes, img_array=img)
    
    # B2: Tính toán dự đoán (Có hiệu ứng Pulse)
    future_grid = predictor.simulate_spread(current_grid)
    
    # B3: Kiểm tra xem có lửa không để báo cáo
    has_fire = np.max(current_grid) > 0.5
    
    # 5. Viết báo cáo SLM
    report_text = "SAFE - No thermal anomaly detected."
    if has_fire:
        if client:
            try:
                prompt = f"Wildfire detected. Wind: NE {WIND_SPEED*10}km/h. Objects: {detected}. Predict: Fire spreading North-East. Suggest 1 tactical action."
                chat = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.1-8b-instant",
                )
                report_text = chat.choices[0].message.content
            except:
                report_text = "ALERT: Fire Detected. AI Reasoning Unavailable."
        else:
            report_text = f"ALERT: Thermal Anomaly Detected! (Groq Unavailable)"

    return {
        "text_report": report_text,
        "detected_data": detected,
        "processed_size": len(buffer),
        "heatmap": future_grid.tolist(), # Gửi ma trận về Frontend
        "grid_size": GRID_SIZE
    }

@app.get("/internal/latest-image")
def get_stored_image():
    if SERVER_STORAGE["latest_image_bytes"]:
        return Response(content=SERVER_STORAGE["latest_image_bytes"], media_type="image/jpeg")
    return {"error": "No image stored"}

if __name__ == "__main__":
    import uvicorn
    print("🧠 W.I.S.E AI CORE RUNNING ON PORT 8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)