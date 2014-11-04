stopsound-pi-script
===================

This is the Raspberry Pi script for StopSound. It monitors the sound levels in a room and sends out text messages if the room gets too loud.
For example, if you are studying in your room and your flatmates are blasting music, Stop Sound can be used to mitigate the awkwardness and the pain of 
alerting your roommates to quiet down. 

Setup
-----
To install dev dependencies:

1.  Create a virtualenv
2.  Install requirements.txt by `pip install -r requirements.txt`
3.  Install pyaudio `python setup.py install` in the pyaudio folder.
4.  Install SPI python wrapper `python setup.py install` in the python-spi folder.
5.  Run the script!

The raspberry pi script to detect if sound is playing in the room. 

To ensure the script runs, make sure to include a creds.json in the directory in the following format:

```javascript
{

  "stopsound_username": username on stopsound.herokuapp.com, 

  "stopsound_password": pw for stopsound account
}
```

To be able to send the messages, the account on stopsound must be a superuser. Contact Sumeet Jain (sumeetjain1994@gmail.com) to enable superuser access.

Details
-------
The script does the following things in order:

1. Figures out the ambient sound level of the room. It does this by averaging the max sound for x seconds, dictated by the `AMBIENT_SOUND_TIME` constant.
2. It then modifies the ambient basehold by some number dictated by the stopsound website. See the website repo for more information.
3. It then monitors sound by taking the max of each sample. If it hasn't heard a loud enough sound in `QUIET_REST_TIME` seconds, it will reset the time heard counter.
4. After the stopsound has deteected sound for `TIME_TO_RESPOND` seconds, it will alert the specified users through sms messaging. The users it will alert are dictated by the stopsound website. Then, stopsound will strobe its lights for `STROBE_LIGHT` seconds. 
5. Then, to reduce noise, stopsound will sleep for `STOP_DELAY_MINS` minutes, and repeated from number 3 again.
