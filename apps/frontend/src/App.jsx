import React, { useState, useEffect } from 'react';
import { Play, Download, Loader2, AlertCircle, Video, Check } from 'lucide-react';
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
                const currentStatus = data.status ? data.status.toUpperCase() : 'UNKNOWN';
                setStatus(currentStatus);
                setErrorMsg(null);

                if (currentStatus === 'COMPLETED') {
                    setDownloadUrl(data.download_url);
                    clearInterval(interval);
                } else if (currentStatus === 'FAILED') {
                    setErrorMsg(data.error || 'Ocurrió un error al procesar el vídeo.');
                    clearInterval(interval);
                }
            } catch (err) {
                console.error('Error durante el polling:', err);
                // Se sigue consultando: la API puede estar reiniciándose (--reload)
                setErrorMsg('No se puede contactar con la API. Reintentando...');
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

            const data = await res.json().catch(() => ({}));
            // 422 de FastAPI: detail es una lista de errores de validación
            if (!res.ok) throw new Error(data.detail?.[0]?.msg || 'Error al enviar la solicitud al servidor');

            setJobId(data.job_id);
        } catch (err) {
            console.error(err);
            setErrorMsg(err.message);
            setStatus(null);
        }
    };

    return (
        <div className="min-h-screen bg-[#0d0e11] text-zinc-200 flex flex-col justify-center py-12 px-6 font-sans">
            <div className="max-w-4xl mx-auto w-full">

                {/* Cabecera */}
                <header className="mb-12 text-center">
                    <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight text-zinc-100">
                        ClipSync
                    </h1>
                    <p className="mt-3 text-base text-zinc-400 mx-auto leading-relaxed">
                        Genera recortes verticales en formato 9:16 desde enlaces de YouTube o Twitch.
                    </p>
                </header>

                {/* Grid principal */}
                <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">

                    {/* Formulario */}
                    <form
                        onSubmit={handleSubmit}
                        className="md:col-span-7 bg-[#14161b] border border-[#22252c] rounded-lg p-6 space-y-6"
                    >
                        <div className="space-y-4">
                            <div>
                                <label className="block text-xs font-medium text-zinc-300 mb-2">
                                    Enlace del vídeo
                                </label>
                                <input
                                    type="url"
                                    required
                                    placeholder="https://www.youtube.com/watch?v=..."
                                    value={videoUrl}
                                    onChange={(e) => setVideoUrl(e.target.value)}
                                    className="w-full bg-[#0b0c0e] border border-[#262a33] rounded-md px-3.5 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-400 transition-colors"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4 pt-2">
                                <TimeInput
                                    label="Tiempo inicio"
                                    value={startTime}
                                    onChange={setStartTime}
                                />
                                <TimeInput
                                    label="Tiempo fin"
                                    value={endTime}
                                    onChange={setEndTime}
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={status === 'QUEUED' || status === 'PROCESSING'}
                            className="w-full bg-zinc-200 hover:bg-white text-zinc-900 font-medium py-2.5 px-4 rounded-md transition-colors disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm"
                        >
                            {status === 'QUEUED' || status === 'PROCESSING' ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin text-zinc-800" />
                                    <span>Generando vídeo...</span>
                                </>
                            ) : (
                                <>
                                    <Play className="w-4 h-4 fill-zinc-900" />
                                    <span>Generar clip</span>
                                </>
                            )}
                        </button>
                    </form>

                    {/* Área de resultado / Vista previa */}
                    <div className="md:col-span-5 bg-[#14161b] border border-[#22252c] rounded-lg p-6 min-h-[380px] flex flex-col items-center justify-center relative">

                        {errorMsg && (
                            <div className="w-full p-4 bg-red-950/30 border border-red-900/50 rounded-md text-red-300 flex items-start gap-3">
                                <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-400 mt-0.5" />
                                <span className="text-xs leading-relaxed">{errorMsg}</span>
                            </div>
                        )}

                        {!status && !errorMsg && (
                            <div className="text-center text-zinc-500 space-y-2">
                                <Video className="w-8 h-8 mx-auto stroke-[1.25] text-zinc-600" />
                                <p className="text-xs text-zinc-400 max-w-[200px]">
                                    El resultado final aparecerá aquí una vez procesado.
                                </p>
                            </div>
                        )}

                        {(status === 'QUEUED' || status === 'PROCESSING') && (
                            <div className="text-center space-y-3">
                                <Loader2 className="w-6 h-6 text-zinc-400 animate-spin mx-auto" />
                                <div>
                                    <p className="text-xs font-medium text-zinc-200">
                                        {status === 'QUEUED' ? 'En cola de espera' : 'Procesando clip'}
                                    </p>
                                    <p className="text-[11px] text-zinc-500 mt-1 max-w-[220px]">
                                        Extrayendo fragmento y ajustando encuadre.
                                    </p>
                                </div>
                            </div>
                        )}

                        {status === 'COMPLETED' && downloadUrl && (
                            <div className="w-full flex flex-col items-center gap-4">
                                <div className="w-[180px] aspect-[9/16] bg-black rounded border border-[#22252c] overflow-hidden shadow-sm">
                                    <video src={downloadUrl} controls className="w-full h-full object-contain" />
                                </div>

                                <a
                                    href={downloadUrl}
                                    download
                                    className="w-full bg-[#1e2129] hover:bg-[#252933] text-zinc-200 border border-[#2d323e] font-medium py-2 px-3 rounded-md transition-colors flex items-center justify-center gap-2 text-xs"
                                >
                                    <Download className="w-3.5 h-3.5" /> Descargar archivo
                                </a>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
