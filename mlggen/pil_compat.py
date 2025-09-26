# Compatibility helpers for Pillow resampling constants
from PIL import Image

# Pillow 9 and earlier provided Image.ANTIALIAS (alias for LANCZOS).
# Pillow 10 removed those aliases and uses Image.Resampling.LANCZOS.
try:
    # Pillow >= 10
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
    RESAMPLE_BILINEAR = Image.Resampling.BILINEAR
except AttributeError:
    # Older Pillow: fall back to the old names or reasonable defaults
    RESAMPLE_LANCZOS = getattr(Image, "LANCZOS", getattr(Image, "ANTIALIAS", Image.BICUBIC))
    RESAMPLE_BILINEAR = getattr(Image, "BILINEAR", Image.NEAREST)