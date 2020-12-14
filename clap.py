import time
import pyaudio
import wave

from datetime import datetime, timedelta

from scipy import signal

import numpy as np

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
BUFFER = 512

last_click = datetime(1970,1,1)

def clicked():
    global last_click
    print("click")
    now = datetime.now()
    if now - last_click < timedelta(seconds=1):
        print("double click")
    last_click = now


db_cutoff = 25
last_start = datetime(1970,1,1)
last_end = datetime(1970,1,2)

def process_chunk(data):
    global last_start
    global last_end
    db = 20*np.log10(np.sqrt(np.sum(data**2)/len(data)))
    print(db)
    if db > db_cutoff:
        if last_end > last_start:
            last_start = datetime.now()
    else:
        if last_start > last_end:
            last_end = datetime.now()
            if last_end - last_start < timedelta(seconds=.1):
                clicked()

sos = signal.cheby1(50, 5, 10000, 'hp', fs=RATE, output='sos')

def callback(input_data, frame_count, time_info, flags):
    data = np.frombuffer(input_data, dtype=np.int16)
    padded = np.zeros(len(data)*5//4)
    padded[len(data)//8:len(data)*9//8] = data
    data = signal.sosfilt(sos,padded)[len(data)//8:len(data)*9//8]
    process_chunk(data)
    return input_data, pyaudio.paContinue

audio = pyaudio.PyAudio()

stream = audio.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    stream_callback=callback,
                    frames_per_buffer=BUFFER)

stream.start_stream()

while stream.is_active():
    time.sleep(0.1)

stream.stop_stream()
stream.close()

audio.terminate()

wavfile.write("recording.wav", RATE, data)
