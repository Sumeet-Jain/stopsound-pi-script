stopsound-pi-script
===================

To install dev dependencies:
1.  Create a virtualenv
2.  Install requirements.txt by `pip install -r requirements.txt`
3.  Install pyaudio
4.  Run the script!

The raspberry pi script to detect if sound is playing in the room. 

To ensure the script runs, make sure to include a creds.json in the directory in the following format:

```javascript
{

  "stopsound_username": username on stopsound.herokuapp.com, 

  "stopsound_password": pw for stopsound account,

  "googlevoice_email": email for google voice account,

  "googlevoice_password": password for google voice account

}
```

