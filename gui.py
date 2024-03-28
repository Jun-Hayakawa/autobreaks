import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from pydub import AudioSegment
import pyaudio
import threading
import random
import numpy as np
import math

def create_slider(frame, text, from_, to): #makes sliders. yum
    label = tk.Label(frame, text=text)
    label.pack(side=tk.LEFT, padx=5)
    slider = ttk.Scale(frame, from_=from_, to=to, orient=tk.HORIZONTAL, length=200, value=(from_ + to) / 2)
    slider.pack(side=tk.LEFT, padx=5)
    return slider

# the interpolation helper function carried out by threads. takes the non-integer indices created in the new array and interpolates values using
# the weights calculated in pitch_shift()
def process_channel(channel, audio_data, new_audio_data, lower_indices, upper_indices, weights):
    new_audio_data[:, channel] = (1 - weights) * audio_data[lower_indices, channel] + weights * audio_data[upper_indices, channel]

# a dope ass pitch shifting algorithm. does not preserve time to avoid artifacting. effectively stretches or compresses all the samples in the input audio.
def pitch_shift(audio_data, input_value):
    # remaps input_value to a more convenient range of numbers (0.5 - 2, where 0.5 = one octave down, 2 = one octave up)
    pitch_factor = 2 - (input_value / 99) * 1.5

    #creates an empty array with the calculated length of the pitched audio
    n_samples, n_channels = audio_data.shape
    new_n_samples = int(np.ceil(n_samples * pitch_factor))
    new_audio_data = np.zeros((new_n_samples, n_channels))

    # makes the number of indices in the original audio data fit to the size of the new empty array
    old_indices = np.arange(new_n_samples) / pitch_factor

    # finds the closest integer index in the old audio data for interpolation
    lower_indices = np.floor(old_indices).astype(int)
    upper_indices = np.clip(np.ceil(old_indices), 0, n_samples - 1).astype(int)

    # calculates weights for interpolation
    weights = old_indices - lower_indices

    # creates and starts a thread for each channel
    threads = []
    for channel in range(n_channels):
        thread = threading.Thread(target=process_channel, args=(channel, audio_data, new_audio_data, lower_indices, upper_indices, weights))
        threads.append(thread)
        thread.start()

    # combines threads when finished
    for thread in threads:
        thread.join()

    # converts the new audio data to 16-bit integers so pydub can play it
    new_audio_data = new_audio_data.astype(np.int16)

    return new_audio_data

# sequentially loads each slice into pydub's audio stream at a rate calculated by the bpm slider
def play_slice(slice_index):
    global slices_fr
    if slices_fr:
        slice_duration_ms = (60 / tempo_slider.get()) * 250  # duration of a sixteenth note in milliseconds from bpm
        slice = slices_fr[slice_index]

        # crops audio to fit the length of a sixteenth note by either padding with silence or by cutting it off
        if len(slice) < slice_duration_ms:
            silence_duration = slice_duration_ms - len(slice)
            silence = AudioSegment.silent(duration=silence_duration)
            cropped_slice = slice + silence
        else:
            cropped_slice = slice[:slice_duration_ms]
        stream.write(cropped_slice.raw_data)

# THIS TOOK SO LONG TO TUNE
def fill_seed(chaos_parameter, bar_count): 
    numbers = [0, 1, 2, 3, 4]
    unscaled_probabilities = []
    for i in range(5):
        if bar_count == 7:
            unscaled_probabilities.append(math.exp(i*chaos_parameter))
        elif bar_count == 3:
            unscaled_probabilities.append(math.exp(i*(chaos_parameter - 0.2)))
        elif bar_count == 1 or bar_count == 5:
            unscaled_probabilities.append(math.exp(i*(chaos_parameter - 0.6)))
    probabilities = [i / sum(unscaled_probabilities) for i in unscaled_probabilities]
    number = random.choices(numbers, probabilities)[0]
    print(probabilities)
    binary_list = [1] * number + [0] * (4 - number)
    random.shuffle(binary_list)
    return binary_list

def reverse(slices, i):
    reversed = []
    for slice in slices[i:i+4]:
        reversed_audio_data = slice.reverse()
        reversed.append(reversed_audio_data)
    reversed.reverse()
    result = slices[:i] + reversed + slices[i+4:]
    return result

def newpattern():
    return reorder_slices(pitch_n_slice(input_audio))

def stutter(slices, i): # use i = 0, 4, 8, or 12
    thirtysecond_stutter = slices[i][:len(slices[i]) // 2] + slices[i][:len(slices[i]) // 2]
    var1 = [slices[i], slices[i], slices[i], slices[i]]
    var2 = [slices[i], slices[i], slices[i+2], slices[i+3]]
    var3 = [slices[i], slices[i], slices[i+2], slices[i+2]]
    var4 = [slices[i], slices[i], thirtysecond_stutter, thirtysecond_stutter]
    stutter = random.choice([var1, var2, var3, var4])
    result = slices[:i] + stutter + slices[i+4:]
    return result

def chop(slices, i):
    fill = []
    for j in range(i, i + 4):
        slice = slices[j]
        half_length = len(slice) // 2
        silence = AudioSegment.silent(duration=half_length)
        cut_slice = slice[:half_length] + silence
        fill.append(cut_slice)
    result = slices[:i] + fill + slices[i+4:]
    return result

def extended_dotted(slices):
    return slices[10:] + slices[10:] + slices[10:14]

def fill_selector(bar_count):
    global slices, slices_fr
    if bar_count == 7:
        slices_fr = random.choice([slices, extended_dotted(slices), newpattern()])
    if bar_count % 2 == 1:
        print(bar_count)
        reverse_seed = fill_seed(chaos_slider.get(), bar_count)
        stutter_seed = fill_seed(chaos_slider.get(), bar_count)
        chop_seed = fill_seed(chaos_slider.get(), bar_count)
        for index, value in enumerate(reverse_seed):
            if value == 1:
                slices_fr = reverse(slices_fr, index*4)
        for index, value in enumerate(stutter_seed):
            if value == 1:
                slices_fr = stutter(slices_fr, index*4)
        for index, value in enumerate(chop_seed):
            if value == 1:
                slices_fr = chop(slices_fr, index*4)
    else:
        slices_fr = slices
    return slices_fr

# loops through slices infinitely to loop audio
def play_loop(): 
    global is_playing, slices_fr
    bar_count = 0
    sixteenth_note_count = 0
    while is_playing:
        slices_fr = fill_selector(bar_count)
        for slice_index in range(len(slices_fr)):
            if not is_playing:
                break
            sixteenth_note_count += 1
            bar_count = np.floor(sixteenth_note_count / 16) % 8
            play_slice(slice_index)

# self explanatory, toggles play
def toggle_play():
    global is_playing
    is_playing = not is_playing
    if is_playing:
        play_button.config(text="Pause")
        threading.Thread(target=play_loop).start()
    else:
        play_button.config(text="Play")

# randomly selects quarter and dotted quarter note blocks of slices and arranges them into a new pattern
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

# command for regenerate button. updates pitch value from slider and then regenerates a pattern using reorder_slices()
def regenerate_pattern():
    global slices, original_slices
    original_slices = pitch_n_slice(input_audio)
    slices = reorder_slices(original_slices)

# applies pitch shift function and then re-splits the new audio. this is necessary because changing pitch also changes length.
# uses a flag to check if the pitch slider's value has actually changed, so that the computation-heavy pitch shifting function
# is only called when actually necessary. 
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

# handles inital setup when a new audio file is loaded
def import_file():
    global input_audio, slices, stream, p, not_equal_flag, prev_audio
    file_path = filedialog.askopenfilename(filetypes=[("Audio files", "*.wav *.mp3")])
    if file_path:
        input_audio = AudioSegment.from_file(file_path)
        not_equal_flag = 0
        prev_audio = None
        original_slices = pitch_n_slice(input_audio)
        slices = original_slices
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
    global slices, original_slices, slices_fr, is_playing, tempo_slider, pitch_slider, chaos_slider, play_button, stream, p, pitch_val
    pitch_val = 49
    slices = []
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
    chaos_slider = create_slider(controls_frame, "Chaos", -1, 0.1)
    play_button = tk.Button(controls_frame, text="Play", height=2, width=10, command=toggle_play)
    play_button.pack(side=tk.LEFT, padx=5)
    
    regenerate_button = tk.Button(controls_frame, text="Regenerate", height=2, width=10, command=regenerate_pattern)
    regenerate_button.pack(side=tk.LEFT, padx=5)

    import_button = tk.Button(controls_frame, text="Import File", height=2, width=10, command=import_file)
    import_button.pack(side=tk.LEFT, padx=5)

    root.mainloop()

if __name__ == "__main__":
    main()