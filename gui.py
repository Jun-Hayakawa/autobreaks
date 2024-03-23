import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from pydub import AudioSegment
import pyaudio
import threading
import random

def create_square(frame, text, command):
    square = tk.Button(frame, text=text, height=2, width=5, command=command)
    square.pack(side=tk.LEFT, padx=5, pady=5)
    return square

def create_slider(frame, text, from_, to):
    label = tk.Label(frame, text=text)
    label.pack(side=tk.LEFT, padx=5)
    slider = ttk.Scale(frame, from_=from_, to=to, orient=tk.HORIZONTAL, length=200, value=(from_ + to) / 2)
    slider.pack(side=tk.LEFT, padx=5)
    return slider

def play_slice(slice_index):
    if audio_slices:

        slice_duration_ms = (60 / tempo_slider.get()) * 250  # Duration of a sixteenth note in milliseconds
        original_slice = audio_slices[slice_index]

        if len(original_slice) < slice_duration_ms:
            silence_duration = slice_duration_ms - len(original_slice)
            silence = AudioSegment.silent(duration=silence_duration)
            cropped_slice = original_slice + silence
        else:
            cropped_slice = original_slice[:slice_duration_ms]
        stream.write(cropped_slice.raw_data)

def play_loop():
    global is_playing
    while is_playing:
        for slice_index in range(len(audio_slices)):
            if not is_playing:
                break
            play_slice(slice_index)

def toggle_play():
    global is_playing
    is_playing = not is_playing
    if is_playing:
        play_button.config(text="Pause")
        threading.Thread(target=play_loop).start()
    else:
        play_button.config(text="Play")

def reorder_slices(original_slices):
    dotted_start_seed = random.randint(0, 5)
    quarter_start_seed = random.randint(0, 6)
    dotted_start_index = dotted_start_seed * 2
    quarter_start_index = quarter_start_seed * 2
    dotted = original_slices[dotted_start_index:dotted_start_index + 6]
    quarter = original_slices[quarter_start_index:quarter_start_index + 4]

    order = random.choice([[quarter, dotted, dotted], [dotted, quarter, dotted], [dotted, dotted, quarter]])
    reordered_slices = [item for sublist in order for item in sublist]

    return reordered_slices

def regenerate_pattern():
    global audio_slices
    if original_slices:
        audio_slices = reorder_slices(original_slices)

def import_file():
    global audio_slices, original_slices, stream, p
    file_path = filedialog.askopenfilename(filetypes=[("Audio files", "*.wav *.mp3")])
    if file_path:
        audio = AudioSegment.from_file(file_path)
        slice_duration = len(audio) // 16
        original_slices = [audio[i * slice_duration:(i + 1) * slice_duration] for i in range(16)]
        audio_slices = reorder_slices(original_slices)
        if stream is not None:
            stream.stop_stream()
            stream.close()
            p.terminate()
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(audio.sample_width),
                        channels=audio.channels,
                        rate=audio.frame_rate,
                        output=True)

def main():
    global audio_slices, original_slices, is_playing, tempo_slider, play_button, stream, p
    audio_slices = []
    original_slices = []
    is_playing = False
    stream = None
    p = None

    root = tk.Tk()
    root.title("skibidi breakcore")

    squares_frame = tk.Frame(root)
    squares_frame.pack(pady=10)

    for i in range(16):
        create_square(squares_frame, str(i + 1), lambda slice_index=i: threading.Thread(target=lambda: play_slice(slice_index)).start())

    controls_frame = tk.Frame(root)
    controls_frame.pack(pady=10)

    tempo_slider = create_slider(controls_frame, "Tempo", 60, 180)
    play_button = tk.Button(controls_frame, text="Play", height=2, width=10, command=toggle_play)
    play_button.pack(side=tk.LEFT, padx=5)

    import_button = tk.Button(controls_frame, text="Import File", height=2, width=10, command=import_file)
    import_button.pack(side=tk.LEFT, padx=5)

    regenerate_button = tk.Button(controls_frame, text="Regenerate", height=2, width=10, command=regenerate_pattern)
    regenerate_button.pack(side=tk.LEFT, padx=5)

    root.mainloop()

if __name__ == "__main__":
    main()



