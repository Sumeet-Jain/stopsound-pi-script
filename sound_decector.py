from array import array
import json
from struct import pack
from sys import byteorder
import time

from  bs4 import BeautifulSoup
from googlevoice import Voice
import pyaudio
import requests
import wave

LOGGING = True

def log(string_):
    if LOGGING:
        print string_


THRESHOLD = 850
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
RATE = 44100
TIME_TO_RESPOND = 10

STOPSOUND_URL = 'http://stopsound.herokuapp.com/'
CONTACTS_URL = STOPSOUND_URL + 'contacts/get_actives/'
LOGIN_URL = STOPSOUND_URL + 'auth/login/'

with open('creds.json', 'r') as f_:
    CREDS = json.load(f_)

def send_messages():
    with requests.Session() as sesh:
        login_page = sesh.get(LOGIN_URL)

        # Grab csrf token from the form
        soup = BeautifulSoup(login_page.text)
        for input_ in soup.find_all('input'):
            if 'name' in input_.attrs and input_.attrs['name'] == 'csrfmiddlewaretoken':
                token = input_['value']
                break;

        login_data = {}
        login_data['csrfmiddlewaretoken'] = token
        login_data['username'] = CREDS['stopsound_username']
        login_data['password'] = CREDS['stopsound_password']
        login_resp = sesh.post(LOGIN_URL, data=login_data)
        assert(login_resp.status_code == 200)

        voice = Voice()
        voice.login(email=CREDS['googlevoice_email'], passwd=CREDS['googlevoice_password'])

        contacts = sesh.get(CONTACTS_URL)
        for name, number in contacts.json().items():
            log( "sending a message to %s" % name)
            voice.send_sms(number, "Dear %s, Stop Sound is notifying that you may be too loud. Contact your nearest neighbor." % name)
            log("finished")


def is_loud(sound_data):
    log(max(sound_data))
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
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=1, rate=RATE,
        input=True, output=True,
        frames_per_buffer=CHUNK_SIZE)

    time_hearing = 0
    time_not_hearing = 0

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
                time_not_hearing = 0
                time_hearing += time.time() - timestamp
                log("Sound for %f seconds" % time_hearing)
                if time_hearing > 5:
                    print "Sound for %f seconds" % time_hearing
            else:
                time_not_hearing += time.time() - timestamp
                log("Stop hearing sound")
                if time_not_hearing > .1:
                    time_hearing = 0
    finally:
        sample_width = p.get_sample_size(FORMAT)
        stream.stop_stream()
        stream.close()
        p.terminate()

    send_messages()

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
