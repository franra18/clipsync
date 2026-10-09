import os
import subprocess
import shutil
from pathlib import Path
from typing import Tuple, Optional
import cv2
import yt_dlp
from faster_whisper import WhisperModel
from src.core.storage import s3_client
from src.core.config import MINIO_BUCKET, MINIO_ENDPOINT

OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
CAM_HEIGHT = 720
GAME_HEIGHT = OUTPUT_HEIGHT - CAM_HEIGHT

MODEL_PROTO_PATH = Path("/app/deploy.prototxt")
MODEL_CAFFE_PATH = Path("/app/res10_300x300_ssd_iter_140000.caffemodel")

FACE_NET = cv2.dnn.readNetFromCaffe(str(MODEL_PROTO_PATH), str(MODEL_CAFFE_PATH))
WHISPER_MODEL = WhisperModel("base", device="cpu", compute_type="int8")

def to_seconds(time_str: str) -> int:
    parts = list(map(int, time_str.split(':')))
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return 0

def format_time_ass(seconds: float) -> str:
    centisecs = int((seconds - int(seconds)) * 100)
    secs = int(seconds) % 60
    mins = (int(seconds) // 60) % 60
    hours = int(seconds) // 3600
    return f"{hours}:{mins:02}:{secs:02}.{centisecs:02}"

def download_clip_segment(video_url: str, start_time: str, end_time: str, raw_path: Path) -> None:
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': str(raw_path),
        'download_ranges': yt_dlp.utils.download_range_func(
            None, [(to_seconds(start_time), to_seconds(end_time))]
        ),
        'force_keyframes_at_cuts': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        'quiet': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

def detect_face_bbox(video_path: Path, max_frames: int = 150) -> Tuple[int, int, int, int]:
    cap = cv2.VideoCapture(str(video_path))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    best_box: Optional[Tuple[int, int, int, int]] = None
    max_confidence = 0.5
    frames_checked = 0

    try:
        while cap.isOpened() and frames_checked < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            frames_checked += 1
            if frames_checked % 3 != 0:
                continue

            blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))
            FACE_NET.setInput(blob)
            detections = FACE_NET.forward()

            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                if confidence > max_confidence:
                    box = detections[0, 0, i, 3:7] * [width, height, width, height]
                    x1, y1, x2, y2 = box.astype("int")
                    w, h = x2 - x1, y2 - y1
                    if w < 50 or h < 50:
                        continue
                    max_confidence = confidence
                    pad_w, pad_h = int(w * 1.0), int(h * 1.0)
                    crop_x = max(0, x1 - pad_w // 2)
                    crop_y = max(0, y1 - pad_h // 2)
                    crop_w = min(width - crop_x, w + pad_w)
                    crop_h = min(height - crop_y, h + pad_h)
                    best_box = (crop_x, crop_y, crop_w, crop_h)
    finally:
        cap.release()

    return best_box or (int(width * 0.7), int(height * 0.05), int(width * 0.28), int(height * 0.35))

def generate_subtitles_ass(audio_video_path: Path, ass_output_path: Path, words_per_chunk: int = 2) -> None:
    segments, _ = WHISPER_MODEL.transcribe(str(audio_video_path), beam_size=5, word_timestamps=True)
    words_list = [w for segment in segments if segment.words for w in segment.words]
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
    crop_x, crop_y, crop_w, crop_h = detect_face_bbox(raw_path)
    filter_complex = (
        f"[0:v]crop={crop_w}:{crop_h}:{crop_x}:{crop_y},"
        f"scale={OUTPUT_WIDTH}:{CAM_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={OUTPUT_WIDTH}:{CAM_HEIGHT}[cam];"
        f"[0:v]scale={OUTPUT_WIDTH}:{GAME_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={OUTPUT_WIDTH}:{GAME_HEIGHT}[game];"
        f"[cam][game]vstack=inputs=2,"
        f"ass='{ass_path}'[outv]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", str(raw_path),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-c:a", "aac",
        str(output_path)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def process_video_pipeline(job_id: str, video_url: str, start_time: str, end_time: str) -> str:
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
        s3_client.upload_file(str(final_output), MINIO_BUCKET, object_name)
        return object_name
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
