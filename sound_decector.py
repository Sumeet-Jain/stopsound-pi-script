from array import array
from contextlib import contextmanager
import json
import itertools
from sys import byteorder
import time

from  bs4 import BeautifulSoup
from googlevoice import Voice
import pyaudio
import requests
try:
    import spidev
except ImportError:
    spidev = None

def logger():
    LOGGING = False
    def inner(string):
        if LOGGING:
            print string
    return inner

log = logger()


CHUNK_SIZE = 512
FORMAT = pyaudio.paInt16
RATE = 44100

TIME_TO_RESPOND = 5
AMBIENT_SOUND_TIME = 10
QUIET_REST_TIME = .5

LEDS = 32

class LightsController(object):

    def __init__(self, num_leds):
        self.num_leds = num_leds
        # Converts rgb values to right byte values.
        self.gamma = bytearray(256)
        for i in range(256):
            self.gamma[i] =  0x80 | int(pow(float(i) / 255.0, 2.5) * 127.0 + 0.5)
        self.led_buffer = [bytearray(3) for x in range(self.num_leds)]

    def fill(self, r, g, b):
        for led in self.led_buffer:
            # For some reason, colors get passed in the form (g, r, b).
            led[0] = self.gamma[g]
            led[1] = self.gamma[r]
            led[2] = self.gamma[b]

    def update(self, spi):
        final_buff = list(itertools.chain.from_iterable(self.led_buffer))
        final_buff.append(0)
        spi.xfer(final_buff)

class StopSoundSite(object):

    def __init__(self, creds):
        self.STOPSOUND_URL = 'http://stopsound.herokuapp.com/'
        self.CONTACTS_URL = self.STOPSOUND_URL + 'contacts/get_actives/'
        self.LOGIN_URL = self.STOPSOUND_URL + 'auth/login/'
        self.SETTING_URLS = self.STOPSOUND_URL + 'contacts/view_settings/'
        self.CREDS = creds

    @contextmanager
    def login(self):
        with requests.Session() as sesh:
            login_page = sesh.get(self.LOGIN_URL)

            # Grab csrf token from the form
            soup = BeautifulSoup(login_page.text)
            for input_ in soup.find_all('input'):
                if 'name' in input_.attrs and input_.attrs['name'] == 'csrfmiddlewaretoken':
                    token = input_['value']
                    break;

            login_data = {}
            login_data['csrfmiddlewaretoken'] =  token
            login_data['username'] = self.CREDS['stopsound_username']
            login_data['password'] = self.CREDS['stopsound_password']
            login_resp = sesh.post(self.LOGIN_URL, data=login_data)
            assert(login_resp.status_code == 200)

            yield sesh

    def send_messages(self):
        with self.login() as sesh:
            voice = Voice()
            voice.login(email=self.CREDS['googlevoice_email'], passwd=self.CREDS['googlevoice_password'])
            contacts = sesh.get(self.CONTACTS_URL)
            for name, number in contacts.json().items():
                print( "sending a message to %s" % name)
                voice.send_sms(number, "Dear %s, Stop Sound is notifying that you may be too loud. Contact your nearest neighbor." % name)
                print("finished")

    def get_settings(self):
        with self.login() as sesh:
            settings_resp = sesh.get(self.SETTINGS_URL)
            assert(settings_resp.status_code == 200)
            return settings_resp.json()


@contextmanager
def spi_opener():
    if spidev:
        spi = spidev.SpiDev()
        spi.open(0,0)
        spi.max_speed_hz = 40000000
        yield spi
        spi.close()
    else:
        yield

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

def is_loud(sound_data, threshold):
    return max(sound_data) > threshold 

def monitor_sound(threshold, lights, spi):
    with recorder() as stream:
        time_hearing = 0
        time_not_hearing = 0

        timestamp = time.time()
        while time_hearing < TIME_TO_RESPOND:
            try:
                sound_data = array('h', stream.read(CHUNK_SIZE))
                # little endian, signed short
                if byteorder == 'big':
                    sound_data.byteswap()

                now = time.time()
                if is_loud(sound_data, threshold):
                    time_not_hearing = 0
                    time_hearing += now - timestamp
                    #print "Time hearing: %f" % time_hearing
                else:
                    time_not_hearing += now - timestamp
                    if time_not_hearing > QUIET_REST_TIME:
                        time_hearing = 0
                timestamp = now
            except IOError:
                pass
            finally:
                if spi:
                    lights.fill(0, 0, 0)
                    lights.update(spi)


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
    return ambient_sound + 50


if __name__ == '__main__':
    print "Sound monitor -- Stop Sound -- Nu Pledge Class -- GOOOOO"
    threshold = get_ambient_threshold()
    print "Threshold is currently at %f" % threshold

    with open('creds.json', 'r') as f_:
        creds = json.load(f_)
        stop_sound_site = StopSoundSite(creds)

    with spi_opener() as spi:
        while True:
            print "Monitoring Sound"
            lights = LightsController(LEDS)
            monitor_sound(threshold, lights, spi)
            stop_sound_site.send_messages()
            start = time.time()
            if spi:
                while time.time() - start < 10:
                    lights.fill(254, 0, 0)
                    lights.update(spi)
                    time.sleep(.1)
                    lights.fill(0, 0, 0)
                    lights.update(spi)
                    time.sleep(.1)
            time.sleep(5)
