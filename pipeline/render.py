"""Step 5: assemble the final video with ffmpeg, sized to the chosen format.
Shorts get burned captions; long-form does not. Requires ffmpeg on PATH."""
import subprocess
import shutil
import config


def _ffmpeg(args):
    exe = shutil.which("ffmpeg")
    if not exe:
        raise SystemExit("ffmpeg not found on PATH. Install it (see README).")
    subprocess.run([exe, "-y", "-hide_banner", "-loglevel", "error", *args], check=True)


def _audio_duration(path) -> float:
    probe = shutil.which("ffprobe")
    out = subprocess.check_output([
        probe, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ])
    return float(out.strip())


def render(broll, audio_path, ass_path, out_path, work, fmt):
    w, h, fps = fmt["width"], fmt["height"], config.FPS
    dur = _audio_duration(audio_path)

    norm_clips = []
    for i, clip in enumerate(broll):
        norm = work / f"norm_{i:02d}.mp4"
        _ffmpeg([
            "-i", str(clip),
            "-vf",
            f"scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},fps={fps}",
            "-an", "-t", "8", "-c:v", "libx264", "-preset", "veryfast",
            "-pix_fmt", "yuv420p", str(norm),
        ])
        norm_clips.append(norm)

    listfile = work / "concat.txt"
    listfile.write_text("".join(f"file '{c.as_posix()}'\n" for c in norm_clips),
                        encoding="utf-8")
    silent = work / "silent.mp4"
    _ffmpeg(["-f", "concat", "-safe", "0", "-i", str(listfile), "-c", "copy", str(silent)])

    vf = None
    if fmt["burn_captions"] and ass_path is not None:
        ass = ass_path.as_posix().replace(":", "\\:")
        vf = f"subtitles='{ass}'"

    args = ["-stream_loop", "-1", "-i", str(silent), "-i", str(audio_path),
            "-t", f"{dur:.2f}"]
    if vf:
        args += ["-vf", vf]
    args += ["-map", "0:v:0", "-map", "1:a:0",
             "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-shortest",
             "-movflags", "+faststart", str(out_path)]
    _ffmpeg(args)
    return out_path
