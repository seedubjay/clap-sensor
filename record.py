import time
import pyaudio
import wave

import scipy.io.wavfile as wavfile

import numpy as np

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 4096

audio = pyaudio.PyAudio()

data = []

def callback(input_data, frame_count, time_info, flags):
    data.append(np.frombuffer(input_data, dtype=np.int16))
    print(np.min(data), np.max(data))
    return input_data, pyaudio.paContinue

stream = audio.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    stream_callback=callback,
                    frames_per_buffer=CHUNK)

stream.start_stream()

#while stream.is_active():
#    time.sleep(0.1)

time.sleep(10)

stream.stop_stream()
stream.close()

audio.terminate()

data = np.ravel(data)

wavfile.write("recording.wav", RATE, data)
