import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

import cv2
import yt_dlp
from faster_whisper import WhisperModel

from src.core.config import MINIO_BUCKET
from src.core.storage import s3_client
from src.core.timecode import to_seconds

# ==========================================
# CONSTANTES Y CONFIGURACIÓN
# ==========================================
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
CAM_HEIGHT = 720
GAME_HEIGHT = OUTPUT_HEIGHT - CAM_HEIGHT  # 1200px

MODEL_DIR = Path(os.environ.get("MODEL_DIR", "/app"))
MODEL_PROTO_PATH = Path(
    os.environ.get("MODEL_PROTO_PATH", MODEL_DIR / "deploy.prototxt")
)
MODEL_CAFFE_PATH = Path(
    os.environ.get(
        "MODEL_CAFFE_PATH", MODEL_DIR / "res10_300x300_ssd_iter_140000.caffemodel"
    )
)

# Carga única de Whisper en memoria para reutilizar el modelo
WHISPER_MODEL = WhisperModel("base", device="cpu", compute_type="int8")
_FACE_NET = None


def get_face_net():
    """Carga perezosa (lazy load) del detector neuronal Caffe."""
    global _FACE_NET
    if _FACE_NET is None:
        _FACE_NET = cv2.dnn.readNetFromCaffe(
            str(MODEL_PROTO_PATH), str(MODEL_CAFFE_PATH)
        )
    return _FACE_NET


def format_time_ass(seconds: float) -> str:
    """Formatea tiempo flotante al estándar ASS (H:MM:SS.CS)."""
    centisecs = int((seconds - int(seconds)) * 100)
    secs = int(seconds) % 60
    mins = (int(seconds) // 60) % 60
    hours = int(seconds) // 3600
    return f"{hours}:{mins:02}:{secs:02}.{centisecs:02}"


def download_clip_segment(
    video_url: str, start_time: str, end_time: str, raw_path: Path
) -> None:
    """Descarga el tramo pedido hasta 1440p, con audio, unido en MP4."""
    ydl_opts = {
        # 1440p da más píxeles reales a la cámara, que luego se amplía x3-x4
        "format": "bv*[height<=1440]+ba/b",
        "merge_output_format": "mp4",
        # Con force_keyframes_at_cuts yt-dlp recodifica con los defaults de FFmpeg (CRF 23);
        # casi sin pérdida aquí, porque el render final vuelve a codificar
        "external_downloader_args": {
            "ffmpeg_o": ["-c:v", "libx264", "-crf", "10", "-preset", "veryfast", "-c:a", "copy"]
        },
        "outtmpl": str(raw_path),
        "download_ranges": yt_dlp.utils.download_range_func(
            None, [(to_seconds(start_time), to_seconds(end_time))]
        ),
        "force_keyframes_at_cuts": True,
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])


def detect_face_bbox(video_path: Path, max_frames: int = 150) -> Tuple[int, int, int, int]:
    """Detecta el encuadre óptimo de la cámara usando el detector neuronal."""
    cap = cv2.VideoCapture(str(video_path))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    best_box: Optional[Tuple[int, int, int, int]] = None
    max_confidence = 0.25
    frames_checked = 0

    try:
        net = get_face_net()

        while cap.isOpened() and frames_checked < max_frames:
            frames_checked += 1
            # grab() avanza sin decodificar el frame: solo analizamos 1 de cada 5
            if frames_checked % 5 != 0:
                if not cap.grab():
                    break
                continue

            ret, frame = cap.read()
            if not ret:
                break

            blob = cv2.dnn.blobFromImage(
                frame,
                1.0,
                (300, 300),
                (104.0, 177.0, 123.0),
                swapRB=False,
                crop=False,
            )
            net.setInput(blob)
            detections = net.forward()

            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                if confidence > max_confidence:
                    box = detections[0, 0, i, 3:7] * [width, height, width, height]
                    x1, y1, x2, y2 = box.astype("int")
                    w, h = x2 - x1, y2 - y1

                    if w < 35 or h < 35 or w > (width * 0.6):
                        continue

                    max_confidence = confidence

                    # Zoom cercano: 1.8x el tamaño del rostro (cabeza y hombros)
                    center_x, center_y = x1 + w // 2, y1 + h // 2
                    crop_size = max(int(w * 1.8), int(h * 1.8))

                    crop_x = max(0, center_x - crop_size // 2)
                    crop_y = max(0, center_y - crop_size // 2)
                    crop_w = min(width - crop_x, crop_size)
                    crop_h = min(height - crop_y, crop_size)

                    best_box = (crop_x, crop_y, crop_w, crop_h)

    except Exception as e:
        print(f"Aviso en detección facial: {e}. Usando encuadre fallback.")
    finally:
        cap.release()

    if best_box:
        print(f"[INFO] Cara detectada con confianza {max_confidence:.2f}: {best_box}")
        return best_box

    print("[WARN] No se detectó cara. Aplicando recuadrazo predeterminado cercano.")
    return (0, 0, int(width * 0.25), int(height * 0.35))


def generate_subtitles_ass(
    audio_video_path: Path, ass_output_path: Path, words_per_chunk: int = 2
) -> None:
    """Genera subtítulos .ass animados en bloques cortos de palabras."""
    segments, _ = WHISPER_MODEL.transcribe(
        str(audio_video_path), beam_size=1, vad_filter=True, word_timestamps=True
    )

    words_list = [
        w for segment in segments if segment.words for w in segment.words
    ]
    if not words_list:
        return

    chunks = []
    for i in range(0, len(words_list), words_per_chunk):
        chunk = words_list[i:i + words_per_chunk]
        text = " ".join([w.word.strip() for w in chunk]).lower()
        chunks.append((chunk[0].start, chunk[-1].end, text))

    ass_header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {OUTPUT_WIDTH}\n"
        f"PlayResY: {OUTPUT_HEIGHT}\n"
        "WrapStyle: 2\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,90,&H0000FFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,92,100,0,0,1,4,0,8,40,40,625,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    anim_tag = r"{\fscx69\fscy75\t(0,80,\fscx92\fscy100)}"

    with open(ass_output_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        for start, end, text in chunks:
            f.write(f"Dialogue: 0,{format_time_ass(start)},{format_time_ass(end)},Default,,0,0,0,,{anim_tag}{text}\n")


def render_vertical_clip(raw_path: Path, ass_path: Path, output_path: Path) -> None:
    """Ensambla el formato 9:16 en FFmpeg e incrusta el subtítulo animado."""
    crop_x, crop_y, crop_w, crop_h = detect_face_bbox(raw_path)

    filter_complex = (
        f"[0:v]crop={crop_w}:{crop_h}:{crop_x}:{crop_y},"
        f"scale={OUTPUT_WIDTH}:{CAM_HEIGHT}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={OUTPUT_WIDTH}:{CAM_HEIGHT},"
        # Enfoque suave para compensar el reescalado (solo luminancia)
        f"unsharp=5:5:0.6:5:5:0.0[cam];"
        f"[0:v]scale={OUTPUT_WIDTH}:{GAME_HEIGHT}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={OUTPUT_WIDTH}:{GAME_HEIGHT}[game];"
        f"[cam][game]vstack=inputs=2,"
        f"ass='{ass_path}'[outv]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(raw_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "[outv]",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "21",
        "-profile:v",
        "high",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def process_video_pipeline(
    job_id: str, video_url: str, start_time: str, end_time: str
) -> str:
    """Orquestador completo del procesamiento de vídeo y subida a MinIO."""
    temp_dir = Path(f"/tmp/clip_{job_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)

    raw_video = temp_dir / "raw.mp4"
    ass_file = temp_dir / "subtitles.ass"
    final_output = temp_dir / f"{job_id}.mp4"

    try:
        download_clip_segment(video_url, start_time, end_time, raw_video)
        generate_subtitles_ass(raw_video, ass_file)
        render_vertical_clip(raw_video, ass_file, final_output)

        object_name = f"clips/{job_id}.mp4"
        s3_client.upload_file(
            Filename=str(final_output), Bucket=MINIO_BUCKET, Key=object_name,
            ExtraArgs={"ContentType": "video/mp4"},
        )
        return object_name
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
