import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Radio, Wifi, Download, AlertTriangle, Database } from 'lucide-react';

function App() {
  const [logs, setLogs] = useState([]);
  const [currentAlert, setCurrentAlert] = useState(null);
  const [satelliteImage, setSatelliteImage] = useState(null);
  const [loadingImage, setLoadingImage] = useState(false);
  const [isConnected, setIsConnected] = useState(false);

  // Auto-scroll terminal
  const logEndRef = useRef(null);
  const scrollToBottom = () => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  useEffect(scrollToBottom, [logs]);

  // Kết nối WebSocket
  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/satellite-stream");

    ws.onopen = () => {
      setIsConnected(true);
      addLog("SYSTEM", "Handshake established with Orbital Unit.");
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'report') {
        setCurrentAlert(data);
        setSatelliteImage(null); // Reset ảnh cũ khi có báo cáo mới
        addLog("INCOMING", `Msg Size: ${data.bandwidth_usage} bytes | Content: ${data.text}`);
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
    setLoadingImage(true);
    try {
      addLog("UPLOAD_REQ", "Initiating high-bandwidth transmission...");
      const res = await axios.get('http://localhost:8000/request-image');
      setSatelliteImage(res.data.image);
      addLog("SUCCESS", "Image received. Bandwidth consumed.");
    } catch (err) {
      console.error(err);
    }
    setLoadingImage(false);
  };

  return (
    <div className="min-h-screen bg-space-black p-8 font-mono text-green-500">
      {/* HEADER */}
      <header className="flex justify-between items-center mb-8 border-b border-green-900 pb-4">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-widest">GROUND CONTROL</h1>
          <p className="text-xs text-green-600">ACT-IN-SPACE 2026 // DEEP SPACE NETWORK</p>
        </div>
        <div className={`flex items-center gap-2 px-3 py-1 rounded ${isConnected ? 'bg-green-900/30' : 'bg-red-900/30'}`}>
          <Wifi size={18} className={isConnected ? "animate-pulse" : ""} />
          <span className="text-sm font-bold">{isConnected ? "SIGNAL LOCKED" : "SEARCHING..."}</span>
        </div>
      </header>

      <main className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* CỘT 1: NHẬT KÝ TÍN HIỆU (TERMINAL) */}
        <div className="lg:col-span-1 bg-black border border-green-800 p-4 rounded h-[500px] overflow-hidden flex flex-col">
          <h2 className="text-white font-bold mb-2 flex items-center gap-2"><Radio size={16}/> SIGNAL LOGS</h2>
          <div className="flex-1 overflow-y-auto space-y-2 text-xs opacity-80">
            {logs.map((log, i) => (
              <div key={i} className="border-l-2 border-green-900 pl-2 hover:bg-green-900/10">
                {log}
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        </div>

        {/* CỘT 2 & 3: MAIN DISPLAY */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* KHUNG CẢNH BÁO MỚI NHẤT */}
          <div className="bg-space-panel border border-neon-green p-6 rounded relative overflow-hidden">
            <div className="absolute top-0 right-0 p-2 opacity-20"><AlertTriangle size={100}/></div>
            
            <h2 className="text-xl text-white font-bold mb-4">LATEST TRANSMISSION</h2>
            
            {currentAlert ? (
              <div className="relative z-10">
                <div className="text-2xl text-neon-green font-bold mb-2 typewriter">
                  {currentAlert.text}
                </div>
                
                <div className="grid grid-cols-2 gap-4 mt-6 text-sm text-gray-400 bg-black/50 p-4 rounded">
                  <div>Detected: {JSON.stringify(currentAlert.detected)}</div>
                  <div>Report Size: <span className="text-white">{currentAlert.bandwidth_usage} Bytes</span></div>
                  <div>Pending Image: <span className="text-red-400">{(currentAlert.image_available_size/1024).toFixed(1)} KB</span></div>
                </div>

                {/* NÚT QUYẾT ĐỊNH DOWNLOAD */}
                {!satelliteImage && (
                  <div className="mt-6 flex items-center gap-4">
                    <div className="text-xs text-green-600 animate-pulse">
                      Waiting for command...
                    </div>
                    <button 
                      onClick={handleFetchImage}
                      disabled={loadingImage}
                      className="bg-green-600 hover:bg-green-500 text-black font-bold py-2 px-6 rounded flex items-center gap-2 transition-all shadow-[0_0_15px_#00FF41]"
                    >
                      {loadingImage ? "DOWNLOADING..." : "REQUEST VISUAL VERIFICATION"}
                      <Download size={18}/>
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-10 opacity-50">Scanning orbit... Standby for intel.</div>
            )}
          </div>

          {/* KHUNG HIỂN THỊ ẢNH (CHỈ HIỆN KHI ĐÃ DOWNLOAD) */}
          {satelliteImage && (
            <div className="bg-black border border-green-800 rounded p-2 animate-in fade-in duration-1000">
              <div className="flex justify-between items-center mb-2 px-2">
                <span className="text-xs font-bold text-neon-blue">VISUAL FEED RECONSTRUCTED</span>
                <span className="text-xs text-red-500 border border-red-500 px-1">CONFIDENTIAL</span>
              </div>
              <img src={satelliteImage} className="w-full h-auto rounded object-cover" alt="Satellite Evidence" />
            </div>
          )}

        </div>
      </main>
    </div>
  );
}

export default App;