import yt_dlp

def to_seconds(time_str: str) -> int:
    parts = list(map(int, time_str.split(':')))
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return 0

def download_clip_segment(video_url: str, start_time: str, end_time: str, output_path: str):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'download_ranges': yt_dlp.utils.download_range_func(None, [(to_seconds(start_time), to_seconds(end_time))]),
        'force_keyframes_at_cuts': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

if __name__ == "__main__":
    test_url = "https://www.youtube.com/watch?v=zQyrhjEAqLs"
    output_file = "/output/clip_prueba.mp4"
    
    print("Iniciando descarga dentro del contenedor Docker...")
    download_clip_segment(test_url, "00:05", "00:15", output_file)
    print(f"Clip guardado correctamente en: {output_file}")
