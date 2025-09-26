# Updated effects module: works with or without Pillow installed.
import random
import os
import numpy as np
from moviepy.editor import (
    CompositeVideoClip, ImageClip, AudioFileClip, concatenate_videoclips,
    VideoFileClip, afx, vfx, TextClip
)

# Try to import Pillow (PIL). If it's not installed, fall back to moviepy-only behavior.
try:
    from PIL import Image as PILImage, ImageDraw, ImageFont
    HAS_PIL = True
except Exception:
    PILImage = None
    ImageDraw = None
    ImageFont = None
    HAS_PIL = False

def safe_text_clip(txt, fontsize=48, color='white', duration=2, size=(640, 360)):
    """
    Return an ImageClip with text.
    - If Pillow is available, use it to draw text on a transparent image.
    - Else try moviepy.TextClip (requires ImageMagick).
    - Else return a transparent placeholder clip of the requested size and duration.
    """
    if HAS_PIL:
        # Pillow-based text rendering (no ImageMagick required)
        img = PILImage.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", fontsize)
        except Exception:
            font = ImageFont.load_default()

        # center text
        w, h = draw.textsize(txt, font=font)
        pos = ((size[0] - w) // 2, (size[1] - h) // 2)
        outline_color = "black"
        for ox, oy in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
            draw.text((pos[0] + ox, pos[1] + oy), txt, font=font, fill=outline_color)
        draw.text(pos, txt, font=font, fill=color)
        return ImageClip(np.array(img)).set_duration(duration)
    else:
        # Try TextClip (ImageMagick) first
        try:
            txtclip = TextClip(txt, fontsize=fontsize, color=color, stroke_color='black', stroke_width=2)
            txtclip = txtclip.set_duration(duration)
            return txtclip
        except Exception:
            # Fallback: transparent placeholder clip (no text)
            w, h = size
            arr = np.zeros((h, w, 4), dtype=np.uint8)  # fully transparent RGBA
            return ImageClip(arr).set_duration(duration)

def flash(clip, flashes=6, color=(255, 255, 255)):
    """
    Add quick flashes to the clip by overlaying colored frames at intervals.
    """
    w, h = clip.size
    flashes_clips = []
    for i in range(flashes):
        t = i * clip.duration / max(flashes, 1)
        img = ImageClip(make_solid_image(w, h, color)).set_start(t).set_duration(0.05)
        flashes_clips.append(img)
    return CompositeVideoClip([clip] + flashes_clips).set_duration(clip.duration)

def make_solid_image(w, h, color):
    # Use numpy to create a solid-color frame (avoid PIL dependency here)
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    arr[..., 0] = color[0]
    arr[..., 1] = color[1]
    arr[..., 2] = color[2]
    return arr

def quick_cut(clips, target_duration=None):
    """
    Hard cuts: trims clips to short bursts and concatenates.
    """
    shots = []
    for clip in clips:
        dur = clip.duration
        # pick a short random snippet
        max_len = min(2.0, dur)
        if max_len <= 0.1:
            continue
        length = random.uniform(0.2, max_len)
        start = random.uniform(0, max(0, dur - length))
        shot = clip.subclip(start, start + length)
        # randomly speed up
        if random.random() < 0.6:
            factor = random.uniform(1.3, 2.5)
            shot = shot.fx(vfx.speedx, factor)
        # randomly add zoom and color
        if random.random() < 0.5:
            shot = shot.fx(vfx.colorx, random.uniform(1.2, 2.2))
            shot = zoom_effect(shot)
        shots.append(shot)
        if target_duration and sum(s.duration for s in shots) > target_duration:
            break
    return shots

def zoom_effect(clip, max_zoom=1.5):
    # fallback: use resize with small factor change
    factor = random.uniform(1.08, max_zoom)
    return clip.fx(vfx.resize, factor)

def overlay_image(clip, image_path, pos=('center', 'center'), duration=None, opacity=0.95):
    """
    Overlay an image onto clip.

    Behavior:
    - If Pillow is available, use PIL to open and resize the overlay with good resampling.
    - If Pillow is not available, fall back to moviepy.ImageClip(...) and .resize(...) which uses ffmpeg.
    """
    if not image_path:
        return clip
    if not os.path.exists(image_path):
        return clip

    try:
        if HAS_PIL:
            # Use Pillow to load and resize the overlay (keeps control without depending on ffmpeg resizing)
            pil_img = PILImage.open(image_path).convert("RGBA")
            target_h = int(clip.h * 0.35)
            ow, oh = pil_img.size
            if oh == 0:
                return clip
            scale = target_h / float(oh)
            new_w = max(1, int(ow * scale))
            new_h = max(1, int(oh * scale))
            # Use Pillow's LANCZOS (or available equivalent) for good quality
            try:
                resample = PILImage.Resampling.LANCZOS
            except Exception:
                resample = getattr(PILImage, "LANCZOS", getattr(PILImage, "ANTIALIAS", PILImage.BICUBIC))
            pil_img = pil_img.resize((new_w, new_h), resample=resample)
            img_clip = ImageClip(np.array(pil_img)).set_duration(duration or clip.duration).set_opacity(opacity)
            img_clip = img_clip.set_pos(pos)
            return CompositeVideoClip([clip, img_clip.set_duration(clip.duration)])
        else:
            # No Pillow: load with moviepy and let moviepy/ffmpeg handle resizing
            img = ImageClip(image_path).set_duration(duration or clip.duration).set_opacity(opacity)
            # moviepy resize supports keyword height
            img = img.resize(height=int(clip.h * 0.35))
            img = img.set_pos(pos)
            return CompositeVideoClip([clip, img.set_duration(clip.duration)])
    except Exception:
        # Last-resort fallback: try moviepy.ImageClip path
        try:
            img = ImageClip(image_path).set_duration(duration or clip.duration).set_opacity(opacity)
            img = img.resize(height=int(clip.h * 0.35))
            img = img.set_pos(pos)
            return CompositeVideoClip([clip, img.set_duration(clip.duration)])
        except Exception:
            return clip

def add_text_overlay(clip, text, fontsize=48, duration=1.5):
    # Try TextClip (ImageMagick) first
    try:
        txtclip = TextClip(text, fontsize=fontsize, color='white', stroke_color='black', stroke_width=2)
        txtclip = txtclip.set_duration(duration).set_pos(("center", "bottom"))
    except Exception:
        # fall back to safe_text_clip which handles both PIL and non-PIL fallback
        txtclip = safe_text_clip(text, fontsize=fontsize, duration=duration, size=clip.size).set_pos(("center", "bottom"))
    return CompositeVideoClip([clip, txtclip.set_start(random.uniform(0, max(0, clip.duration - duration))).set_opacity(0.9)])

def add_airhorn(clip, airhorn_path, when=0.1, vol=1.0):
    if not os.path.exists(airhorn_path):
        return clip
    try:
        a = AudioFileClip(airhorn_path).volumex(vol)
        # We'll place the airhorn in the final composition rather than modify each clip here.
        return clip, (a, when)
    except Exception:
        return clip

def make_mlg_clip_sequence(video_paths, assets, target_duration=12, intensity="medium"):
    """
    video_paths: list of paths to video files
    assets: dict of asset paths (airhorn, doritos, etc.)
    returns CompositeVideoClip ready to write.
    """
    loaded = []
    for p in video_paths:
        try:
            v = VideoFileClip(p)
            # Optionally resize to a manageable size
            if max(v.size) > 1280:
                v = v.resize(width=1280)
            loaded.append(v)
        except Exception:
            continue
    if not loaded:
        raise RuntimeError("No valid video clips loaded")

    # Create quick-cut shots
    shots = quick_cut(loaded, target_duration=target_duration)
    if not shots:
        raise RuntimeError("No shots created for MLG sequence")

    # Add overlays and random text
    processed = []
    airhorns = []
    for s in shots:
        # overlay doritos sometimes
        if random.random() < 0.5:
            s = overlay_image(s, assets.get("doritos", ""), pos=("left", "top"), opacity=0.95)
        # overlay lensflare rarely
        if random.random() < 0.25:
            s = overlay_image(s, assets.get("lensflare", ""), pos=("center", "center"), opacity=0.6)
        # add text
        if random.random() < 0.6:
            s = add_text_overlay(s, random.choice(["MLG", "PWNED", "360 NOSCOPE", "REKT"]), fontsize=random.choice([42, 54, 68]))
        # collect airhorns occasionally
        if random.random() < 0.4 and os.path.exists(assets.get("airhorn", "")):
            try:
                a = AudioFileClip(assets.get("airhorn"))
                airhorns.append((a, 0.0))
            except Exception:
                pass
        processed.append(s)

    final = concatenate_videoclips(processed, method="compose")
    # Optionally set background music
    if os.path.exists(assets.get("mtndew", "")):
        try:
            music = AudioFileClip(assets.get("mtndew")).volumex(0.2)
            music = music.subclip(0, min(final.duration, music.duration))
            final = final.set_audio(music)
        except Exception:
            pass
    return final