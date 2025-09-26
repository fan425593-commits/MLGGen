# MLGGen

Small MLG-style video generator (Windows 8.1 friendly) using Python + moviepy 1.0.1.

Features
- Simple Tkinter GUI to select clips and render an MLG remix
- Built-in MLG effects: quick cuts, speed-ups, color punch, zooms, flashes, overlays (Doritos/Dew), airhorn audio overlay
- Assets folder for typical MLG assets (airhorn, doritos.png, mtndew.mp3)
- CLI runner script

Requirements & Notes
- Designed for Python 3.6+ on Windows (8.1 compatible)
- moviepy 1.0.1 may require ImageMagick for TextClip; if you don't have ImageMagick, the code falls back to Pillow-based text overlay where possible.
- Install requirements:
  pip install -r requirements.txt

Usage
- Put your assets into the `assets/` folder (see assets/README.md for filenames).
- Run GUI:
  python -m mlggen.gui
  or
  python scripts/run_mlggen.py --gui

- Run CLI (example):
  python scripts/run_mlggen.py --inputs clip1.mp4 clip2.mp4 --output out_mlg.mp4 --randomize --intensity high

License
- MIT
```
