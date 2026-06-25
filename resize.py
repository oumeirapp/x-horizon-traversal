import os
from PIL import Image
from pathlib import Path
from utils import L2, L3,L3_err,L3_ok
import ffmpeg

# ═════════════════════════════════════════════════════════════
#  Video helpers
# ═════════════════════════════════════════════════════════════
 
HD_LONG  = 1280
HD_SHORT = 720

 
def probe_video(path: str) -> dict:
    """Extract width, height and duration from a video file via ffprobe."""
    try:
        info = ffmpeg.probe(path)
    except ffmpeg.Error as exc:
        raise RuntimeError(
            f"Could not probe '{path}':\n{exc.stderr.decode().strip()}\n\n"
            "Make sure FFmpeg is installed and on your PATH: "
            "https://ffmpeg.org/download.html"
        )
 
    video_streams = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    if not video_streams:
        raise RuntimeError(f"No video stream found in '{path}'.")
 
    stream = video_streams[0]
    try:
        width    = int(stream["width"])
        height   = int(stream["height"])
        duration = float(
            stream.get("duration") or info.get("format", {}).get("duration", 0)
        )
    except (KeyError, ValueError) as exc:
        raise RuntimeError(f"Could not parse video dimensions: {exc}")
 
    return {"width": width, "height": height, "duration": duration}
 
 
def compute_target_dimensions(width: int, height: int) -> tuple | None:
    """
    Return (target_w, target_h) scaled down to HD_LONG×HD_SHORT,
    or None if the video is already within HD bounds (no upscaling).
    """
    is_landscape = width >= height
    long_side, short_side = (width, height) if is_landscape else (height, width)
 
    if long_side <= HD_LONG and short_side <= HD_SHORT:
        return None
 
    scale_factor = HD_LONG / long_side
    new_short    = short_side * scale_factor
 
    new_long  = HD_LONG
    new_short = new_short if new_short >= HD_SHORT else HD_SHORT
 
    # Enforce even pixel counts (required by H.264)
    new_long  = (int(new_long)  // 2) * 2
    new_short = (int(new_short) // 2) * 2
 
    return (new_long, new_short) if is_landscape else (new_short, new_long)
 
 
def _ffmpeg_resize_video(input_path: str, output_path: str, target_dims: tuple) -> None:
    """Run ffmpeg scale filter, copy audio, write to output_path."""
    tw, th = target_dims
    try:
        input_node = ffmpeg.input(input_path)
        video = input_node.video.filter("scale", tw, th, flags="lanczos")
        audio = input_node.audio
        (
            ffmpeg
            .output(video, audio, output_path, vcodec="libx264", acodec="copy",
                    **{"movflags": "+faststart"})
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as exc:
        raise RuntimeError(
            f"FFmpeg error during resize:\n{exc.stderr.decode().strip()}"
        )
 
 
def human_size(path: str) -> str:
    """Return a human-readable file size string (e.g. '24.3 MB')."""
    size = os.path.getsize(path)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
 
 
# ═════════════════════════════════════════════════════════════
#  Video resizing
# ═════════════════════════════════════════════════════════════
 
def resize_videos(folder: Path):
    L2("RESIZE VIDEOS")
    video_extensions = {".mp4", ".avi"}
    count = 0
 
    for video_file in folder.iterdir():
        if not (video_file.is_file() and video_file.suffix.lower() in video_extensions):
            continue
        try:
            meta = probe_video(str(video_file))
            w, h = meta["width"], meta["height"]
            target = compute_target_dimensions(w, h)
 
            if target is None:
                L3(f"OK (size): {video_file.name}  ({w}×{h} — within HD, skipped)")
                continue
 
            # Resize into a temp file then replace the original in-place
            tmp_path = video_file.with_stem(video_file.stem + "_tmp")
            _ffmpeg_resize_video(str(video_file), str(tmp_path), target)
 
            size_before = human_size(str(video_file))
            video_file.unlink()
            tmp_path.rename(video_file)
            size_after = human_size(str(video_file))
 
            tw, th = target
            L3_ok(
                f"Resized: {video_file.name}  "
                f"({w}×{h}  →  {tw}×{th})  "
                f"{size_before}  →  {size_after}"
            )
            count += 1
 
        except Exception as e:
            L3_err(f"Failed to resize {video_file.name}: {e}")
 
    L3(f"Videos resized: {count}")
    print()


# ═════════════════════════════════════════════════════════════
#  Image resizing
# ═════════════════════════════════════════════════════════════
 
def resize_images(folder: Path, quality: int = 70):
    L2("RESIZE IMAGES")
    MAX_SIZE = (1920, 1080)
    image_extensions = {".jpg", ".jpeg", ".png"}
    count = 0
 
    for image_file in folder.iterdir():
        if not (image_file.is_file() and image_file.suffix.lower() in image_extensions):
            continue
        try:
            with Image.open(image_file) as img:
                orig_w, orig_h = img.width, img.height
                if orig_w > 1920 or orig_h > 1080:
                    img.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
                    img.save(image_file, optimize=True, quality=quality)
                    L3_ok(f"Resized:   {image_file.name}  ({orig_w}×{orig_h}  →  {img.width}×{img.height})")
                else:
                    L3(f"OK (size): {image_file.name}  ({orig_w}×{orig_h})")
            count += 1
        except Exception as e:
            L3_err(f"Failed to resize {image_file.name}: {e}")
 
    L3(f"Images processed: {count}")
    print()