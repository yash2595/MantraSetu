import os
import io
import difflib
from gtts import gTTS
from pydub import AudioSegment
import speech_recognition as sr

def calculate_accuracy(original, transcript):
    if not transcript:
        return 0.0
    
    # Calculate word-level accuracy
    orig_words = original.lower().split()
    trans_words = transcript.lower().split()
    
    matcher = difflib.SequenceMatcher(None, orig_words, trans_words)
    return matcher.ratio() * 100

def test_phrase(phrase_latin, phrase_devanagari):
    print(f"\n--- Testing Phrase ---")
    print(f"Latin: '{phrase_latin}'")
    try:
        # 1. Generate audio using gTTS (Hindi)
        # Using devanagari for better TTS pronunciation
        tts = gTTS(text=phrase_devanagari, lang='hi', slow=False)
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)

        # 2. Convert to WAV using pydub
        audio = AudioSegment.from_file(mp3_fp, format="mp3")
        wav_fp = io.BytesIO()
        audio.export(wav_fp, format="wav")
        wav_fp.seek(0)

        # 3. Send to Google Web Speech API using SpeechRecognition
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_fp) as source:
            audio_data = recognizer.record(source)

        print("Sending to Google STT (language='hi-IN')...")
        transcript = recognizer.recognize_google(audio_data, language="hi-IN")
        
        # 4. Compare using devanagari to devanagari for actual accuracy
        accuracy = calculate_accuracy(phrase_devanagari, transcript)
        
        print(f"Original Text (Devanagari): {phrase_devanagari}")
        print(f"Actual STT Transcript     : {transcript}")
        print(f"Word-by-word Accuracy     : {accuracy:.2f}%")
        
        return True, transcript, accuracy
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
        return False, None, 0.0
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        return False, None, 0.0
    except Exception as e:
        print(f"Error testing phrase '{phrase_latin}': {e}")
        return False, None, 0.0

def main():
    phrases = [
        ("Mera education Gurukul se hua hai", "मेरा एजुकेशन गुरुकुल से हुआ है"),
        ("Sanskrit padhani aati hai", "संस्कृत पढ़नी आती है"),
        ("Das saal ka anubhav hai", "दस साल का अनुभव है")
    ]

    for i, (latin, devanagari) in enumerate(phrases):
        success, transcript, accuracy = test_phrase(latin, devanagari)
        if i == 0 and not success:
            print("\nFirst test failed. Aborting remaining tests.")
            break

if __name__ == "__main__":
    main()
