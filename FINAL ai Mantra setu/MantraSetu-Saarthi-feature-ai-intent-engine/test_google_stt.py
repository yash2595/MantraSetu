import os
import speech_recognition as sr
from pydub import AudioSegment
from gtts import gTTS

def test_google_stt():
    print("--- Running Google Web Speech STT Accuracy Test ---")
    
    # 1. Generate Real Hindi Speech using gTTS
    original_text = "Mera education Gurukul se hua hai"
    mp3_file = "test_speech.mp3"
    wav_file = "test_speech.wav"
    
    print(f"Original Text: '{original_text}'")
    print("Generating speech via gTTS...")
    tts = gTTS(text=original_text, lang='hi')
    tts.save(mp3_file)
    
    # 2. Convert MP3 to WAV using pydub
    print("Converting MP3 to WAV...")
    audio = AudioSegment.from_mp3(mp3_file)
    audio.export(wav_file, format="wav")
    
    # 3. Call Google Web Speech API
    recognizer = sr.Recognizer()
    print("Sending WAV to Google Web Speech API for recognition...")
    try:
        with sr.AudioFile(wav_file) as source:
            audio_data = recognizer.record(source)
            
        actual_transcript = recognizer.recognize_google(audio_data, language="hi-IN")
        
        print("\n--- RESULTS ---")
        print(f"Original Text   : {original_text}")
        print(f"STT Transcript  : {actual_transcript}")
        
        # Simple match comparison
        if original_text.lower() == actual_transcript.lower():
            print("Accuracy        : 100% Exact Match")
        else:
            print("Accuracy        : Partial Match / Differences Found")
            
    except sr.UnknownValueError:
        print("Result: FAIL (Google Web Speech could not understand audio)")
    except sr.RequestError as e:
        print(f"Result: FAIL (Could not request results from Google Web Speech service; {e})")
    except Exception as e:
        print(f"Result: FAIL (Unexpected error: {e})")
        
    # Cleanup
    if os.path.exists(mp3_file):
        os.remove(mp3_file)
    if os.path.exists(wav_file):
        os.remove(wav_file)

if __name__ == "__main__":
    test_google_stt()
