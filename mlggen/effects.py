# Updated effects module to avoid moviepy/vfx.resize dependency on OpenCV/Scipy/Pillow.
# If PIL/Scipy/OpenCV are not available, this implements a pure-numpy nearest-neighbor
# fallback resize used via clip.fl_image or when producing resized image overlays.
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

def _safe_resize_array_nn(arr, new_w, new_h):
    """
    Nearest-neighbor resize for a numpy array frame (H x W x C) to (new_h, new_w).
    Pure numpy implementation (no PIL/Scipy/OpenCV).
    """
    if arr is None:
        return arr
    # arr shape: (h, w, channels) or (h, w)
    h, w = arr.shape[:2]
    if h == new_h and w == new_w:
        return arr
    # compute source indices
    row_idx = (np.floor(np.linspace(0, h - 1, new_h)).astype(np.int32))
    col_idx = (np.floor(np.linspace(0, w - 1, new_w)).astype(np.int32))
    # use advanced indexing to sample the pixels
    resized = arr[row_idx[:, None], col_idx[None, :]]
    return resized

def _compute_target_size(clip_w, clip_h, width=None, height=None, factor=None):
    if factor is not None:
        return max(1, int(round(clip_w * factor))), max(1, int(round(clip_h * factor)))
    if width is not None and height is not None:
        return max(1, int(round(width))), max(1, int(round(height)))
    if width is not None:
        new_w = int(round(width))
        new_h = max(1, int(round(clip_h * (new_w / float(clip_w)))))
        return new_w, new_h
    if height is not None:
        new_h = int(round(height))
        new_w = max(1, int(round(clip_w * (new_h / float(clip_h)))))
        return new_w, new_h
    # default: no change
    return clip_w, clip_h

def safe_resize_clip(clip, width=None, height=None, factor=None):
    """
    Resize a clip robustly:
    - If Pillow (or other dependencies) are present moviepy's vfx.resize is used.
    - Else, use a numpy-based nearest-neighbor resize via clip.fl_image.
    Returns a new clip with the requested size.
    """
    new_w, new_h = _compute_target_size(clip.w, clip.h, width, height, factor)

    # If nothing to do, return original clip
    if new_w == clip.w and new_h == clip.h:
        return clip

    # If PIL is available, prefer the moviepy/vfx resize path which will use PIL for good quality
    if HAS_PIL:
        # Use vfx.resize with a width or height parameter so moviepy/pil handles it
        if factor is not None:
            return clip.fx(vfx.resize, factor)
        if width is not None:
            return clip.fx(vfx.resize, width=new_w)
        if height is not None:
            return clip.fx(vfx.resize, height=new_h)
        return clip.fx(vfx.resize, newsize=(new_w, new_h))

    # Fallback: no PIL/Scipy/OpenCV available. Use fl_image with _safe_resize_array_nn.
    def _resize_frame(frame):
        return _safe_resize_array_nn(frame, new_w, new_h)
    # fl_image will apply the function to each frame (frame is a numpy array)
    resized_clip = clip.fl_image(_resize_frame)
    # Keep same duration and fps, but update size metadata for moviepy
    resized_clip = resized_clip.set_duration(clip.duration)
    # moviepy uses clip.w/clip.h from the first frame; set size attributes for safety
    resized_clip.size = (new_w, new_h)
    return resized_clip

def safe_resize_image_array(arr, new_w, new_h):
    """
    Resize a numpy image array (H x W x C) to new size using the same NN fallback.
    """
    return _safe_resize_array_nn(arr, new_w, new_h)

def safe_load_and_resize_image(image_path, target_h):
    """
    Load an image from disk and produce a numpy array resized to target height (preserving aspect).
    Uses PIL if available (better quality), else uses moviepy.ImageClip to load then numpy resize.
    Returns a numpy array (H x W x 4) RGBA.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)

    if HAS_PIL:
        pil_img = PILImage.open(image_path).convert("RGBA")
        ow, oh = pil_img.size
        if oh == 0:
            raise ValueError("Invalid image height")
        scale = target_h / float(oh)
        new_w = max(1, int(round(ow * scale)))
        new_h = max(1, int(round(oh * scale)))
        # Use LANCZOS if available
        try:
            resample = PILImage.Resampling.LANCZOS
        except Exception:
            resample = getattr(PILImage, "LANCZOS", getattr(PILImage, "ANTIALIAS", PILImage.BICUBIC))
        pil_img = pil_img.resize((new_w, new_h), resample=resample)
        arr = np.array(pil_img)
        return arr
    else:
        # Use moviepy.ImageClip to load image into memory (moviepy may still use PIL internally,
        # but if PIL is not installed ImageClip will attempt to load via ffmpeg; get_frame will provide array)
        img_clip = ImageClip(image_path).set_duration(0.01)
        arr = img_clip.get_frame(0)  # H x W x C
        h, w = arr.shape[:2]
        if h == 0:
            raise ValueError("Invalid loaded image height")
        scale = target_h / float(h)
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        arr_resized = safe_resize_image_array(arr, new_w, new_h)
        # Ensure result has 3 or 4 channels (ImageClip may produce RGB)
        if arr_resized.ndim == 2:
            arr_resized = np.stack([arr_resized]*3, axis=-1)
        return arr_resized

def safe_text_clip(txt, fontsize=48, color='white', duration=2, size=(640, 360)):
    """
    Return an ImageClip with text.
    - If Pillow is available, use it to draw text on a transparent image.
    - Else try moviepy.TextClip (ImageMagick).
    - Else return a transparent placeholder clip of the requested size and duration.
    """
    if HAS_PIL:
        img = PILImage.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", fontsize)
        except Exception:
            font = ImageFont.load_default()
        w, h = draw.textsize(txt, font=font)
        pos = ((size[0] - w) // 2, (size[1] - h) // 2)
        outline_color = "black"
        for ox, oy in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
            draw.text((pos[0] + ox, pos[1] + oy), txt, font=font, fill=outline_color)
        draw.text(pos, txt, font=font, fill=color)
        return ImageClip(np.array(img)).set_duration(duration)
    else:
        try:
            txtclip = TextClip(txt, fontsize=fontsize, color=color, stroke_color='black', stroke_width=2)
            txtclip = txtclip.set_duration(duration)
            return txtclip
        except Exception:
            w, h = size
            arr = np.zeros((h, w, 4), dtype=np.uint8)
            return ImageClip(arr).set_duration(duration)

def flash(clip, flashes=6, color=(255, 255, 255)):
    w, h = clip.size
    flashes_clips = []
    for i in range(flashes):
        t = i * clip.duration / max(flashes, 1)
        img = ImageClip(make_solid_image(w, h, color)).set_start(t).set_duration(0.05)
        flashes_clips.append(img)
    return CompositeVideoClip([clip] + flashes_clips).set_duration(clip.duration)

def make_solid_image(w, h, color):
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    arr[..., 0] = color[0]
    arr[..., 1] = color[1]
    arr[..., 2] = color[2]
    return arr

def quick_cut(clips, target_duration=None):
    shots = []
    for clip in clips:
        dur = clip.duration
        max_len = min(2.0, dur)
        if max_len <= 0.1:
            continue
        length = random.uniform(0.2, max_len)
        start = random.uniform(0, max(0, dur - length))
        shot = clip.subclip(start, start + length)
        if random.random() < 0.6:
            factor = random.uniform(1.3, 2.5)
            # Use safe_resize_clip for speed changes that imply resizing via speedx (no change needed)
            shot = shot.fx(vfx.speedx, factor)
        if random.random() < 0.5:
            shot = shot.fx(vfx.colorx, random.uniform(1.2, 2.2))
            shot = zoom_effect(shot)
        shots.append(shot)
        if target_duration and sum(s.duration for s in shots) > target_duration:
            break
    return shots

def zoom_effect(clip, max_zoom=1.5):
    """
    Simple zoom implemented via resizing frames. Uses safe_resize_clip to avoid
    moviepy's dependency on PIL/Scipy/OpenCV.
    This implementation applies a small random resize factor for the zoom.
    """
    factor = random.uniform(1.08, max_zoom)
    # Use safe resize so it works even without PIL/Scipy/OpenCV
    return safe_resize_clip(clip, factor=factor)

def overlay_image(clip, image_path, pos=('center', 'center'), duration=None, opacity=0.95):
    """
    Overlay an image onto clip.
    - If PIL is available, use it to load and resize the overlay.
    - Else load with moviepy.ImageClip then resize using our numpy fallback.
    """
    if not image_path:
        return clip
    if not os.path.exists(image_path):
        return clip

    try:
        # Target height is a fraction of clip height
        target_h = int(clip.h * 0.35)
        if HAS_PIL:
            pil_img = PILImage.open(image_path).convert("RGBA")
            ow, oh = pil_img.size
            if oh == 0:
                return clip
            scale = target_h / float(oh)
            new_w = max(1, int(round(ow * scale)))
            new_h = max(1, int(round(oh * scale)))
            try:
                resample = PILImage.Resampling.LANCZOS
            except Exception:
                resample = getattr(PILImage, "LANCZOS", getattr(PILImage, "ANTIALIAS", PILImage.BICUBIC))
            pil_img = pil_img.resize((new_w, new_h), resample=resample)
            img_clip = ImageClip(np.array(pil_img)).set_duration(duration or clip.duration).set_opacity(opacity)
            img_clip = img_clip.set_pos(pos)
            return CompositeVideoClip([clip, img_clip.set_duration(clip.duration)])
        else:
            # Load via ImageClip then get array and resize with numpy fallback
            img_clip = ImageClip(image_path).set_duration(duration or clip.duration).set_opacity(opacity)
            arr = img_clip.get_frame(0)  # H x W x C
            h, w = arr.shape[:2]
            if h == 0:
                return clip
            scale = target_h / float(h)
            new_w = max(1, int(round(w * scale)))
            new_h = max(1, int(round(h * scale)))
            arr_resized = safe_resize_image_array(arr, new_w, new_h)
            img_clip2 = ImageClip(arr_resized).set_duration(duration or clip.duration).set_opacity(opacity)
            img_clip2 = img_clip2.set_pos(pos)
            return CompositeVideoClip([clip, img_clip2.set_duration(clip.duration)])
    except Exception:
        try:
            img = ImageClip(image_path).set_duration(duration or clip.duration).set_opacity(opacity)
            img = img.resize(height=int(clip.h * 0.35))
            img = img.set_pos(pos)
            return CompositeVideoClip([clip, img.set_duration(clip.duration)])
        except Exception:
            return clip

def add_text_overlay(clip, text, fontsize=48, duration=1.5):
    try:
        txtclip = TextClip(text, fontsize=fontsize, color='white', stroke_color='black', stroke_width=2)
        txtclip = txtclip.set_duration(duration).set_pos(("center", "bottom"))
    except Exception:
        txtclip = safe_text_clip(text, fontsize=fontsize, duration=duration, size=clip.size).set_pos(("center", "bottom"))
    return CompositeVideoClip([clip, txtclip.set_start(random.uniform(0, max(0, clip.duration - duration))).set_opacity(0.9)])

def add_airhorn(clip, airhorn_path, when=0.1, vol=1.0):
    if not os.path.exists(airhorn_path):
        return clip
    try:
        a = AudioFileClip(airhorn_path).volumex(vol)
        return clip, (a, when)
    except Exception:
        return clip

def make_mlg_clip_sequence(video_paths, assets, target_duration=12, intensity="medium"):
    loaded = []
    for p in video_paths:
        try:
            v = VideoFileClip(p)
            if max(v.size) > 1280:
                # Use safe_resize_clip to reduce resolution without requiring extra deps
                v = safe_resize_clip(v, width=1280)
            loaded.append(v)
        except Exception:
            continue
    if not loaded:
        raise RuntimeError("No valid video clips loaded")

    shots = quick_cut(loaded, target_duration=target_duration)
    if not shots:
        raise RuntimeError("No shots created for MLG sequence")

    processed = []
    airhorns = []
    for s in shots:
        if random.random() < 0.5:
            s = overlay_image(s, assets.get("doritos", ""), pos=("left", "top"), opacity=0.95)
        if random.random() < 0.25:
            s = overlay_image(s, assets.get("lensflare", ""), pos=("center", "center"), opacity=0.6)
        if random.random() < 0.6:
            s = add_text_overlay(s, random.choice(["MLG", "PWNED", "360 NOSCOPE", "REKT"]), fontsize=random.choice([42, 54, 68]))
        if random.random() < 0.4 and os.path.exists(assets.get("airhorn", "")):
            try:
                a = AudioFileClip(assets.get("airhorn"))
                airhorns.append((a, 0.0))
            except Exception:
                pass
        processed.append(s)

    final = concatenate_videoclips(processed, method="compose")
    if os.path.exists(assets.get("mtndew", "")):
        try:
            music = AudioFileClip(assets.get("mtndew")).volumex(0.2)
            music = music.subclip(0, min(final.duration, music.duration))
            final = final.set_audio(music)
        except Exception:
            pass
    return final