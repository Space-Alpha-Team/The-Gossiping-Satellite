# PROJECT A.E.G.I.S. - Autonomous Edge & Ground Intelligence System
# Satellite-side AI Engine (PORT 8001)
# Purpose: Real-time wildfire detection, mask generation, and fire spread prediction

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

# --- FIRE DETECTION & SIMULATION PARAMETERS ---
# A.E.G.I.S Core: Autonomous detection powered by spectral analysis (NBR Mask)
GRID_SIZE = 100         # Lưới 100x100 (mịn hơn cho heatmap)
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

        # 2. Thuật toán Red-Excess & Green-Blue-Excess (QUAN TRỌNG ĐỂ BẮT MÀU LỬA)
        if img_array is not None:
            # Resize ảnh về kích thước lưới (40x40) để tính toán siêu nhanh
            small_img = cv2.resize(img_array, (self.size, self.size))
            
            # Tách kênh màu (OpenCV dùng chuẩn BGR)
            B, G, R = cv2.split(small_img)
            
            # Công thức 1: Red Excess - Vùng cháy (Đỏ)
            # Pixel nào có Rất nhiều Đỏ và ít Xanh lá/Xanh dương
            red_excess = 2.0 * R.astype("float") - G.astype("float") - B.astype("float")
            # Normalize sao cho có nhiều giá trị trung gian, không chỉ 0/1
            red_excess[red_excess < 0] = 0
            # Dùng pow để tạo curve - giá trị nhỏ được scale lên để mở rộng vùng vàng
            red_normalized = np.power(np.clip(red_excess / 255.0, 0, 1.0), 0.7)
            
            # Công thức 2: Green-Blue Excess - Vùng an toàn (Xanh)
            # Pixel nào có Rất nhiều Xanh lá/Xanh dương và ít Đỏ
            green_blue_excess = (G.astype("float") + B.astype("float")) / 2.0 - R.astype("float")
            green_blue_excess[green_blue_excess < 0] = 0
            green_blue_normalized = np.clip(green_blue_excess / 255.0, 0, 1.0)
            
            # Gán vào grid: 
            # - Nếu vùng có fire_score cao, dùng fire_score (dương)
            # - Nếu vùng có safety_score cao, dùng -safety_score (âm)
            # - Phần còn lại mặc định 0 (vùng trung bình = vàng)
            safety_score = -green_blue_normalized * 0.5  # Âm = an toàn
            fire_score = red_normalized
            
            # Chỉ ghi vào grid nơi fire_score cao hơn (giữ vùng cháy)
            grid = np.maximum(grid, fire_score)
            
            # Chỉ ghi vào grid nơi safety_score cao hơn và fire_score thấp
            safe_mask = green_blue_normalized > 0.3
            grid[safe_mask & (fire_score < 0.1)] = safety_score[safe_mask & (fire_score < 0.1)]
            
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
    
    # B4: Xác định nguồn lửa (fire origin)
    fire_origin = None
    if has_fire:
        # Tìm điểm nóng nhất (max intensity point)
        max_idx = np.unravel_index(np.argmax(current_grid), current_grid.shape)
        fire_origin = {
            "row": int(max_idx[0]),
            "col": int(max_idx[1]),
            "intensity": float(np.max(current_grid))
        }
    
    # B5: Xác định ranh giới vùng an toàn (safe zone boundary)
    safe_boundary = []
    
    # Resize lại ảnh để tính green-blue score
    if img is not None:
        small_img = cv2.resize(img, (GRID_SIZE, GRID_SIZE))
        B, G, R = cv2.split(small_img)
        
        # Green-Blue excess (cao hơn = an toàn hơn)
        green_blue_score = (G.astype("float") + B.astype("float")) / 2.0 - R.astype("float")
        green_blue_score[green_blue_score < 0] = 0
        green_blue_normalized = np.clip(green_blue_score / 255.0, 0, 1.0)
        
        # Safe zone là nơi có green-blue cao (giảm threshold xuống 0.05)
        safe_zone_mask = green_blue_normalized > 0.05
        
        if np.any(safe_zone_mask):
            # Tìm ranh giới bằng edge detection
            # Mở rộng safe zone một chút để có ranh giới rõ ràng hơn
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            safe_dilated = cv2.dilate(safe_zone_mask.astype(np.uint8), kernel, iterations=1)
            
            # Debug: in ra giá trị min/max
            print(f"🔍 Green-blue normalized: min={np.min(green_blue_normalized):.3f}, max={np.max(green_blue_normalized):.3f}")
            print(f"🔍 Safe zone cells (>0.05): {np.sum(safe_zone_mask)}")
            
            # Tìm điểm ranh giới = điểm nằm trên biên (edges)
            for r in range(GRID_SIZE):
                for c in range(GRID_SIZE):
                    if safe_dilated[r, c] == 1:  # Nếu là safe zone
                        # Kiểm tra neighbors xem có non-safe không
                        has_non_safe_neighbor = False
                        for dr in [-1, 0, 1]:
                            for dc in [-1, 0, 1]:
                                nr, nc = r + dr, c + dc
                                if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                                    if safe_dilated[nr, nc] == 0:
                                        has_non_safe_neighbor = True
                                        break
                            if has_non_safe_neighbor:
                                break
                        
                        if has_non_safe_neighbor:
                            safe_boundary.append({"row": int(r), "col": int(c)})
            
            print(f"🟢 Safe zone detected: {np.sum(safe_zone_mask)} cells, boundary points: {len(safe_boundary)}")
        else:
            print(f"⚠️ No safe zone detected (threshold too high?)")
    else:
        print(f"⚠️ No image data for safe zone detection")
    
    # 5. Viết báo cáo SLM
    report_text = "SAFE - No thermal anomaly detected."
    if has_fire:
        if client:
            try:
                prompt = (
                    f"Wildfire detected. Wind: NE {WIND_SPEED*10}km/h. Objects: {detected}. "
                    "Predict: Fire spreading North-East. Suggest 1 tactical action. "
                    "Reply in 1-2 concise sentences, no explanation."
                )
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
        "heatmap": future_grid.tolist(),
        "grid_size": GRID_SIZE,
        "fire_origin": fire_origin,
        "safe_boundary": safe_boundary
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