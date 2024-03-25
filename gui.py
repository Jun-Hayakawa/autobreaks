import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from pydub import AudioSegment
import pyaudio
import threading
import random
import numpy as np

def create_slider(frame, text, from_, to): #makes sliders
    label = tk.Label(frame, text=text)
    label.pack(side=tk.LEFT, padx=5)
    slider = ttk.Scale(frame, from_=from_, to=to, orient=tk.HORIZONTAL, length=200, value=(from_ + to) / 2)
    slider.pack(side=tk.LEFT, padx=5)
    return slider

import numpy as np

def pitch_shift(audio_data, input_value):
    # remaps input_value to a more convenient range of numbers
    pitch_factor = 2 - (input_value / 99) * 1.5

    n_samples, n_channels = audio_data.shape
    new_n_samples = int(np.ceil(n_samples * pitch_factor))

    new_audio_data = np.zeros((new_n_samples, n_channels))

    old_indices = np.arange(new_n_samples) / pitch_factor

    lower_indices = np.floor(old_indices).astype(int)
    upper_indices = np.clip(np.ceil(old_indices), 0, n_samples - 1).astype(int)

    weights = old_indices - lower_indices

    # vectorized linear interpolation for each channel
    for channel in range(n_channels):
        new_audio_data[:, channel] = (1 - weights) * audio_data[lower_indices, channel] + weights * audio_data[upper_indices, channel]

    new_audio_data = new_audio_data.astype(np.int16)

    return new_audio_data

def play_slice(slice_index):
    if audio_slices:
        slice_duration_ms = (60 / tempo_slider.get()) * 250  # duration of a sixteenth note in milliseconds
        slice = audio_slices[slice_index]

        if len(slice) < slice_duration_ms:
            silence_duration = slice_duration_ms - len(slice)
            silence = AudioSegment.silent(duration=silence_duration)
            cropped_slice = slice + silence
        else:
            cropped_slice = slice[:slice_duration_ms]
        stream.write(cropped_slice.raw_data)


def play_loop():
    global is_playing
    while is_playing:
        for slice_index in range(len(audio_slices)):
            if not is_playing:
                break
            play_slice(slice_index)

def toggle_play():
    global is_playing, audio_slices, original_slices
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
    global audio_slices, original_slices
    original_slices = pitch_n_slice(input_audio)
    audio_slices = reorder_slices(original_slices)

def pitch_n_slice(audio):
    global not_equal_flag, prev_audio
    pitch = pitch_slider.get()
    if pitch != not_equal_flag:
        audio_data = np.array(audio.get_array_of_samples()).reshape(-1, audio.channels)
        pitched_audio_data = pitch_shift(audio_data, pitch)
        pitched_audio = AudioSegment(
                data=pitched_audio_data.tobytes(),
                sample_width=audio.sample_width,
                frame_rate=audio.frame_rate,
                channels=audio.channels
            )
    else:
        pitched_audio = prev_audio

    not_equal_flag = pitch
    prev_audio = pitched_audio

    slice_duration = len(pitched_audio) // 16
    slices = [pitched_audio[i * slice_duration:(i + 1) * slice_duration] for i in range(16)]
    return slices

def import_file():
    global input_audio, audio_slices, stream, p, not_equal_flag, prev_audio
    file_path = filedialog.askopenfilename(filetypes=[("Audio files", "*.wav *.mp3")])
    if file_path:
        input_audio = AudioSegment.from_file(file_path)
        not_equal_flag = 0
        prev_audio = None
        original_slices = pitch_n_slice(input_audio)
        audio_slices = original_slices
        if stream is not None:
            stream.stop_stream()
            stream.close()
            p.terminate()
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(input_audio.sample_width),
                        channels=input_audio.channels,
                        rate=input_audio.frame_rate,
                        output=True)

def main():
    global audio_slices, original_slices, is_playing, tempo_slider, pitch_slider, play_button, stream, p, pitch_val
    pitch_val = 49
    audio_slices = []
    original_slices = []
    is_playing = False
    stream = None
    p = None

    root = tk.Tk()
    root.title("skibidi breakcore")

    controls_frame = tk.Frame(root)
    controls_frame.pack(pady=10)

    tempo_slider = create_slider(controls_frame, "Tempo", 60, 180)
    pitch_slider = create_slider(controls_frame, "Pitch", 0, 99)
    play_button = tk.Button(controls_frame, text="Play", height=2, width=10, command=toggle_play)
    play_button.pack(side=tk.LEFT, padx=5)
    
    regenerate_button = tk.Button(controls_frame, text="Regenerate", height=2, width=10, command=regenerate_pattern)
    regenerate_button.pack(side=tk.LEFT, padx=5)

    import_button = tk.Button(controls_frame, text="Import File", height=2, width=10, command=import_file)
    import_button.pack(side=tk.LEFT, padx=5)

    root.mainloop()

if __name__ == "__main__":
    main()