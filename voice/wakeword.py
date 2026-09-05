# Jarvis AI — Wake Word Detection
# Uses openwakeword for offline, local, continuous background listening.

import threading
import time
import pyaudio
import numpy as np
from openwakeword.model import Model

class WakeWordDetector:
    def __init__(self, callback):
        """
        Initialize the wake word detector.
        Args:
            callback: Function to call when the wake word is detected.
        """
        self.callback = callback
        self.is_running = False
        self._thread = None
        self.is_paused = False
        
        # We use the pre-trained "hey jarvis" model included in openwakeword
        self.oww_model = Model(wakeword_models=["hey_jarvis"], inference_framework="tflite")

    def start(self):
        """Start the background wake word detection thread."""
        if self.is_running:
            return
            
        self.is_running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the background thread."""
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            
    def pause(self):
        """Pause listening (e.g., when Jarvis is already speaking or listening for a command)."""
        self.is_paused = True
        
    def resume(self):
        """Resume listening."""
        self.oww_model.reset()
        self.is_paused = False

    def _listen_loop(self):
        """Main audio capture and detection loop."""
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        CHUNK = 1280
        
        audio = pyaudio.PyAudio()
        
        try:
            mic_stream = audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
            )
        except Exception as e:
            print(f"⚠️  Wake Word Error: Could not open microphone - {e}")
            self.is_running = False
            return

        while self.is_running:
            try:
                # Read audio from microphone
                data = mic_stream.read(CHUNK, exception_on_overflow=False)
                
                if self.is_paused:
                    continue
                    
                # Convert to numpy array for openwakeword
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                # Predict wake word
                prediction = self.oww_model.predict(audio_data)
                
                # Check the score for 'hey_jarvis'
                for mdl, score in prediction.items():
                    if score > 0.3:  # Lowered threshold for better sensitivity (was 0.5)
                        # We heard it!
                        
                        # Reset the model state so it doesn't immediately trigger again
                        self.oww_model.reset()
                        
                        # Pause our own listening while the main app handles the voice command
                        self.pause()
                        
                        # Call the callback function
                        self.callback()
                        break
                        
            except Exception as e:
                print(f"⚠️  Wake Word Error: {e}")
                time.sleep(1.0)

        # Cleanup
        mic_stream.stop_stream()
        mic_stream.close()
        audio.terminate()
