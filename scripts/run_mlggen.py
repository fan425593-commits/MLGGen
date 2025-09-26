import argparse
import sys
import os

def run_gui():
    # Launch the GUI
    from mlggen.gui import main
    main()

def run_cli(args):
    from mlggen.assets import resolve_assets
    from mlggen.effects import make_mlg_clip_sequence
    assets = resolve_assets()
    clip = make_mlg_clip_sequence(args.inputs, assets, target_duration=args.duration, intensity=args.intensity)
    print("Writing to", args.output)
    clip.write_videofile(args.output, codec="libx264", audio_codec="aac")

def parse():
    parser = argparse.ArgumentParser(description="MLGGen runner")
    parser.add_argument("--gui", action="store_true", help="Start GUI")
    parser.add_argument("--inputs", nargs="+", help="Input video files for CLI mode")
    parser.add_argument("--output", default="mlg_cli_output.mp4", help="Output file")
    parser.add_argument("--duration", type=float, default=12.0, help="Target duration (seconds) for CLI MLG montage")
    parser.add_argument("--intensity", choices=["low", "medium", "high"], default="medium", help="Effect intensity")
    return parser.parse_args()

def main():
    args = parse()
    if args.gui:
        run_gui()
    elif args.inputs:
        run_cli(args)
    else:
        print("No mode selected. Use --gui or provide --inputs ...")
        sys.exit(2)

if __name__ == "__main__":
    main()