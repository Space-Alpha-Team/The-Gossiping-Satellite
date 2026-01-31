# �️ PROJECT A.E.G.I.S. - Autonomous Edge & Ground Intelligence System

> **Mission:** Predicting Fire Before It Spreads
> **Tagline:** The Shield from Above, The Mind on the Ground
> **Challenge:** Space 4.0 & Wildfire Detection/Prediction
> **Team:** SpaceUS

## 🎯 The Vision
In Greek mythology, Aegis was the ultimate shield of Zeus and Athena. PROJECT A.E.G.I.S. is the technological shield protecting forests from wildfire.

## 🚀 The Innovation
Traditional wildfire detection relies on **either** satellites **or** ground stations. We combine **both**.

- **A (Autonomous):** Satellite autonomously detects fire using advanced color algorithms (NBR Mask)
- **E (Edge):** Processing happens at the edge (on-board) with zero-latency compression via VAE Encoder
- **G (Ground):** Ground stations provide critical context (wind, slope, humidity) that satellites cannot see
- **I (Intelligence):** Fusion algorithm creates predictive intelligence (Fire Heatmap + Spread Simulation)
- **S (System):** Continuous handshake between satellite and ground for real-time prediction updates

**Result:** Real-time wildfire prediction with 99.99% bandwidth savings.

## 🛠️ Tech Stack
- **On-board AI (Backend):** Python, FastAPI, YOLOv8, OpenCV, Groq API (Llama-3), WebSockets
- **Ground Station (Frontend):** React, TailwindCSS, Vite, Canvas API for real-time heatmap visualization
- **Core Algorithm:** Red-Excess & Green-Blue-Excess for fire detection + Cellular Automata for fire spread simulation

## 📸 Demo
![Architecture](./demo-architecture.png)

## 🔑 Environment Setup (API Keys)

This project uses **Groq Cloud** (Llama-3) for high-speed on-board AI processing. Each team member must generate their own API Key to run the Backend.

### 1. Get a Free API Key
1. Visit: [Groq Console](https://console.groq.com/keys).
2. Log in using GitHub or Google.
3. Click **Create API Key**.
4. Name it (e.g., `ActInSpace_Dev`) and click Submit.
5. **Copy the key immediately** (it starts with `gsk_...`). You won't be able to see it again.

### 2. Configure Backend
You need to create an environment variable file to store your key (this file is git-ignored for security).

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create a new file named .env.
3. Open .env and paste the following content (Replace gsk_... with your actual key):
   ```bash
   # ⚠️ IMPORTANT: Keep the variable name as GROK_API_KEY to match the source code
   GROK_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

## 📦 Running
### 1. Backend
```bash
cd backend
pip install -r requirements.txt
python server.py
```
### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
