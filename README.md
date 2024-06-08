Live Autotune - MUS 17
Overview

The Live Autotune project is a web application that allows users to record their audio in real-time, apply an autotune effect to it, and then listen to the processed audio. This project is part of the MUS 17 coursework.
Features

    Real-time audio recording using the browser's microphone.
    Application of autotune effects with extreme pitch shifting.
    Playback of processed audio.
    Cleanup of uploaded and processed files after a specified delay.

Technologies Used

    Python (Flask, Flask-SocketIO)
    JavaScript (MediaRecorder API, Socket.IO)
    HTML/CSS
    Pydub for audio processing
    Gevent for asynchronous server operations

Installation
Prerequisites

    Python 3.8 or higher
    Node.js and npm

Setup

    Clone the repository:

    sh

git clone <repository_url>
cd autotune

Create a virtual environment and activate it:

sh

python -m venv .venv
source .venv/bin/activate

Install the required Python packages:

sh

pip install -r requirements.txt

Install Node.js dependencies:

sh

    npm install socket.io

Running the Server

    Start the Flask server:

    sh

python app.py

Open your browser and navigate to:

arduino

    http://127.0.0.1:5000

Usage

    Navigate to the Home Page:
    Open your browser and go to http://127.0.0.1:5000.

    Recording Audio:
        Click the "Start Recording" button to begin recording.
        Click the "Stop Recording" button to stop and process the recording.

    Listening to Processed Audio:
        After stopping the recording, the processed audio will be played back automatically.
        You can replay the audio using the audio player controls.

Directory Structure

scss

autotune/
│
├── templates/
│   ├── index.html
│   ├── live.html
│   ├── results.html
│
├── static/
│   ├── styles.css
│
├── uploads/
│   ├── (uploaded audio files)
│
├── processed/
│   ├── (processed audio files)
│
├── app.py
├── requirements.txt
└── README.md

Troubleshooting

If you encounter issues, check the following:

    Ensure you have the correct versions of Python and Node.js installed.
    Check the browser console and server logs for errors or warnings.

License

This project is licensed under the MIT License. See the LICENSE file for details.
Acknowledgements

    The Flask and Flask-SocketIO communities for their excellent libraries.
    The Pydub library for easy audio processing in Python.
    The MediaRecorder API for enabling in-browser audio recording.