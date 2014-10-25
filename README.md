stopsound-pi-script
===================

The raspberry pi script to detect if sound is playing in the room. 

To ensure the script runs, make sure to include a creds.json in the directory in the following format:

{
  "stopsound_username": username on stopsound.herokuapp.com,
  "stopsound_password": pw for stopsound account,
  "googlevoice_email": email for google voice account,
  "googlevoice_password": password for google voice account
}
