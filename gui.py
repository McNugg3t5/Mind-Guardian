import tkinter as tk
from tkinter import ttk
import threading
import queue
import os
from tkinter import filedialog

# Imports needed for audio recording
import pyaudio
import wave
import time # Import time for potential delays

# Import for speech recognition (requires local installation: pip install SpeechRecognition)
try:
    import speech_recognition as sr
    print("SpeechRecognition imported successfully.")
except ImportError:
    sr = None
    print("SpeechRecognition not found. Audio transcription functionality will not work.")


# Import the backend logic
from backend import MindGuardian

# Define audio recording parameters (adjust as needed)
FORMAT = pyaudio.paInt16  # 16-bit resolution
CHANNELS = 1              # 1 channel (mono)
RATE = 44100              # 44.1kHz sampling rate
CHUNK = 1024              # 1024 samples per chunk
RECORD_SECONDS = 5        # Duration of recording (can be adjusted)
WAVE_OUTPUT_FILENAME = "temp_recording.wav" # Temporary file to save recording


class MindGuardianGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mind Guardian")
        self.geometry("600x500")

        style = ttk.Style(self)
        style.theme_use('clam')

        self.guardian = None # Initialize guardian to None
        self.result_queue = queue.Queue()

        self.status_label = tk.Label(self, text="Loading AI model, please wait...", fg="blue")
        self.status_label.pack(pady=10)

        self.setup_gui_structure()
        self.disable_analysis_buttons()

        backend_thread = threading.Thread(target=self.initialize_backend)
        backend_thread.start()

        self.check_queue()

        # Audio recording attributes
        self._is_recording = False
        self._frames = []
        self._audio = None # PyAudio instance
        self._stream = None # PyAudio stream
        self._recording_thread = None
        self._last_recorded_audio_path = None # Store the path to the last recording
        # Removed _playback_obj attribute

        # Moment Analysis attributes
        self.loaded_image_path = None

        # Speech Recognition recognizer instance
        self._recognizer = sr.Recognizer() if sr else None
        if not self._recognizer:
             print("Speech recognition is disabled due to missing library.")

        # Initialize PyAudio instance here
        try:
            self._audio = pyaudio.PyAudio()
            print("PyAudio initialized successfully.")
        except Exception as e:
            print(f"❌ PyAudio Initialization Error: {e}. Audio recording/playback will be disabled.")
            self._audio = None # Ensure it's None if initialization fails


    def initialize_backend(self):
        """Initializes the MindGuardian backend in a separate thread."""
        try:
            self.guardian = MindGuardian()
            if not self.guardian or not self.guardian.model:
                 error_message = "Failed to load the local AI model. Analysis features are disabled."
                 print(f"❌ Critical Error: {error_message}")
                 self.after(0, self.update_status_and_buttons, error_message, False)
            else:
                 print("DEBUG: MindGuardian backend initialized successfully.")
                 self.after(0, self.update_status_and_buttons, "AI model loaded. Ready for analysis.", True)
        except Exception as e:
            error_message = f"Failed to initialize MindGuardian backend: {e}"
            print(f"❌ Critical Error: {error_message}")
            self.after(0, self.update_status_and_buttons, error_message, False)

    def update_status_and_buttons(self, message, enable_buttons):
        """Updates the status label and button states from the main GUI thread."""
        self.status_label.config(text=message, fg="green" if enable_buttons else "red")
        if enable_buttons:
            self.enable_analysis_buttons()
        else:
            self.disable_analysis_buttons()


    def setup_gui_structure(self):
        """Creates the notebook and tab frames."""
        notebook = ttk.Notebook(self)
        notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # --- Journal Analysis Tab ---
        journal_frame = ttk.Frame(notebook, padding="10")
        notebook.add(journal_frame, text="Journal Analysis")
        self.create_journal_tab(journal_frame)

        # --- Voice Note Analysis Tab ---
        voice_frame = ttk.Frame(notebook, padding="10")
        notebook.add(voice_frame, text="Voice Note Analysis")
        self.create_voice_tab(voice_frame)

        # --- Moment Analysis Tab ---
        moment_frame = ttk.Frame(notebook, padding="10")
        notebook.add(moment_frame, text="Moment Analysis")
        self.create_moment_tab(moment_frame)


    def create_journal_tab(self, parent_frame):
        """Adds widgets to the Journal Analysis tab."""
        tk.Label(parent_frame, text="Enter your journal entry:").pack(pady=(0, 5), anchor='w')
        self.journal_text_input = tk.Text(parent_frame, height=10, width=50, wrap="word")
        self.journal_text_input.pack(expand=True, fill="both", pady=(0, 10))
        self.analyze_journal_button = ttk.Button(parent_frame, text="Analyze Journal", command=self.analyze_journal_click)
        self.analyze_journal_button.pack(pady=(0, 10))
        tk.Label(parent_frame, text="Analysis Result:").pack(pady=(0, 5), anchor='w')
        self.journal_result_output = tk.Text(parent_frame, height=10, width=50, state='disabled', wrap="word")
        self.journal_result_output.pack(expand=True, fill="both", pady=(0, 10))

    def create_voice_tab(self, parent_frame):
        """Adds widgets to the Voice Note Analysis tab, focusing on recording and playback."""
        tk.Label(parent_frame, text="Record voice note:").pack(pady=(0, 5), anchor='w')

        record_button_frame = ttk.Frame(parent_frame)
        record_button_frame.pack(pady=(0, 5), anchor='w')

        self.record_button = ttk.Button(record_button_frame, text="Record", command=self.start_recording)
        self.record_button.pack(side=tk.LEFT, padx=(0, 5))

        self.stop_button = ttk.Button(record_button_frame, text="Stop", command=self.stop_recording, state='disabled')
        self.stop_button.pack(side=tk.LEFT)

        # Removed audio playback button/representation
        # tk.Label(parent_frame, text="Recorded Audio:").pack(pady=(10, 5), anchor='w')
        # self.audio_playback_button = ttk.Button(parent_frame, text="No audio recorded yet.", command=self.play_last_recording, state='disabled')
        # self.audio_playback_button.pack(pady=(0, 10), anchor='w')

        self.analyze_voice_button = ttk.Button(parent_frame, text="Analyze Voice Note", command=self.analyze_voice_click)
        self.analyze_voice_button.pack(pady=(0, 10))

        tk.Label(parent_frame, text="Analysis Result:").pack(pady=(0, 5), anchor='w')
        self.voice_result_output = tk.Text(parent_frame, height=10, width=50, state='disabled', wrap="word")
        self.voice_result_output.pack(expand=True, fill="both", pady=(0, 10))

    def create_moment_tab(self, parent_frame):
        """Adds widgets to the Moment Analysis tab, including image upload."""
        tk.Label(parent_frame, text="Describe the moment:").pack(pady=(0, 5), anchor='w')

        image_upload_frame = ttk.Frame(parent_frame)
        image_upload_frame.pack(pady=(0, 5), anchor='w')

        self.upload_image_button = ttk.Button(image_upload_frame, text="Carregar Imagem", command=self.upload_image)
        self.upload_image_button.pack(side=tk.LEFT, padx=(0, 5))

        self.image_status_label = tk.Label(image_upload_frame, text="Nenhuma imagem carregada.", fg="gray")
        self.image_status_label.pack(side=tk.LEFT)

        self.moment_text_input = tk.Text(parent_frame, height=10, width=50, wrap="word")
        self.moment_text_input.pack(expand=True, fill="both", pady=(0, 10))

        self.analyze_moment_button = ttk.Button(parent_frame, text="Analyze Moment", command=self.analyze_moment_click)
        self.analyze_moment_button.pack(pady=(0, 10))

        tk.Label(parent_frame, text="Analysis Result:").pack(pady=(0, 5), anchor='w')
        self.moment_result_output = tk.Text(parent_frame, height=10, width=50, state='disabled', wrap="word")
        self.moment_result_output.pack(expand=True, fill="both", pady=(0, 10))

    def disable_analysis_buttons(self):
        """Disables the analysis buttons."""
        if hasattr(self, 'analyze_journal_button'):
            self.analyze_journal_button.config(state='disabled')
        if hasattr(self, 'analyze_voice_button'):
            self.analyze_voice_button.config(state='disabled')
        if hasattr(self, 'analyze_moment_button'):
            self.analyze_moment_button.config(state='disabled')
        if hasattr(self, 'record_button'):
             self.record_button.config(state='disabled')
        if hasattr(self, 'stop_button'):
             self.stop_button.config(state='disabled')
        if hasattr(self, 'upload_image_button'):
             self.upload_image_button.config(state='disabled')
        # Removed audio_playback_button


    def enable_analysis_buttons(self):
        """Enables the analysis buttons."""
        if self.guardian and self.guardian.model:
            if hasattr(self, 'analyze_journal_button'):
                self.analyze_journal_button.config(state='normal')
            if hasattr(self, 'analyze_voice_button'):
                self.analyze_voice_button.config(state='normal')
            if hasattr(self, 'analyze_moment_button'):
                self.analyze_moment_button.config(state='normal')
            if hasattr(self, 'record_button'):
                 self.record_button.config(state='normal')
            if hasattr(self, 'upload_image_button'):
                 self.upload_image_button.config(state='normal')
            # Removed audio_playback_button check and enable


        else:
            self.disable_analysis_buttons()


    def analyze_journal_click(self):
        if not self.guardian or not self.guardian.model:
            print("Analysis not available: MindGuardian or model not initialized.")
            self.update_output(self.journal_result_output, "Error: AI model not loaded.", self.analyze_journal_button)
            return

        text = self.journal_text_input.get("1.0", tk.END).strip()
        if text:
            self.analyze_journal_button.config(state='disabled', text="Analyzing...")
            self.update_output(self.journal_result_output, "Analyzing...", None)
            thread = threading.Thread(target=self.run_analysis, args=(self.guardian.analyze_journal, text, self.journal_result_output, self.analyze_journal_button))
            thread.start()
        else:
            self.update_output(self.journal_result_output, "Please enter text to analyze.", self.analyze_journal_button)


    def analyze_voice_click(self):
        if not self.guardian or not self.guardian.model:
            print("Analysis not available: MindGuardian or model not initialized.")
            self.update_output(self.voice_result_output, "Error: AI model not loaded.", self.analyze_voice_button)
            return

        # Ensure simpleaudio and speech_recognition are available for voice analysis
        # Removed simpleaudio check as playback is removed
        if not sr:
            error_message = "Voice analysis requires SpeechRecognition library."
            print(f"❌ Voice Analysis Error: {error_message}")
            self.update_output(self.voice_result_output, error_message, self.analyze_voice_button)
            return


        if self._last_recorded_audio_path and os.path.exists(self._last_recorded_audio_path):
             # Perform transcription in a separate thread to avoid blocking the GUI
             self.analyze_voice_button.config(state='disabled', text="Transcribing...")
             self.update_output(self.voice_result_output, "Transcribing audio...", None)
             transcription_thread = threading.Thread(target=self._transcribe_and_analyze_voice)
             transcription_thread.start()

        else:
             text_to_analyze = "No audio recorded. Please record a voice note first."
             print("No audio recorded for voice analysis.")
             self.update_output(self.voice_result_output, text_to_analyze, self.analyze_voice_button)
             return


    def _transcribe_and_analyze_voice(self):
        """Transcribes the audio and then triggers analysis (runs in a separate thread)."""
        if not self._last_recorded_audio_path or not os.path.exists(self._last_recorded_audio_path):
             self.result_queue.put((self.voice_result_output, "Error: No audio file found for transcription.", self.analyze_voice_button))
             return

        if not self._recognizer:
             self.result_queue.put((self.voice_result_output, "Error: Speech recognition library not loaded.", self.analyze_voice_button))
             return

        text_to_analyze = self.transcribe_audio(self._last_recorded_audio_path)
        print(f"DEBUG: Transcribed text: {text_to_analyze[:100]}...")

        if text_to_analyze and not text_to_analyze.startswith("Transcription failed:"):
            # Now run the analysis
            self.result_queue.put((self.voice_result_output, "Analyzing transcribed text...", None)) # Update status in GUI
            self.run_analysis(self.guardian.analyze_audio_transcript, text_to_analyze, self.voice_result_output, self.analyze_voice_button)
        elif text_to_analyze: # It started with "Transcription failed:"
             self.result_queue.put((self.voice_result_output, text_to_analyze, self.analyze_voice_button)) # Show the error message
        else:
             self.result_queue.put((self.voice_result_output, "Could not obtain transcript for analysis.", self.analyze_voice_button)) # Show a general error


    def analyze_moment_click(self):
        if not self.guardian or not self.guardian.model:
            print("Analysis not available: MindGuardian or model not initialized.")
            self.update_output(self.moment_result_output, "Error: AI model not loaded.", self.analyze_moment_button)
            return

        text = self.moment_text_input.get("1.0", tk.END).strip()
        if text:
            self.analyze_moment_button.config(state='disabled', text="Analyzing...")
            self.update_output(self.moment_result_output, "Analyzing...", None)
            thread = threading.Thread(target=self.run_analysis, args=(self.guardian.analyze_moment, text, self.moment_result_output, self.analyze_moment_button))
            thread.start()
        else:
            self.update_output(self.moment_result_output, "Please enter text to analyze.", self.analyze_moment_button)

    def run_analysis(self, analysis_func, text, output_widget, button):
        """Runs the analysis and puts the result in a queue."""
        try:
            result = analysis_func(text)
            self.result_queue.put((output_widget, result, button))
        except Exception as e:
             self.result_queue.put((output_widget, f"An error occurred during analysis: {e}", button))


    def check_queue(self):
        """Checks the queue for results and updates the GUI."""
        try:
            while True:
                output_widget, result, button = self.result_queue.get_nowait()
                self.update_output(output_widget, result, button)
        except queue.Empty:
            pass
        finally:
            self.after(100, self.check_queue)


    def update_output(self, output_widget, result, button):
        """Helper to update the text widget and re-enable the button."""
        output_widget.config(state='normal')
        output_widget.delete("1.0", tk.END)
        output_widget.insert(tk.END, result)
        output_widget.config(state='disabled')
        if button:
            current_text = button.cget('text')
            if "Analyzing..." in current_text:
                 original_text = current_text.replace("Analyzing...", "Analyze")
                 button.config(state='normal', text=original_text.strip())
            elif "Transcribing..." in current_text:
                 # If it was transcribing, restore to "Analyze Voice Note"
                 button.config(state='normal', text="Analyze Voice Note")
            else:
                 button.config(state='normal')


    def start_recording(self):
        """Starts recording audio from the microphone."""
        print("Start recording button clicked.")
        # Check if PyAudio was initialized successfully
        if not self._audio:
            error_message = "Audio recording is not available. PyAudio failed to initialize."
            print(f"❌ Recording Error: {error_message}")
            self.update_output(self.voice_result_output, error_message, self.record_button)
            # Removed audio_playback_button update
            return

        if not self.guardian or not self.guardian.model:
            print("Recording not available: AI model not initialized.")
            self.update_output(self.voice_result_output, "Error: AI model not loaded, cannot record.", self.record_button)
            # Removed audio_playback_button update
            return

        try:
            # Removed check and stop for previous playback

            self._stream = self._audio.open(format=FORMAT,
                                            channels=CHANNELS,
                                            rate=RATE,
                                            input=True,
                                            frames_per_buffer=CHUNK)
            self._is_recording = True
            self._frames = []
            self._last_recorded_audio_path = None

            self.record_button.config(state='disabled')
            self.stop_button.config(state='normal')
            # Removed audio_playback_button update
            self.update_output(self.voice_result_output, "Recording...", None)

            self._recording_thread = threading.Thread(target=self._record_audio_stream)
            self._recording_thread.start()

        except Exception as e:
            error_message = f"Failed to start recording: {e}. Make sure microphone is available."
            print(f"❌ Recording Error: {error_message}")
            self._is_recording = False
            self.update_output(self.voice_result_output, error_message, self.record_button)
            # Removed audio_playback_button update
            self.record_button.config(state='normal')
            self.stop_button.config(state='disabled')
            # Clean up stream and audio if they were partially initialized
            if self._stream:
                try:
                    self._stream.stop_stream()
                    self._stream.close()
                except:
                    pass # Ignore errors during cleanup
                self._stream = None
            # Note: We don't terminate self._audio here as it's initialized once


    def _record_audio_stream(self):
        """Reads audio data from the stream in a separate thread."""
        print("Recording thread started.")
        try:
            # Read from stream until recording stops
            while self._is_recording and self._stream:
                 try:
                     data = self._stream.read(CHUNK)
                     self._frames.append(data)
                 except IOError as e:
                     # Handle potential input overflow or other stream errors
                     print(f"❌ IOError during recording stream: {e}")
                     # Attempt to gracefully stop recording
                     self._is_recording = False
                     # Put error message in queue to update GUI from main thread
                     self.result_queue.put((self.voice_result_output, f"Recording stream error: {e}", self.record_button))
                     # Removed audio_playback_button update
                     break # Exit loop on error

        except Exception as e:
             print(f"❌ Error during recording stream: {e}")
             # Put error message in queue to update GUI from main thread
             self.result_queue.put((self.voice_result_output, f"Recording stream error: {e}", self.record_button))
             # Removed audio_playback_button update
        finally:
             print("Recording thread finished.")


    def stop_recording(self):
        """Stops recording and saves the audio to a file."""
        print("Stop recording button clicked.")
        if not self._is_recording:
            print("Not currently recording.")
            # Ensure buttons are in correct state if stop is clicked when not recording
            self.after(0, self.record_button.config, {'state': 'normal'})
            self.after(0, self.stop_button.config, {'state': 'disabled'})
            return

        self._is_recording = False # Signal the recording thread to stop

        # Wait briefly for the recording thread to finish processing the last chunk
        # This is a simple approach; a more robust method would involve event flags or queues
        if self._recording_thread and self._recording_thread.is_alive():
             self._recording_thread.join(timeout=1.0) # Wait for up to 1 second


        try:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None # Explicitly set to None after closing

            # Note: self._audio is NOT terminated here, it's kept for potential future recordings

            # Save the recorded data to a WAV file
            if self._frames:
                print(f"DEBUG: Saving audio to {WAVE_OUTPUT_FILENAME}")
                wf = None # Initialize wf to None
                try:
                    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
                    wf.setnchannels(CHANNELS)
                    # Use the sample width from the stream if available, otherwise default
                    sampwidth = self._audio.get_sample_size(FORMAT) if self._audio else 2
                    wf.setsampwidth(sampwidth)
                    wf.setframerate(RATE)
                    wf.writeframes(b''.join(self._frames))
                    print(f"Audio saved to {WAVE_OUTPUT_FILENAME}")
                    self._last_recorded_audio_path = WAVE_OUTPUT_FILENAME # Store the path

                    # Clear frames after saving
                    self._frames = []

                    # Update GUI (from main thread)
                    self.result_queue.put((self.voice_result_output, f"Recording stopped. Audio saved to {WAVE_OUTPUT_FILENAME}.\nReady to analyze.", self.record_button))
                    # Removed playback button update

                except Exception as e:
                    error_message = f"Failed to save audio file: {e}"
                    print(f"❌ File Save Error: {error_message}")
                    self.result_queue.put((self.voice_result_output, error_message, self.record_button))
                    self._last_recorded_audio_path = None # Error saving
                    # Removed playback button update
                finally:
                     if wf:
                         wf.close() # Ensure the wave file is closed


            else:
                print("No audio frames recorded.")
                self.result_queue.put((self.voice_result_output, "Recording stopped. No audio captured.", self.record_button))
                self._last_recorded_audio_path = None # No audio recorded
                # Removed playback button update


        except Exception as e:
            error_message = f"An unexpected error occurred during stop recording: {e}"
            print(f"❌ Stop Recording Error: {error_message}")
            self.result_queue.put((self.voice_result_output, error_message, self.record_button))
            self._last_recorded_audio_path = None # Error during stop process
            # Removed playback button update


        finally:
            # Ensure buttons are in correct state
            self.after(0, self.record_button.config, {'state': 'normal'})
            self.after(0, self.stop_button.config, {'state': 'disabled'})
            # Ensure PyAudio resources are released when the app closes
            # This should be handled in a separate cleanup method or __del__
            # if self._audio:
            #     self._audio.terminate()
            #     self._audio = None


    # Removed play_last_recording method
    # Removed _play_audio_thread method


    def transcribe_audio(self, audio_filepath):
        """Transcribes audio from a given file path."""
        print(f"Transcribing audio from {audio_filepath}")
        if not self._recognizer:
            return "Transcription failed: Speech recognition library not loaded."

        try:
            with sr.AudioFile(audio_filepath) as source:
                # Adjust for ambient noise and record the audio
                self._recognizer.adjust_for_ambient_noise(source, duration=5) # Optional: adjust noise for 5 seconds
                print("Adjusting for ambient noise...")
                audio_data = self._recognizer.record(source)

                # Use Google Web Speech API for transcription
                print("Recognizing speech...")
                text = self._recognizer.recognize_google(audio_data, language='pt-BR') # Using Portuguese for transcription
                print(f"Recognition complete: {text[:100]}...")
                return text
        except sr.UnknownValueError:
            return "Transcription failed: Could not understand audio."
        except sr.RequestError as e:
            return f"Transcription failed: Could not request results from Google Speech Recognition service; {e}"
        except FileNotFoundError:
             return f"Transcription failed: Audio file not found at {audio_filepath}"
        except Exception as e:
            return f"Transcription failed: An unexpected error occurred; {e}"


    def upload_image(self):
        """Handles image upload via file dialog."""
        print("Upload Image button clicked.")
        if not self.guardian or not self.guardian.model:
            print("Image upload not available: AI model not initialized.")
            self.image_status_label.config(text="Error: AI model not loaded.", fg="red")
            return

        try:
            filepath = filedialog.askopenfilename(
                title="Select an Image",
                filetypes=(("Image files", "*.jpg *.jpeg *.png *.gif"), ("All files", "*.*"))
            )
            if filepath:
                self.loaded_image_path = filepath
                print(f"Image selected: {filepath}")
                self.image_status_label.config(text=f"Imagem carregada: {os.path.basename(filepath)}", fg="green")
            else:
                self.loaded_image_path = None
                self.image_status_label.config(text="Nenhuma imagem carregada.", fg="gray")
                print("No file selected.")

        except Exception as e:
            error_message = f"Failed to upload image: {e}"
            print(f"❌ Image Upload Error: {error_message}")
            self.image_status_label.config(text=f"Erro ao carregar imagem: {e}", fg="red")

    def on_closing(self):
        """Handles cleanup when the GUI window is closed."""
        print("Closing application...")
        # Stop any ongoing recording
        if self._is_recording:
            self.stop_recording() # This will attempt to stop the stream and save the file

        # Removed stop any ongoing playback

        # Terminate PyAudio instance
        if self._audio:
            try:
                self._audio.terminate()
                print("PyAudio terminated.")
            except Exception as e:
                 print(f"Error terminating PyAudio: {e}")

        # Destroy the GUI window
        self.destroy()


# Add the protocol for handling window closing
# To run the application (this will fail in Colab/non-GUI environments)
if __name__ == "__main__":
    try:
        app = MindGuardianGUI()
        # Bind the closing protocol to the on_closing method
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop()
    except tk.TclError as e:
        print(f"Failed to start GUI. This is expected in a non-GUI environment. Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during GUI execution: {e}")