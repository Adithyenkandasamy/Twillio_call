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
import time,os
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
        self.FORMAT = pyaudio.paFloat32
        self.CHANNELS = 1
        self.RATE = 48000
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

    async def handle_websocket(self, websocket_url):
        """Handle WebSocket connection for real-time audio"""
        async with websockets.connect(websocket_url) as websocket:
            # Send audio thread
            async def send_audio():
                while self.is_active:
                    try:
                        data = self.input_stream.read(self.CHUNK)
                        await websocket.send(data)
                    except Exception as e:
                        print(f"Error sending audio: {e}")
                        break

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

    def make_call(self, to_number):
        """Initialize a two-way call"""
        try:
            self.is_active = True
            self.setup_audio()
            
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
                self.handle_websocket(websocket_url)
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
        # Make call
        recipient_number = '+916382841307'  # Replace with the number you want to call
        call_sid = voice_call.make_call(recipient_number)
        
        if call_sid:
            print(f"Call connected! Call SID: {call_sid}")
            print("Speaking through microphone and listening through speakers...")
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