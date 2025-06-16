import subprocess

def merge_video_audio(video_path, audio_path, output_path):
    print("Merging video and audio with FFmpeg...")
    command = [
        "ffmpeg",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-strict", "experimental",
        "-y",  # Overwrite output file if it exists
        output_path
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        print("Merge completed! Saved as", output_path)
    else:
        print("Error during merge:", result.stderr)