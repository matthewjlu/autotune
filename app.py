from gevent import monkey
monkey.patch_all()

import os
import time
import shutil
import threading
import numpy as np
import subprocess
import matplotlib
import atexit
import logging
from flask import Flask, request, render_template, send_from_directory, flash, redirect, url_for, Response
from werkzeug.utils import secure_filename
from pydub import AudioSegment
import librosa
import uuid
from flask_socketio import SocketIO, emit
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler
from io import BytesIO

matplotlib.use('Agg')  # Use the 'Agg' backend for non-GUI environments
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # For flash messages
socketio = SocketIO(app, async_mode='gevent')

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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_audio(file_path):
    try:
        return AudioSegment.from_file(file_path)
    except Exception as e:
        logging.error(f"Error loading audio: {e}")
        return None

def pitch_shift_rubberband(input_file, output_file, semitones):
    try:
        command = [
            "rubberband", "-p", str(semitones),
            input_file, output_file
        ]
        subprocess.run(command, check=True)
        logging.info(f"Generated {output_file} with a pitch shift of {semitones} semitones")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error during pitch shifting: {e}")

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
            logging.info(f"Cleaned up {path}")
    threading.Thread(target=cleanup).start()

def clear_all_directories():
    logging.info("Clearing all directories...")
    # Clear processed directories
    for root, dirs, files in os.walk(PROCESSED_FOLDER):
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            shutil.rmtree(dir_path)
            logging.info(f"Cleaned up {dir_path}")

    # Clear uploads directory
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
            logging.info(f"Deleted {file_path}")

    # Delete the pitch plot PNG file
    png_file_path = os.path.join(STATIC_FOLDER, 'pitch_plot.png')
    if os.path.exists(png_file_path):
        os.remove(png_file_path)
        logging.info(f"Deleted {png_file_path}")

@app.route('/')
def index():
    logging.info("Serving index.html")
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    logging.info("Upload endpoint called")
    global processed_counter
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file:
        # Increment the processed counter
        processed_counter += 1

        # Rename session folder to the number it was processed
        session_id = str(processed_counter)
        session_path = os.path.join(PROCESSED_FOLDER, session_id)
        os.makedirs(session_path, exist_ok=True)

        # Name the uploaded file based on the input file name
        filename = secure_filename(file.filename)
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
        logging.info("Rendering results.html with output files")
        return render_template('results.html', pitch_plot='pitch_plot.png', output_files=output_files_relative)
    
    return 'File upload failed'

@app.route('/processed/<session_id>/<filename>')
def download_file(session_id, filename):
    logging.info(f"Downloading file: {filename} from session: {session_id}")
    return send_from_directory(os.path.join(PROCESSED_FOLDER, session_id), filename)

@app.route('/live')
def live():
    logging.info("Serving live.html")
    return render_template('live.html')

@socketio.on('connect')
def handle_connect():
    logging.info("Client connected")
    emit('message', {'data': 'Connected to server'})

@socketio.on('audio_data')
def handle_audio_data(data):
    logging.info("Received audio data")
    try:
        # Process the received audio data
        audio = AudioSegment.from_file(BytesIO(data), format="webm")

        # Here we apply pitch shifting, you can replace this with actual autotune logic
        semitones = 6.0  # Example: shifting up by 1 semitone
        shifted_audio = audio._spawn(audio.raw_data, overrides={
            "frame_rate": int(audio.frame_rate * (2.0 ** (semitones / 12.0)))
        }).set_frame_rate(audio.frame_rate)

        # Convert the processed audio back to a format suitable for sending back to the client
        buf = BytesIO()
        shifted_audio.export(buf, format="wav")
        buf.seek(0)

        emit('processed_audio', buf.read())
    except Exception as e:
        logging.error(f"Error processing audio data: {e}")

if __name__ == '__main__':
    logging.info("Starting server")
    atexit.register(clear_all_directories)
    http_server = WSGIServer(('0.0.0.0', 5000), app, handler_class=WebSocketHandler)
    http_server.serve_forever()
