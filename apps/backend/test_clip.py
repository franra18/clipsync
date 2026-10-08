import os
import subprocess
import cv2
import yt_dlp

def to_seconds(time_str: str) -> int:
    parts = list(map(int, time_str.split(':')))
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return 0

def download_clip_segment(video_url: str, start_time: str, end_time: str, raw_path: str):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': raw_path,
        'download_ranges': yt_dlp.utils.download_range_func(None, [(to_seconds(start_time), to_seconds(end_time))]),
        'force_keyframes_at_cuts': True,
        # Simular clientes móviles de YouTube para evitar el bloqueo anti-bot
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        },
        'quiet': False
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

def detect_face_bbox(video_path: str):
    """
    Detecta el rostro usando la red neuronal SSD de OpenCV (mucho más precisa).
    Escanea varios segundos del vídeo buscando la detección con mayor confianza.
    """
    proto_path = "/app/deploy.prototxt"
    model_path = "/app/res10_300x300_ssd_iter_140000.caffemodel"
    
    net = cv2.dnn.readNetFromCaffe(proto_path, model_path)
    cap = cv2.VideoCapture(video_path)
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    best_box = None
    max_confidence = 0.5  # Umbral mínimo de certeza
    
    # Muestreamos hasta 150 fotogramas saltando de 3 en 3 para no ralentizar
    step = 3
    frames_checked = 0

    while cap.isOpened() and frames_checked < 150:
        ret, frame = cap.read()
        if not ret:
            break

        frames_checked += 1
        if frames_checked % step != 0:
            continue

        # Preparar imagen para la red neuronal (300x300)
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))
        net.setInput(blob)
        detections = net.forward()

        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            
            if confidence > max_confidence:
                box = detections[0, 0, i, 3:7] * [width, height, width, height]
                x1, y1, x2, y2 = box.astype("int")
                
                w = x2 - x1
                h = y2 - y1
                
                # Descartamos detecciones diminutas o artefactos
                if w < 50 or h < 50:
                    continue

                max_confidence = confidence

                # Añadimos margen alrededor para capturar hombros y encuadre de cámara
                pad_w = int(w * 1.0)
                pad_h = int(h * 1.0)
                
                crop_x = max(0, x1 - pad_w // 2)
                crop_y = max(0, y1 - pad_h // 2)
                crop_w = min(width - crop_x, w + pad_w)
                crop_h = min(height - crop_y, h + pad_h)
                
                best_box = (crop_x, crop_y, crop_w, crop_h)

    cap.release()

    if best_box:
        print(f"Rostro localizado con éxito (confianza: {max_confidence:.2f}): {best_box}")
        return best_box

    print("No se encontró rostro con suficiente confianza; usando fallback.")
    return (int(width * 0.7), int(height * 0.05), int(width * 0.28), int(height * 0.35))

def render_vertical_stream_clip(raw_path: str, output_path: str):
    """
    Compone el layout:
    - Arriba (1080x720): Webcam recortada centrada.
    - Abajo (1080x1200): Pantalla de gameplay centrada.
    """
    crop_x, crop_y, crop_w, crop_h = detect_face_bbox(raw_path)
    print(f"Coordenadas de webcam detectadas: x={crop_x}, y={crop_y}, w={crop_w}, h={crop_h}")

    # Filtro FFmpeg: divide el video original en dos ramas ([cam] y [game]) y las une verticalmente ([outv])
    filter_complex = (
        f"[0:v]crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale=1080:720:force_original_aspect_ratio=increase,crop=1080:720[cam];"
        f"[0:v]scale=1080:1200:force_original_aspect_ratio=increase,crop=1080:1200[game];"
        f"[cam][game]vstack=inputs=2[outv]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", raw_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-c:a", "aac",
        output_path
    ]
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    # Puedes poner aquí una URL de Twitch o YouTube que tenga un streamer con cámara visible
    test_url = "https://www.youtube.com/watch?v=zQyrhjEAqLs"
    raw_video = "/output/raw_stream.mp4"
    final_vertical = "/output/stream_vertical.mp4"

    print("1. Descargando fragmento original...")
    download_clip_segment(test_url, "00:05", "00:15", raw_video)

    print("2. Analizando fotogramas y componiendo layout 9:16...")
    render_vertical_stream_clip(raw_video, final_vertical)

    print(f"Proceso finalizado con éxito: {final_vertical}")
