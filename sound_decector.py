from array import array
from contextlib import contextmanager
import json
from sys import byteorder
import time

from  bs4 import BeautifulSoup
from googlevoice import Voice
import pyaudio
import requests

LOGGING = True

def log(string):
    if LOGGING:
        print string


CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
RATE = 44100
TIME_TO_RESPOND = 20
AMBIENT_SOUND_TIME = 10

STOPSOUND_URL = 'http://stopsound.herokuapp.com/'
CONTACTS_URL = STOPSOUND_URL + 'contacts/get_actives/'
LOGIN_URL = STOPSOUND_URL + 'auth/login/'

@contextmanager
def recorder():
    """ Used to open a recording stream that gets audio from pyaudio """
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=1, rate=RATE,
        input=True, output=True,
        frames_per_buffer=CHUNK_SIZE)
    yield stream
    stream.stop_stream()
    stream.close()
    p.terminate()

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
        login_data['csrfmiddlewaretoken'] =  token
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


def is_loud(sound_data, threshold):
    log(max(sound_data))
    return max(sound_data) > threshold 

def respond_to_loud_sound():
    send_messages()

def monitor_sound(threshold):
    with recorder() as stream:
        time_hearing = 0
        time_not_hearing = 0

        while time_hearing < TIME_TO_RESPOND:
            timestamp = time.time()
            # little endian, signed short
            sound_data = array('h', stream.read(CHUNK_SIZE))
            if byteorder == 'big':
                sound_data.byteswap()

            if is_loud(sound_data, threshold):
                time_not_hearing = 0
                time_hearing += time.time() - timestamp
                log("Sound for %f seconds" % time_hearing)
                if time_hearing > 5:
                    print "Sound for %f seconds" % time_hearing
            else:
                time_not_hearing += time.time() - timestamp
                #log("Stop hearing sound")
                if time_not_hearing > .1:
                    time_hearing = 0

    send_messages()

def get_ambient_threshold():
    ambient_sound = 0
    samples = 0.0

    print "Calculating ambient sound for %f seconds..." % AMBIENT_SOUND_TIME

    with recorder() as stream:
        start = time.time()
        while time.time() - start < AMBIENT_SOUND_TIME:
            sound_data = array('h', stream.read(CHUNK_SIZE))
            if byteorder == 'big':
                sound_data.byteswap()
            ambient_sound += max(sound_data)
            log(max(sound_data))
            samples += 1.0

    ambient_sound = ambient_sound / samples
    return ambient_sound + 100

if __name__ == '__main__':
    print "Sound monitor -- Stop Sound -- Nu Pledge Class -- GOOOOO"
    threshold = get_ambient_threshold()
    print "Threshold is currently at %f" % threshold

    with open('creds.json', 'r') as f_:
        CREDS = json.load(f_)

    while True:
        print "Monitoring Sound"
        monitor_sound(threshold)
        time.sleep(10)
