from flask import Flask, request, render_template, jsonify
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client
import os

app = Flask(__name__)

# Your Twilio credentials
TWILIO_ACCOUNT_SID = 'YOUR_ACCOUNT_SID'
TWILIO_AUTH_TOKEN = 'YOUR_AUTH_TOKEN'
TWILIO_NUMBER = 'YOUR_TWILIO_NUMBER'
TWIML_APPLICATION_SID = 'YOUR_TWIML_APP_SID'

# Initialize Twilio client
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

@app.route('/')
def home():
    return render_template('voice.html')

@app.route('/token', methods=['GET'])
def get_token():
    # Create access token
    token = AccessToken(
        TWILIO_ACCOUNT_SID,
        TWIML_APPLICATION_SID,
        TWILIO_AUTH_TOKEN,
        identity="user"
    )
    
    # Create a Voice grant and add to token
    voice_grant = VoiceGrant(
        outgoing_application_sid=TWIML_APPLICATION_SID,
        incoming_allow=True,
    )
    token.add_grant(voice_grant)
    
    # Return token as JSON
    return jsonify({"token": token.to_jwt().decode()})

@app.route('/voice', methods=['POST'])
def voice():
    # Get the phone number being called
    to_number = request.form.get('to')
    
    # Create TwiML response
    resp = VoiceResponse()
    resp.say("Connecting your call...")
    resp.dial(to_number, caller_id=TWILIO_NUMBER)
    
    return str(resp)

if __name__ == '__main__':
    app.run(debug=True, ssl_context='adhoc')