import os
import time
import shutil
import threading
import numpy as np
import subprocess
import matplotlib
import atexit
from flask import Flask, request, render_template, send_from_directory
from pydub import AudioSegment
import librosa
import uuid

matplotlib.use('Agg')  # Use the 'Agg' backend for non-GUI environments
import matplotlib.pyplot as plt

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
STATIC_FOLDER = 'static'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

# Counter for processed sessions
processed_counter = 0

# Mapping for target pitches
pitch_mapping = {
    410.00: '410Hz',
    440.00: 'A4',
    523.25: 'C5',
    659.25: 'E5'
}

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

def plot_pitch_time(y, sr, output_path):
    pitch = detect_pitch(y, sr)
    times = np.arange(len(pitch)) * (len(y) / sr) / len(pitch)
    plt.figure(figsize=(14, 5))
    plt.plot(times, pitch, label='Detected pitch')
    plt.xlabel('Time (s)')
    plt.ylabel('Frequency (Hz)')
    plt.title('Pitch over Time')
    plt.legend()
    plt.savefig(output_path)
    plt.close()  # Close the plot to free up memory

def schedule_cleanup(path, delay=600):
    def cleanup():
        time.sleep(delay)
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"Cleaned up {path}")
    threading.Thread(target=cleanup).start()

def clear_all_directories():
    print("Clearing all directories...")
    # Clear processed directories
    for root, dirs, files in os.walk(PROCESSED_FOLDER):
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            shutil.rmtree(dir_path)
            print(f"Cleaned up {dir_path}")

    # Clear uploads directory
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
            print(f"Deleted {file_path}")

    # Delete the pitch plot PNG file
    png_file_path = os.path.join(STATIC_FOLDER, 'pitch_plot.png')
    if os.path.exists(png_file_path):
        os.remove(png_file_path)
        print(f"Deleted {png_file_path}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    global processed_counter
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file:
        # Increment the processed counter
        processed_counter += 1

        # Rename session folder to the number it was processed
        session_id = str(processed_counter)
        session_path = os.path.join(PROCESSED_FOLDER, session_id)
        os.makedirs(session_path, exist_ok=True)

        # Name the uploaded file based on the input file name
        filename = file.filename
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Process the file
        y, sr = librosa.load(file_path, sr=None)
        pitch_plot_path = os.path.join(STATIC_FOLDER, 'pitch_plot.png')
        plot_pitch_time(y, sr, pitch_plot_path)

        original_pitch = 440.00  # Assuming original pitch is A4 (440 Hz)
        target_pitches = [410.00, 440.00, 523.25, 659.25]  # Example target pitches
        output_files = []
        for target_pitch in target_pitches:
            pitch_name = pitch_mapping[target_pitch]
            output_filename = f"{pitch_name}.wav"
            output_file_path = os.path.join(session_path, output_filename)
            semitones = 12 * np.log2(target_pitch / original_pitch)
            pitch_shift_rubberband(file_path, output_file_path, semitones)
            output_files.append(output_file_path)

        # Schedule cleanup of the session-specific directory
        schedule_cleanup(session_path)

        output_files_relative = [os.path.join(session_id, os.path.basename(f)) for f in output_files]
        return render_template('results.html', pitch_plot='pitch_plot.png', output_files=output_files_relative)
    
    return 'File upload failed'

@app.route('/processed/<session_id>/<filename>')
def download_file(session_id, filename):
    return send_from_directory(os.path.join(PROCESSED_FOLDER, session_id), filename)

if __name__ == '__main__':
    atexit.register(clear_all_directories)
    app.run(debug=True)
