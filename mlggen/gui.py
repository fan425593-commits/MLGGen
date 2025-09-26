import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
from mlggen.assets import resolve_assets
from mlggen.effects import make_mlg_clip_sequence
from moviepy.editor import CompositeVideoClip

DEFAULT_OUTPUT = "mlg_output.mp4"

class MLGGenGUI:
    def __init__(self, root):
        self.root = root
        root.title("MLGGen (simple)")
        self.video_paths = []
        self.assets = resolve_assets()
        self.intensity = tk.StringVar(value="medium")
        self.randomize = tk.BooleanVar(value=True)
        self.output_path = tk.StringVar(value=os.path.abspath(DEFAULT_OUTPUT))

        frm = ttk.Frame(root, padding=10)
        frm.pack(fill="both", expand=True)

        btn_add = ttk.Button(frm, text="Add video(s)", command=self.add_videos)
        btn_add.grid(row=0, column=0, sticky="w")
        btn_clear = ttk.Button(frm, text="Clear list", command=self.clear_list)
        btn_clear.grid(row=0, column=1, sticky="w")
        ttk.Label(frm, text="Selected videos:").grid(row=1, column=0, columnspan=3, sticky="w")
        self.listbox = tk.Listbox(frm, width=80, height=8)
        self.listbox.grid(row=2, column=0, columnspan=3, pady=5)
        ttk.Checkbutton(frm, text="Randomize effects", variable=self.randomize).grid(row=3, column=0, sticky="w")
        ttk.Label(frm, text="Intensity:").grid(row=3, column=1, sticky="e")
        ttk.OptionMenu(frm, self.intensity, "medium", "low", "medium", "high").grid(row=3, column=2, sticky="w")
        ttk.Label(frm, text="Output:").grid(row=4, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.output_path, width=55).grid(row=4, column=1, columnspan=2, sticky="w")
        ttk.Button(frm, text="Browse...", command=self.browse_output).grid(row=4, column=3, sticky="w")
        self.progress = ttk.Label(frm, text="")
        self.progress.grid(row=5, column=0, columnspan=4, sticky="w")
        ttk.Button(frm, text="Generate MLG", command=self.generate).grid(row=6, column=0, pady=8)

    def add_videos(self):
        paths = filedialog.askopenfilenames(title="Choose videos", filetypes=[("MP4 files", "*.mp4 *.mov *.avi *.mkv"), ("All files", "*.*")])
        for p in paths:
            self.video_paths.append(p)
            self.listbox.insert("end", p)

    def clear_list(self):
        self.video_paths = []
        self.listbox.delete(0, "end")

    def browse_output(self):
        p = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 file", "*.mp4")])
        if p:
            self.output_path.set(p)

    def generate(self):
        if not self.video_paths:
            messagebox.showwarning("No input", "Please add at least one video")
            return
        out = self.output_path.get()
        intensity = self.intensity.get()
        self.progress.config(text="Starting render...")
        thread = threading.Thread(target=self._render_thread, args=(list(self.video_paths), out, intensity))
        thread.daemon = True
        thread.start()

    def _render_thread(self, paths, out, intensity):
        try:
            # Build assets dict (could add GUI to change assets)
            assets = self.assets
            self._update_progress("Loading and applying MLG effects...")
            clip = make_mlg_clip_sequence(paths, assets, target_duration=12, intensity=intensity)
            self._update_progress("Writing output (this may take a while)...")
            # Write file via moviepy
            clip.write_videofile(out, codec="libx264", audio_codec="aac", threads=2)
            clip.close()
            self._update_progress("Done! Saved to: {}".format(out))
            messagebox.showinfo("Done", "MLG video saved to:\n{}".format(out))
        except Exception as e:
            self._update_progress("Error: {}".format(e))
            messagebox.showerror("Error", str(e))

    def _update_progress(self, text):
        def cb():
            self.progress.config(text=text)
        self.root.after(1, cb)

def main():
    root = tk.Tk()
    app = MLGGenGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()