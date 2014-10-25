from sys import byteorder
from array import array
from struct import pack
import time

import pyaudio
import wave

THRESHOLD = 500
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
RATE = 44100

def is_loud(sound_data):
    print max(sound_data)
    return max(sound_data) > THRESHOLD

def normalize(sound_data):
    "Average the volume out"
    MAXIMUM = 16384
    times = float(MAXIMUM) / max(abs(i) for i in sound_data)

    r = array('h')
    for i in sound_data:
        r.append(int(i*times))
    return r

def trim(sound_data):
    "Trim the blank spots at the start and end"
    def _trim(sound_data):
        sound_started = False
        r = array('h')

        for i in sound_data:
            if not sound_started and abs(i)>THRESHOLD:
                sound_started = True
                r.append(i)
            elif sound_started:
                r.append(i)
        return r

    # Trim to the left
    sound_data = _trim(sound_data)

    # Trim to the right
    sound_data.reverse()
    sound_data = _trim(sound_data)
    sound_data.reverse()
    return sound_data

def add_silence(sound_data, seconds):
    "Add silence to the start and end of 'sound_data' of length 'seconds' (float)"
    r = array('h', [0 for i in xrange(int(seconds*RATE))])
    r.extend(sound_data)
    r.extend([0 for i in xrange(int(seconds*RATE))])
    return r

def respond_to_loud_sound():
    pass

def monitor_sound():
    TIME_TO_RESPOND = 30

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=1, rate=RATE,
        input=True, output=True,
        frames_per_buffer=CHUNK_SIZE)

    time_hearing = 0

    recording = array('h')

    try:
        while time_hearing < TIME_TO_RESPOND:
            timestamp = time.time()
            # little endian, signed short
            sound_data = array('h', stream.read(CHUNK_SIZE))
            if byteorder == 'big':
                sound_data.byteswap()
            recording.extend(sound_data)

            if is_loud(sound_data):
                time_hearing += time.time() - timestamp
                print "Sound for %f seconds" % time_hearing
            else:
                time_hearing = 0
                print "Stop hearing sound"
            #time.sleep(.1)
    finally:
        sample_width = p.get_sample_size(FORMAT)
        stream.stop_stream()
        stream.close()
        p.terminate()

    respond_to_loud_sound()

    """`
    # Used to write to file
    recording = normalize(recording)
    recording = trim(recording)
    recording = add_silence(recording, 0.5)
    return sample_width, recording
    """

def record_to_file(path):
    "Records from the microphone and outputs the resulting data to 'path'"
    sample_width, data = monitor_sound()
    data = pack('<' + ('h'*len(data)), *data)

    with wave.open(path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(sample_width)
        wf.setframerate(RATE)
        wf.writeframes(data)

if __name__ == '__main__':
    print "Sound monitor -- Stop Sound -- Pledge Class -- GOOOOO"
    monitor_sound()
