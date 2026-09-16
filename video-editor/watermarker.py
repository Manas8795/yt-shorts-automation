import os
import subprocess
import argparse
import imageio_ffmpeg


def get_ffmpeg() -> str:
    """Returns the bundled standalone FFmpeg binary."""
    return imageio_ffmpeg.get_ffmpeg_exe()


def overlay_logo_with_audio(
    video_input_path: str,
    video_output_path: str,
    logo_path: str,
    logo_width: int = 110,
    target_center_x: int = 600,
    target_center_y: int = 1160
) -> str:
    """
    Overlays channel logo directly over the Gemini watermark on 720x1280 videos,
    while completely preserving the original audio stream (ASMR sounds/engine audio).
    """
    if not os.path.exists(video_input_path):
        raise FileNotFoundError(f"Input video not found: {video_input_path}")
    if not os.path.exists(logo_path):
        raise FileNotFoundError(f"Logo not found: {logo_path}")

    ffmpeg_exe = get_ffmpeg()

    # Calculate top-left placement so center of logo is at (target_center_x, target_center_y)
    # The logo has ~1:1 aspect ratio (w=110, h=107)
    x1 = int(target_center_x - logo_width / 2)
    y1 = int(target_center_y - (logo_width * 0.97) / 2)

    os.makedirs(os.path.dirname(os.path.abspath(video_output_path)), exist_ok=True)

    # Use FFmpeg filter_complex: scales logo to logo_width, overlays at (x1, y1),
    # and copies original AAC audio track losslessly with -c:a copy
    cmd = [
        ffmpeg_exe, '-y',
        '-i', video_input_path,
        '-i', logo_path,
        '-filter_complex', f'[1:v]scale={logo_width}:-1[logo];[0:v][logo]overlay={x1}:{y1}[outv]',
        '-map', '[outv]',
        '-map', '0:a?',
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'copy',
        video_output_path
    ]

    print(f"Branding video: {os.path.basename(video_input_path)}")
    print(f"Overlay coordinates: x={x1}, y={y1} (width={logo_width}px)")
    print(f"Audio preservation: Stream #0:1 AAC copy")

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg render failed:\n{result.stderr}")

    file_size_mb = round(os.path.getsize(video_output_path) / (1024 * 1024), 2)
    print(f"✓ Video successfully rendered WITH SOUND: {video_output_path} ({file_size_mb} MB)")
    return video_output_path


def batch_brand_videos(
    source_dir: str,
    output_dir: str,
    logo_path: str,
    logo_width: int = 110
):
    """
    Scans source_dir for all generated video.mp4 files, overlays the channel logo
    over the Gemini watermark, preserves all audio, and saves them into output_dir.
    """
    video_files = []
    for root, _, files in os.walk(source_dir):
        for f in files:
            if f.endswith(".mp4") and not f.startswith("sample_"):
                video_files.append(os.path.join(root, f))

    print(f"Found {len(video_files)} videos in '{source_dir}' to process with sound.")
    success = 0
    for idx, vpath in enumerate(video_files, 1):
        rel = os.path.relpath(vpath, source_dir)
        target_path = os.path.join(output_dir, rel)
        print(f"\n[{idx}/{len(video_files)}] Processing: {rel}")
        try:
            overlay_logo_with_audio(
                video_input_path=vpath,
                video_output_path=target_path,
                logo_path=logo_path,
                logo_width=logo_width
            )
            success += 1
        except Exception as e:
            print(f"Error processing {vpath}: {e}")

    print(f"\n{'='*60}")
    print(f"✓ Batch complete! {success}/{len(video_files)} videos branded with sound.")
    print(f"Saved into: {output_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Overlay channel logo with full audio preservation.")
    parser.add_argument("--input", "-i", type=str, default="sample_video.mp4", help="Input video path")
    parser.add_argument("--output", "-o", type=str, default="sample_video_with_sound.mp4", help="Output video path")
    parser.add_argument("--logo", "-l", type=str, default="channel_logo_transparent.png", help="Path to logo PNG")
    parser.add_argument("--width", "-w", type=int, default=110, help="Logo display width (default: 110px)")
    parser.add_argument("--batch", "-b", action="store_true", help="Batch process all videos from youtube-automation output")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_file = os.path.join(base_dir, args.logo) if not os.path.isabs(args.logo) else args.logo

    if args.batch:
        src_folder = os.path.join(os.path.dirname(base_dir), "youtube-automation", "output")
        out_folder = os.path.join(base_dir, "branded_output")
        batch_brand_videos(src_folder, out_folder, logo_file, logo_width=args.width)
    else:
        in_file = os.path.join(base_dir, args.input) if not os.path.isabs(args.input) else args.input
        out_file = os.path.join(base_dir, args.output) if not os.path.isabs(args.output) else args.output
        overlay_logo_with_audio(in_file, out_file, logo_file, logo_width=args.width)
