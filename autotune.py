import numpy as np
import subprocess
import matplotlib.pyplot as plt
from pydub import AudioSegment
import librosa

def load_audio(file_path):
    return AudioSegment.from_file(file_path)

def pitch_shift_rubberband(input_file, output_file, semitones):
    command = [
        "rubberband", "-p", str(semitones),
        input_file, output_file
    ]
    subprocess.run(command, check=True)
    print(f"Generated {output_file} with a pitch shift of {semitones} semitones")

def detect_pitch(y, sr):
    pitches, magnitudes = librosa.core.piptrack(y=y, sr=sr)
    pitch = np.zeros(pitches.shape[1])
    for t in range(pitches.shape[1]):
        index = magnitudes[:, t].argmax()
        pitch[t] = pitches[index, t]
    return pitch

def plot_pitch_time(y, sr):
    pitch = detect_pitch(y, sr)
    times = np.arange(len(pitch)) * (len(y) / sr) / len(pitch)
    plt.figure(figsize=(14, 5))
    plt.plot(times, pitch, label='Detected pitch')
    plt.xlabel('Time (s)')
    plt.ylabel('Frequency (Hz)')
    plt.title('Pitch over Time')
    plt.legend()
    plt.show()

def main(input_file, output_files, target_pitches):
    # Load original audio file
    y, sr = librosa.load(input_file, sr=None)
    
    # Plot pitch vs time for the original audio file
    plot_pitch_time(y, sr)
    
    original_pitch = 440.00  # Assuming original pitch is A4 (440 Hz)
    
    for output_file, target_pitch in zip(output_files, target_pitches):
        semitones = 12 * np.log2(target_pitch / original_pitch)
        pitch_shift_rubberband(input_file, output_file, semitones)

# Example usage
input_file = '/Users/mattlu/Desktop/autotune.wav'
target_pitches = [410.00, 440.00, 523.25, 659.25]  # 410 Hz, A4, C5, E5
output_files = [
    '/Users/mattlu/Desktop/output_410Hz.wav',
    '/Users/mattlu/Desktop/output_A4.wav',
    '/Users/mattlu/Desktop/output_C5.wav',
    '/Users/mattlu/Desktop/output_E5.wav'
]

main(input_file, output_files, target_pitches)
