import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Wifi, Download, AlertTriangle, Wind, ShieldCheck, Zap } from 'lucide-react';

function App() {
  const [logs, setLogs] = useState([]);
  const [currentAlert, setCurrentAlert] = useState(null);
  const [satelliteImage, setSatelliteImage] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [heatmap, setHeatmap] = useState(null);

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

  // --- RENDER GRID (Đã fix lỗi sọc đỏ) ---
  const renderGrid = () => {
    if (!heatmap) return null;
    return (
      <div 
        className="absolute inset-0 grid z-20" // Z-20 để nằm đè lên ảnh
        style={{
          // Ép cứng số cột và hàng để Tailwind không bị lỗi
          gridTemplateColumns: `repeat(40, minmax(0, 1fr))`,
          gridTemplateRows: `repeat(40, minmax(0, 1fr))`
        }}
      >
        {heatmap.map((row, r) => 
          row.map((val, c) => {
            let color = '';
            // Heatmap styling:
            // > 0.8: Vùng cháy gốc (Đỏ đậm, chớp tắt)
            if (val > 0.8) color = 'bg-red-600/60 shadow-[0_0_8px_rgba(255,0,0,0.8)]'; 
            // > 0.1: Vùng dự đoán lan (Cam nhạt)
            else if (val > 0.1) color = 'bg-orange-500/40'; 
            
            return (
              <div key={`${r}-${c}`} className={`${color} transition-all duration-300 rounded-[1px]`} />
            );
          })
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#050505] text-green-500 font-mono p-6 overflow-hidden selection:bg-green-900 selection:text-white">
      {/* HEADER */}
      <header className="flex justify-between items-center border-b border-green-900/50 pb-4 mb-6">
        <div>
          <h1 className="text-4xl font-black tracking-[0.2em] text-white flex items-center gap-3">
            <Zap size={32} className="text-yellow-500"/> W.I.S.E <span className="text-green-600 text-sm tracking-normal font-normal opacity-70">PROMETHEUS CORE</span>
          </h1>
          <p className="text-[10px] text-gray-500 uppercase tracking-widest mt-1">Wireless Intelligence Satellite Edge // Fire Prediction System</p>
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
        <div className="col-span-4 flex flex-col gap-4">
          
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
          <div className="flex-1 bg-black border border-green-900/30 p-3 rounded overflow-hidden flex flex-col font-mono text-[10px] shadow-inner relative">
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
          <div className="absolute inset-0 flex items-center justify-center z-0">
             {satelliteImage ? (
               // QUAN TRỌNG: w-full h-full để ép ảnh khớp với grid 40x40
               <img src={satelliteImage} className="w-full h-full object-fill opacity-70" alt="Satellite Feed" />
             ) : (
               <div className="flex flex-col items-center opacity-20 space-y-2">
                 <div className="text-6xl font-black text-green-900 tracking-tighter">NO SIGNAL</div>
                 <div className="text-xs text-green-800 tracking-[0.3em]">WAITING FOR VISUAL DATA PACKET...</div>
               </div>
             )}
          </div>

          {/* LỚP 2: HEATMAP GRID (DỮ LIỆU SỐ) */}
          {/* mix-blend-plus-lighter giúp màu lửa rực rỡ hơn trên nền tối */}
          <div className="relative w-full h-full z-10 mix-blend-plus-lighter">
             {heatmap && renderGrid()}
             
             {/* HUD Overlay (Giao diện kính phi công) */}
             <div className="absolute top-4 left-4">
                <div className="bg-black/80 px-3 py-2 text-xs text-orange-400 border-l-2 border-orange-500 backdrop-blur-md shadow-lg">
                  <div className="font-bold text-white mb-1">SIMULATION_MODE</div>
                  <div className="text-[10px] opacity-80">ALGO: CELLULAR AUTOMATA</div>
                  <div className="text-[10px] opacity-80">PREDICTION: T+30 MINS</div>
                </div>
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