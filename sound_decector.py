from array import array
from contextlib import contextmanager
from ctypes import *
import itertools
import json
from sys import byteorder
import time

from  bs4 import BeautifulSoup
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

TIME_TO_RESPOND = 10
AMBIENT_SOUND_TIME = 10
QUIET_REST_TIME = .35
STOP_DELAY_MINS = 1
STROBE_LIGHT = 20

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
        if not spi:
            return
        final_buff = list(itertools.chain.from_iterable(self.led_buffer))
        final_buff.append(0)
        spi.xfer(final_buff)

    def strobe(self, r, g, b, end_time, spi):
        if not spi:
            return
        start = time.time()
        while time.time() - start < end_time:
            self.fill(r, g, b)
            self.update(spi)
            time.sleep(.1)
            self.fill(0, 0, 0)
            self.update(spi)
            time.sleep(.1)

class StopSoundSite(object):

    def __init__(self, creds):
        self.STOPSOUND_URL = 'http://stopsound.herokuapp.com/'
        self.SEND_MESSAGES_URL = self.STOPSOUND_URL + 'contacts/send_messages/'
        self.LOGIN_URL = self.STOPSOUND_URL + 'auth/login/'
        self.SETTINGS_URL = self.STOPSOUND_URL + 'contacts/settings/'
        self.CREDS = creds

    def check_internet_connection(self):
        try:
            requests.get('http://google.com', timeout=5)
            return True
        except requests.ConnectionError:
            pass
        return False

    @contextmanager
    def login(self):
        with requests.Session() as sesh:
            login_page = sesh.get(self.LOGIN_URL)

            # Grab csrf token from the form
            soup = BeautifulSoup(login_page.text)
            for input_ in soup.find_all('input'):
                if 'name' in input_.attrs and input_.attrs['name'] == 'csrfmiddlewaretoken':
                    token = input_['value']
                    break

            login_data = {}
            login_data['csrfmiddlewaretoken'] = token
            login_data['username'] = self.CREDS['stopsound_username']
            login_data['password'] = self.CREDS['stopsound_password']
            login_resp = sesh.post(self.LOGIN_URL, data=login_data)
            login_resp.raise_for_status()

            yield sesh

    def send_messages(self):
        with self.login() as sesh:
            resp = sesh.get(self.SEND_MESSAGES_URL)
            resp.raise_for_status()


    def get_settings(self):
        with self.login() as sesh:
            settings_resp = sesh.get(self.SETTINGS_URL)
            settings_resp.raise_for_status()
            return settings_resp.json()


@contextmanager
def spi_opener():
    """ Opens a connection to spidev on the pi. Used to pass info to lights """
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
    # Following block gets rid of annoying config errors by ALSA
    def py_error_handler(filename, line, function, err, fmt):
        pass
    ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
    c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
    asound = cdll.LoadLibrary('libasound.so')
    asound.snd_lib_error_set_handler(c_error_handler) 

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
                else:
                    time_not_hearing += now - timestamp
                    if time_not_hearing > QUIET_REST_TIME:
                        time_hearing = 0
                timestamp = now
            except IOError:
                print "IOerror"
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
            try:
                sound_data = array('h', stream.read(CHUNK_SIZE))
                if byteorder == 'big':
                    sound_data.byteswap()
                ambient_sound += max(sound_data)
                log(max(sound_data))
                samples += 1.0
            except IOError:
                # TODO Make this a smarter error. Only for input overflow
                print "IOerror"

    ambient_sound = (ambient_sound / samples) + 50
    return ambient_sound + abs(ambient_sound)*.10


if __name__ == '__main__':
    print "Sound monitor -- Stop Sound -- Nu Pledge Class -- GOOOOO"
    print "Checking Internet"
    with open('creds.json', 'r') as f_:
        creds = json.load(f_)
        stop_sound_site = StopSoundSite(creds)

    lights = LightsController(LEDS)

    if not stop_sound_site.check_internet_connection():
        print "No Internet. Strobing Light then turning off"
        with spi_opener() as spi:
            lights.strobe(0, 0, 254, STROBE_LIGHT / 2, spi)
            lights.strobe(0, 0, 0, 1, spi)
            quit()
    else:
        print "Has Internet. Continuing"

    threshold = get_ambient_threshold()
    sound_level_coef = stop_sound_site.get_settings()['sound_level']
    print "Before managing the settings, threshold is: %f" % threshold
    if threshold > 0:
        # TODO If threshold is negative... idk
        threshold = threshold * sound_level_coef
    print "Threshold is currently at %f" % threshold

    with spi_opener() as spi:
        while True:
            print "Monitoring Sound"
            monitor_sound(threshold, lights, spi)
            print "Detected sound. Sending Messages"
            stop_sound_site.send_messages()
            print "Finished sending messages"
            start = time.time()
            print "Strobing"
            lights.strobe(254, 0, 0, STROBE_LIGHT, spi)
            print "Sleeping for {0}".format(60*STOP_DELAY_MINS)
            time.sleep(60*STOP_DELAY_MINS)
