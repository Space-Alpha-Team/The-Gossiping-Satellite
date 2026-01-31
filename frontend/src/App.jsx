import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Wifi, Download, AlertTriangle, Wind, ShieldCheck, Zap, Eye, EyeOff } from 'lucide-react';

function App() {
  const [logs, setLogs] = useState([]);
  const [currentAlert, setCurrentAlert] = useState(null);
  const [satelliteImage, setSatelliteImage] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [heatmap, setHeatmap] = useState(null);
  const [fireOrigin, setFireOrigin] = useState(null);
  const [safeBoundary, setSafeBoundary] = useState(null);
  const [showSatelliteImage, setShowSatelliteImage] = useState(true);

  // Canvas reference cho heatmap rendering
  const canvasRef = useRef(null);

  // Tự động cuộn log xuống cuối
  const logEndRef = useRef(null);
  useEffect(() => logEndRef.current?.scrollIntoView({ behavior: "smooth" }), [logs]);

  // --- WEBSOCKET LOGIC ---
  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/satellite-stream");

    ws.onopen = () => { 
      setIsConnected(true); 
      addLog("SYSTEM", "Uplink established with W.I.S.E Satellite."); 
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'report') {
        setCurrentAlert(data);
        // Cập nhật heatmap liên tục để tạo hiệu ứng động
        setHeatmap(data.heatmap);
        // Nhận vị trí nguồn lửa
        if (data.fire_origin) {
          console.log('Fire origin received:', data.fire_origin);
          setFireOrigin(data.fire_origin);
        }
        // Nhận ranh giới vùng an toàn
        if (data.safe_boundary) {
          console.log('Safe boundary received:', data.safe_boundary.length, 'points');
          setSafeBoundary(data.safe_boundary);
        } else {
          console.log('No safe boundary in data');
          setSafeBoundary(null);
        }
        
        // Không xóa ảnh cũ! Chỉ cập nhật lớp phủ lên trên
        addLog("TELEMETRY", `Fire spread prediction updated. Msg Size: ${data.bandwidth_usage}B`);
      } else if (data.type === 'system') {
        addLog("SYSTEM", data.text);
      }
    };

    ws.onclose = () => setIsConnected(false);
    return () => ws.close();
  }, []);

  const addLog = (source, msg) => {
    const time = new Date().toLocaleTimeString();
    setLogs(prev => [...prev, `[${time}] [${source}] ${msg}`]);
  };

  const handleFetchImage = async () => {
    try {
      addLog("DL_REQ", "Requesting High-Res Visual verification...");
      // Gọi qua Edge Device (Port 8000)
      const res = await axios.get('http://localhost:8000/request-image');
      if (res.data.image) {
        setSatelliteImage(res.data.image);
        addLog("SUCCESS", "Visual data received & reconstructed.");
      } else {
        addLog("ERROR", "Image buffer empty or overwritten.");
      }
    } catch (err) { 
      console.error(err);
      addLog("ERROR", "Downlink failed.");
    }
  };

  // --- CANVAS RENDERING cho HEATMAP (Hiệu năng cao) ---
  const renderHeatmapToCanvas = () => {
    if (!heatmap || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const gridSize = heatmap.length;
    const cellSize = canvas.width / gridSize;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (let r = 0; r < gridSize; r++) {
      for (let c = 0; c < gridSize; c++) {
        const val = heatmap[r][c];
        let fillColor = '';

        if (val > 0.8) {
          const intensity = Math.min(1, val);
          fillColor = `rgba(220, 20, 20, ${0.6 * intensity})`;
        } else if (val > 0.0001) {
          const intensity = (val - 0.0001) / 0.7999;
          fillColor = `rgba(255, 165, 0, ${0.4 * intensity})`;
        } else if (val < -0.01) {
          const intensity = Math.min(1, Math.abs(val));
          fillColor = `rgba(34, 197, 94, ${0.5 * intensity})`;
        } else {
          continue;
        }

        ctx.fillStyle = fillColor;
        ctx.fillRect(c * cellSize, r * cellSize, cellSize, cellSize);
      }
    }

    // Vẽ ranh giới vùng an toàn
    if (safeBoundary && safeBoundary.length > 0) {
      console.log('Drawing safe boundary with', safeBoundary.length, 'points');
      
      // Vẽ các điểm trên ranh giới
      safeBoundary.forEach(point => {
        const x = (point.col + 0.5) * cellSize;
        const y = (point.row + 0.5) * cellSize;
        
        // Vẽ hình vuông nhỏ màu xanh
        ctx.fillStyle = 'rgba(34, 197, 94, 0.9)';
        ctx.fillRect(x - cellSize * 0.15, y - cellSize * 0.15, cellSize * 0.3, cellSize * 0.3);
        
        // Vẽ outline trắng để nổi bật
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
        ctx.lineWidth = 1;
        ctx.strokeRect(x - cellSize * 0.15, y - cellSize * 0.15, cellSize * 0.3, cellSize * 0.3);
      });
    }

    // Vẽ nguồn lửa (fire origin) - Ngọn lửa rực cháy với outline
    if (fireOrigin) {
      console.log('Drawing fire origin at:', fireOrigin, 'Grid size:', gridSize);
      const x = (fireOrigin.col + 0.5) * cellSize;
      const y = (fireOrigin.row + 0.5) * cellSize;
      const fireSize = cellSize * 1.2;

      // Vẽ vùng cảnh báo trắng lớn (outer halo)
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.arc(x, y, fireSize * 1.5, 0, 2 * Math.PI);
      ctx.stroke();

      // Vẽ vùng cảnh báo trắng giữa
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(x, y, fireSize * 1.1, 0, 2 * Math.PI);
      ctx.stroke();

      // Tạo gradient cho ngọn lửa
      const gradient = ctx.createLinearGradient(x, y + fireSize, x, y - fireSize);
      gradient.addColorStop(0, 'rgba(255, 100, 0, 1)');      // Cam phía dưới
      gradient.addColorStop(0.5, 'rgba(255, 20, 0, 1)');     // Đỏ sậm ở giữa
      gradient.addColorStop(1, 'rgba(255, 255, 0, 0.9)');    // Vàng phía trên

      // Vẽ phần thân lửa (hình elipse)
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.ellipse(x, y, fireSize * 0.4, fireSize * 0.8, 0, 0, 2 * Math.PI);
      ctx.fill();

      // Vẽ ngọn lửa bên trái
      ctx.beginPath();
      ctx.ellipse(x - fireSize * 0.3, y - fireSize * 0.2, fireSize * 0.3, fireSize * 0.6, -0.3, 0, 2 * Math.PI);
      ctx.fill();

      // Vẽ ngọn lửa bên phải
      ctx.beginPath();
      ctx.ellipse(x + fireSize * 0.3, y - fireSize * 0.2, fireSize * 0.3, fireSize * 0.6, 0.3, 0, 2 * Math.PI);
      ctx.fill();

      // Vẽ phần lõi lửa (vàng sáng ở giữa)
      const coreGradient = ctx.createRadialGradient(x, y, 0, x, y, fireSize * 0.3);
      coreGradient.addColorStop(0, 'rgba(255, 255, 150, 1)');
      coreGradient.addColorStop(1, 'rgba(255, 150, 0, 0.5)');
      ctx.fillStyle = coreGradient;
      ctx.beginPath();
      ctx.ellipse(x, y, fireSize * 0.3, fireSize * 0.5, 0, 0, 2 * Math.PI);
      ctx.fill();

      // Vẽ outline trắng xung quanh toàn bộ lửa để nổi bật
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.ellipse(x, y, fireSize * 0.4, fireSize * 0.8, 0, 0, 2 * Math.PI);
      ctx.stroke();
    }
  };

  useEffect(() => {
    renderHeatmapToCanvas();
  }, [heatmap, fireOrigin, safeBoundary]);

  return (
    <div className="min-h-screen bg-[#050505] text-green-500 font-mono p-6 overflow-hidden selection:bg-green-900 selection:text-white">
      {/* HEADER */}
      <header className="flex justify-between items-center border-b border-green-900/50 pb-4 mb-6">
        <div>
          <h1 className="text-4xl font-black tracking-[0.2em] text-white flex items-center gap-3">
            <Zap size={32} className="text-yellow-500"/> PROJECT A.E.G.I.S. <span className="text-green-600 text-sm tracking-normal font-normal opacity-70">GROUND COMMAND</span>
          </h1>
          <p className="text-[10px] text-gray-500 uppercase tracking-widest mt-1">Autonomous Edge & Ground Intelligence System // Predicting Fire Before It Spreads</p>
        </div>
        <div className="flex gap-4">
          <div className="flex items-center gap-2 text-yellow-500 border border-yellow-900/30 px-3 py-1 rounded bg-yellow-900/10">
            <Wind size={18} className="animate-pulse" />
            <span className="text-xs font-bold">WIND: NE 15km/h</span>
          </div>
          <div className={`flex items-center gap-2 px-3 py-1 rounded transition-colors duration-500 ${isConnected ? 'bg-green-900/20 text-green-400 border border-green-900/50' : 'bg-red-900/20 text-red-400 border border-red-900/50'}`}>
            <Wifi size={18} />
            <span className="text-xs font-bold">{isConnected ? "UPLINK STABLE" : "OFFLINE"}</span>
          </div>
        </div>
      </header>

      <main className="grid grid-cols-12 gap-6 h-[80vh]">
        
        {/* LEFT COLUMN: CONTROL & LOGS */}
        <div className="col-span-4 flex flex-col gap-4 h-full max-h-[80vh]">
          
          {/* ALERT & ACTION BOX */}
          <div className="bg-gray-900/50 border border-red-500/30 p-5 rounded relative overflow-hidden group hover:border-red-500/60 transition-colors">
            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity"><AlertTriangle size={100} className="text-red-500"/></div>
            
            <h2 className="text-xl text-white font-bold mb-3 flex items-center gap-2">
              <ShieldCheck size={20} className="text-green-400"/> TACTICAL ADVISOR
            </h2>
            
            {currentAlert ? (
              <div className="relative z-10 space-y-4">
                <div className="text-2xl text-red-500 font-black animate-pulse tracking-wide">
                  DETECTED
                </div>
                
                {/* SLM Report Text */}
                <div className="text-sm text-green-300 border-l-2 border-green-500/50 pl-3 italic opacity-90 leading-relaxed">
                  "{currentAlert.text}"
                </div>

                {/* Data Stats */}
                <div className="grid grid-cols-2 gap-2 text-[10px] text-gray-400 bg-black/40 p-2 rounded">
                    <div>OBJ: {Object.keys(currentAlert.detected).join(", ") || "Unknown"}</div>
                    <div>SIZE: {currentAlert.bandwidth_usage} Bytes</div>
                </div>

                {/* Download Button */}
                <button 
                  onClick={handleFetchImage} 
                  className={`w-full py-3 rounded font-bold text-xs tracking-wider flex justify-center items-center gap-2 transition-all duration-300 shadow-[0_0_20px_rgba(0,0,0,0.5)]
                    ${satelliteImage 
                      ? 'bg-gray-800 text-gray-400 border border-gray-700 hover:bg-gray-700' 
                      : 'bg-red-600 text-white hover:bg-red-500 shadow-[0_0_10px_rgba(220,38,38,0.4)]'
                    }`}
                >
                  <Download size={16}/> {satelliteImage ? "REFRESH VISUAL" : "DOWNLOAD VISUAL EVIDENCE"}
                </button>
              </div>
            ) : (
              <div className="text-center py-10 text-gray-600 text-sm animate-pulse">Scanning Orbit Sector...</div>
            )}
          </div>

          {/* TERMINAL LOGS */}
          <div className="flex-1 bg-black border border-green-900/30 p-3 rounded overflow-hidden flex flex-col font-mono text-[10px] shadow-inner relative min-h-0">
            <div className="absolute top-0 right-0 px-2 py-1 text-green-800 font-bold opacity-50">TERM_V1</div>
            <div className="flex-1 overflow-y-auto space-y-1 scrollbar-hide pr-2">
              {logs.map((log, i) => (
                <div key={i} className="hover:bg-green-900/10 px-1 border-l-2 border-transparent hover:border-green-600 transition-all text-gray-300">
                  <span className="text-green-600 font-bold">{log.split(']')[0]}]</span> {log.split(']')[1]}
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: TACTICAL MAP (DIGITAL TWIN) */}
        <div className="col-span-8 bg-black border border-green-800/50 rounded-lg relative overflow-hidden flex items-center justify-center bg-[url('https://www.transparenttextures.com/patterns/dark-matter.png')] shadow-[inset_0_0_50px_rgba(0,0,0,0.8)]">
          
          {/* LỚP 1: ẢNH VỆ TINH GỐC (NỀN) */}
          <div className={`absolute inset-0 flex items-center justify-center z-0 ${showSatelliteImage ? 'opacity-70' : 'opacity-0'} transition-opacity duration-300`}>
             {satelliteImage ? (
               // QUAN TRỌNG: w-full h-full để ép ảnh khớp với grid 40x40
               <img src={satelliteImage} className="w-full h-full object-fill" alt="Satellite Feed" />
             ) : (
               <div className="flex flex-col items-center opacity-20 space-y-2">
                 <div className="text-6xl font-black text-green-900 tracking-tighter">NO SIGNAL</div>
                 <div className="text-xs text-green-800 tracking-[0.3em]">WAITING FOR VISUAL DATA PACKET...</div>
               </div>
             )}
          </div>

          {/* LỚP 2: HEATMAP CANVAS (DỮ LIỆU SỐ) */}
          {/* mix-blend-plus-lighter giúp màu lửa rực rỡ hơn trên nền tối */}
          <div className="relative w-full h-full z-10 mix-blend-plus-lighter">
             {heatmap && (
               <canvas
                 ref={canvasRef}
                 className="absolute inset-0 w-full h-full"
                 width={400}
                 height={400}
               />
             )}
             
             {/* HUD Overlay (Giao diện kính phi công) */}
             <div className="absolute top-4 left-4 flex gap-3">
                <div className="bg-black/80 px-3 py-2 text-xs text-orange-400 border-l-2 border-orange-500 backdrop-blur-md shadow-lg">
                  <div className="font-bold text-white mb-1">SIMULATION_MODE</div>
                  <div className="text-[10px] opacity-80">ALGO: CELLULAR AUTOMATA</div>
                  <div className="text-[10px] opacity-80">PREDICTION: T+30 MINS</div>
                </div>
                
                {/* Toggle Satellite Image Button */}
                <button
                  onClick={() => setShowSatelliteImage(!showSatelliteImage)}
                  className="bg-black/80 px-3 py-2 text-xs border border-green-600/50 rounded backdrop-blur-md shadow-lg hover:bg-black/60 transition-colors flex items-center gap-2 text-green-400"
                  title={showSatelliteImage ? 'Hide satellite image' : 'Show satellite image'}
                >
                  {showSatelliteImage ? <Eye size={14} /> : <EyeOff size={14} />}
                  <span className="text-[10px]">{showSatelliteImage ? 'HIDE' : 'SHOW'}</span>
                </button>
             </div>
             
             {/* Legend */}
             <div className="absolute bottom-4 right-4 bg-black/90 p-3 text-[10px] border border-gray-800 rounded backdrop-blur-md shadow-lg">
               <div className="flex items-center gap-2 mb-1"><div className="w-2 h-2 bg-red-600 shadow-[0_0_5px_red] rounded-full"></div> CURRENT FIRE FRONT</div>
               <div className="flex items-center gap-2"><div className="w-2 h-2 bg-orange-500/50 rounded-full"></div> PREDICTED SPREAD ZONE</div>
             </div>
          </div>

          {/* Scan Line Effect (Hiệu ứng quét radar) */}
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-green-500/5 to-transparent h-[10%] w-full animate-scan pointer-events-none z-30"></div>

        </div>
      </main>
    </div>
  );
}

export default App;