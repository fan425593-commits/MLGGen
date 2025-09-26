from moviepy.editor import concatenate_videoclips, VideoFileClip

def concat_files(video_paths, output_path, codec="libx264", audio_codec="aac"):
    clips = []
    for p in video_paths:
        try:
            c = VideoFileClip(p)
            clips.append(c)
        except Exception as e:
            print("Failed to load", p, e)
    if not clips:
        raise RuntimeError("No clips to concatenate")
    final = concatenate_videoclips(clips, method="compose")
    final.write_videofile(output_path, codec=codec, audio_codec=audio_codec)
    for c in clips:
        c.close()