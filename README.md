# 🛰️ The Gossiping Satellite - ActInSpace 2026

> **Challenge:** Space 4.0 & Data Compression
> **Team:** SpaceUS

## 🚀 The Problem
Satellite imagery is heavy (GBs). Transmitting raw data takes too much bandwidth, time, and energy.

## 💡 The Solution: Edge AI
Instead of sending images, our satellite **thinks** and **speaks**.
It processes images on-board using **YOLOv8** and generates a text-based intelligence report using **Llama-3 (Groq)**.

**Result:** 99.99% Bandwidth Savings.

## 🛠️ Tech Stack
- **On-board AI (Backend):** Python, FastAPI, YOLOv8, Groq API (Llama-3), WebSockets.
- **Ground Station (Frontend):** React, TailwindCSS, Vite.

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
