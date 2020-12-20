import time
import pyaudio
import wave

from datetime import datetime, timedelta

from scipy import signal

from multiprocessing import Process, Value

import lifxlan
import numpy as np

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
BUFFER = 512

light = lifxlan.Light("D0:73:D5:58:62:32", "192.168.2.239")

click_min_gap = .1
click_max_gap = .6

def try_action(click, my, actual):
    time.sleep(click_max_gap)
    if my != actual.value: return
    cur = click.value
    click.value = 0
    is_on = light.get_power()
    if cur == 2:
        light.set_power(65535-is_on, 500, True)
    if cur == 3:
        if is_on > 0: light.set_power(65535, 0, True)
        if is_on == 0 or light.get_color()[2] < 65535:
            light.set_color([0,0,65535,3500], 0 if is_on == 0 else 500, True)
        else:
            light.set_color([0,0,16384,1500], 2000, True)
        if is_on == 0: light.set_power(65535, 500, True)

if __name__ == '__main__':

    click_count = Value('i', 0)
    last_click_ts = Value('d', 0)
    last_click = datetime(1970,1,1)

    def clicked():
        global click_count
        global last_click
        now = datetime.now()
        t = now-last_click
        last_click = now
        last_click_ts.value = last_click.timestamp()
        if t < timedelta(seconds=click_min_gap):
            click_count.value = 0
            print("click", click_count.value, t)
        else:
            click_count.value += 1
            print("click", click_count.value, t)
            p = Process(target=try_action, args=(click_count, last_click_ts.value, last_click_ts))
            p.start()

    hp_sos = signal.cheby1(10, 5, 9000, 'hp', fs=RATE, output='sos')
    lp_sos = signal.cheby1(10, 5, 2000, 'lp', fs=RATE, output='sos')

    db_cutoff = 22
    db_minimum = 15
    db_hp_lp_diff = 0
    last_start = datetime(1970,1,1)
    last_end = datetime(1970,1,2)

    def process_chunk(data):
        global last_start
        global last_end
        padded = np.zeros(len(data)*5//4)
        padded[len(data)//8:len(data)*9//8] = data
        hp_data = signal.sosfilt(hp_sos,padded)[len(data)//8:len(data)*9//8]
        hp_db = 20*np.log10(np.sqrt(np.sum(hp_data**2)/len(hp_data)))
        lp_data = signal.sosfilt(lp_sos,padded)[len(data)//8:len(data)*9//8]
        lp_db = 20*np.log10(np.sqrt(np.sum(lp_data**2)/len(lp_data)))

        if hp_db > db_minimum:print(hp_db, lp_db)

        if hp_db > db_cutoff and lp_db - hp_db < db_hp_lp_diff:
            if last_end > last_start:
                last_start = datetime.now()
        elif hp_db < db_minimum:
            if last_start > last_end:
                last_end = datetime.now()
                print(last_end-last_start)
                if last_end - last_start < timedelta(seconds=.15):
                    clicked()

    prev = np.zeros(BUFFER)

    def callback(input_data, frame_count, time_info, flags):
        global prev
        data = np.frombuffer(input_data, dtype=np.int16)
        process_chunk(np.concatenate((prev,data)))
        prev = data
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
        time.sleep(1)
    stream.stop_stream()
    stream.close()
    audio.terminate()
