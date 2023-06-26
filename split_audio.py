from pydub import AudioSegment
import os
import ffmpeg
import sys

PATH_PYTHON = "C:\\users\\user\\AppData\\Local\\Programs\\Python\\Python39\\python.exe"

# Add ffmepeg to path
root_dir = os.path.dirname(os.path.abspath(__file__))
audio_dir = os.path.join(root_dir, "audio")

# Get file name from command line
audio_filename = sys.argv[1]
audio_file = os.path.join(audio_dir, audio_filename)

print("Loading audio file")
audio = AudioSegment.from_mp3(audio_file)
audio_length = AudioSegment.duration_seconds
print("Audio length: " + str(audio_length))

for (i, chunk) in enumerate(audio[::1400000]):
    chunk_name = os.path.join(audio_dir, f"chunk{i}.mp3")
    print("Exporting " + chunk_name)
    chunk.export(chunk_name, format="mp3")

print("Done")

# execute whisper.py
os.system(PATH_PYTHON + " whisper.py")