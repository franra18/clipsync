import React, { useState, useEffect } from 'react';
import { Play, Download, Loader2, Sparkles, AlertCircle, Video } from 'lucide-react';
import TimeInput from './TimeInput';

const API_BASE_URL = 'http://localhost:8000/api';

export default function App() {
    const [videoUrl, setVideoUrl] = useState('');
    const [startTime, setStartTime] = useState('00:00');
    const [endTime, setEndTime] = useState('00:00');

    const [jobId, setJobId] = useState(null);
    const [status, setStatus] = useState(null); // QUEUED, PROCESSING, COMPLETED, FAILED
    const [downloadUrl, setDownloadUrl] = useState(null);
    const [errorMsg, setErrorMsg] = useState(null);

    // Polling para consultar el estado
    useEffect(() => {
        if (!jobId || status === 'COMPLETED' || status === 'FAILED') return;

        const interval = setInterval(async () => {
            try {
                const res = await fetch(`${API_BASE_URL}/clips/${jobId}`);

                if (!res.ok) {
                    throw new Error(`Error en la API: ${res.status}`);
                }

                const data = await res.json();
                console.log('Estado del trabajo:', data);

                const currentStatus = data.status ? data.status.toUpperCase() : 'UNKNOWN';
                setStatus(currentStatus);

                if (currentStatus === 'COMPLETED') {
                    setDownloadUrl(data.download_url);
                    clearInterval(interval);
                } else if (currentStatus === 'FAILED') {
                    setErrorMsg('Ocurrió un error al procesar el vídeo.');
                    clearInterval(interval);
                }
            } catch (err) {
                console.error('Error durante el polling:', err);
            }
        }, 2000);

        return () => clearInterval(interval);
    }, [jobId, status]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setErrorMsg(null);
        setDownloadUrl(null);
        setJobId(null);
        setStatus('QUEUED');

        try {
            const res = await fetch(`${API_BASE_URL}/clips`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    video_url: videoUrl,
                    start_time: startTime,
                    end_time: endTime,
                }),
            });

            if (!res.ok) throw new Error('Error al enviar la solicitud al servidor');

            const data = await res.json();
            console.log('Job creado:', data);

            setJobId(data.job_id);
        } catch (err) {
            console.error(err);
            setErrorMsg(err.message);
            setStatus(null);
        }
    };

    return (
        <div className="max-w-4xl mx-auto px-4 py-12">
            <header className="text-center mb-10">
                <div className="inline-flex items-center gap-2 px-3 py-1 bg-amber-500/10 text-amber-400 rounded-full text-sm font-medium mb-3 border border-amber-500/20">
                    <Sparkles className="w-4 h-4" /> Generador de Verticales 9:16
                </div>
                <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                    ClipSync
                </h1>
                <p className="mt-2 text-slate-400 text-lg">
                    Convierte directos de YouTube/Twitch en clips verticales listos para TikTok o Reels.
                </p>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Formulario */}
                <form onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl flex flex-col justify-between">
                    <div className="space-y-5">
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">URL del vídeo original</label>
                            <input
                                type="url"
                                required
                                placeholder="https://www.youtube.com/watch?v=..."
                                value={videoUrl}
                                onChange={(e) => setVideoUrl(e.target.value)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-amber-500 transition-colors placeholder:text-slate-600"
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <TimeInput
                                label="Inicio (MM:SS)"
                                value={startTime}
                                onChange={setStartTime}
                            />
                            <TimeInput
                                label="Fin (MM:SS)"
                                value={endTime}
                                onChange={setEndTime}
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={status === 'QUEUED' || status === 'PROCESSING'}
                        className="mt-6 w-full bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold py-3 px-4 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                        {status === 'QUEUED' || status === 'PROCESSING' ? (
                            <>
                                <Loader2 className="w-5 h-5 animate-spin" /> Procesando Clip...
                            </>
                        ) : (
                            <>
                                <Play className="w-5 h-5 fill-slate-950" /> Generar Clip Vertical
                            </>
                        )}
                    </button>
                </form>

                {/* Estado y Reproductor */}
                <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl flex flex-col items-center justify-center min-h-[360px] relative overflow-hidden">
                    {errorMsg && (
                        <div className="text-center p-4 text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-2">
                            <AlertCircle className="w-5 h-5 flex-shrink-0" />
                            <span className="text-sm">{errorMsg}</span>
                        </div>
                    )}

                    {!status && !errorMsg && (
                        <div className="text-center text-slate-500 space-y-2">
                            <Video className="w-12 h-12 mx-auto stroke-[1.5]" />
                            <p className="text-sm">Configura la URL y los tiempos para previsualizar el resultado.</p>
                        </div>
                    )}

                    {(status === 'QUEUED' || status === 'PROCESSING') && (
                        <div className="text-center space-y-4">
                            <Loader2 className="w-12 h-12 text-amber-500 animate-spin mx-auto" />
                            <div>
                                <p className="font-semibold text-slate-200">
                                    {status === 'QUEUED' ? 'En cola de espera...' : 'Procesando y Renderizando...'}
                                </p>
                                <p className="text-xs text-slate-400 mt-1">
                                    Whisper transcribiendo audio y recortando rostro con OpenCV.
                                </p>
                            </div>
                        </div>
                    )}

                    {status === 'COMPLETED' && downloadUrl && (
                        <div className="w-full flex flex-col items-center gap-4">
                            <div className="w-[200px] aspect-[9/16] bg-black rounded-xl overflow-hidden shadow-2xl border border-slate-800">
                                <video src={downloadUrl} controls className="w-full h-full object-contain" />
                            </div>
                            <a
                                href={downloadUrl}
                                download
                                className="w-full bg-slate-800 hover:bg-slate-700 text-white font-medium py-2.5 px-4 rounded-xl transition-colors flex items-center justify-center gap-2 text-sm"
                            >
                                <Download className="w-4 h-4" /> Descargar Vídeo HD
                            </a>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
