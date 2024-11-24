from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect
from dotenv import load_dotenv
import pyaudio
import wave
import threading
import websockets
import asyncio
import json
import sys
import time
import os
from gtts import gTTS

load_dotenv()

class TwilioVoiceCall:
    def __init__(self):
        # Twilio credentials
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_number = os.getenv('TWILIO_NUMBER')
        self.client = Client(self.account_sid, self.auth_token)
        
        # Audio settings
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.p = pyaudio.PyAudio()
        
        # Streams
        self.input_stream = None
        self.output_stream = None
        self.is_active = False

    def setup_audio(self):
        """Setup audio input and output streams"""
        # Input stream (microphone)
        self.input_stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        
        # Output stream (speakers)
        self.output_stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            output=True,
            frames_per_buffer=self.CHUNK
        )

    def text_to_speech(self, text, output_file="message.wav"):
        """Convert text to speech and save to a file"""
        try:
            tts = gTTS(text=text, lang='en')
            tts.save(output_file)
            print(f"Text-to-speech conversion complete. Saved to {output_file}")
        except Exception as e:
            print(f"Error converting text to speech: {e}")
            return None
        return output_file

    async def handle_websocket(self, websocket_url, speech_file):
        """Handle WebSocket connection for real-time audio"""
        async with websockets.connect(websocket_url) as websocket:
            # Send audio thread
            async def send_audio():
                if speech_file:
                    # Read the audio file and send its content
                    with wave.open(speech_file, 'rb') as wf:
                        data = wf.readframes(self.CHUNK)
                        while data:
                            await websocket.send(data)
                            data = wf.readframes(self.CHUNK)

            # Receive audio thread
            async def receive_audio():
                while self.is_active:
                    try:
                        data = await websocket.recv()
                        self.output_stream.write(data)
                    except Exception as e:
                        print(f"Error receiving audio: {e}")
                        break

            # Run both send and receive
            await asyncio.gather(send_audio(), receive_audio())

    def make_call(self, to_number, message):
        """Initialize a two-way call"""
        try:
            self.is_active = True
            self.setup_audio()
            
            # Convert message to speech
            speech_file = self.text_to_speech(message)
            if not speech_file:
                raise ValueError("Failed to generate speech file.")
            
            # Create TwiML for two-way audio
            response = VoiceResponse()
            connect = Connect()
            connect.stream(url=f'wss://your-websocket-server.com/voice')
            response.append(connect)
            
            # Make the call
            call = self.client.calls.create(
                twiml=str(response),
                to=to_number,
                from_=self.twilio_number
            )
            
            # Start WebSocket connection
            websocket_url = f'wss://your-websocket-server.com/voice/{call.sid}'
            asyncio.get_event_loop().run_until_complete(
                self.handle_websocket(websocket_url, speech_file)
            )
            
            return call.sid
            
        except Exception as e:
            print(f"Error making call: {e}")
            self.cleanup()
            return None

    def cleanup(self):
        """Clean up resources"""
        self.is_active = False
        
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
            
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
            
        if self.p:
            self.p.terminate()

def main():
    # Create instance
    voice_call = TwilioVoiceCall()
    
    try:
        # Input the message to be spoken
        message = input("Enter the message to speak during the call: ")
        
        # Make call
        recipient_number = '+916382841307'  # Replace with the number you want to call
        call_sid = voice_call.make_call(recipient_number, message)
        
        if call_sid:
            print(f"Call connected! Call SID: {call_sid}")
            print("Speaking the provided message...")
            print("Press Ctrl+C to end the call")
            
            # Keep the call running until user interrupts
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\nEnding call...")
    finally:
        voice_call.cleanup()

if __name__ == "__main__":
    main()
