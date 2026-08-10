from app.voice.tts.voice_response_pipeline import clean_text_for_tts

def test_emoji_cleaning():
    sample_text = "Om Namah Shivaya! 🙏 MantraSetu parivar mein aapka hardik swagat hai 🚀✨"
    cleaned = clean_text_for_tts(sample_text)
    print(f"Original: {sample_text!r}")
    print(f"Cleaned : {cleaned!r}")
    assert "🙏" not in cleaned
    assert "🚀" not in cleaned
    assert "✨" not in cleaned
    assert cleaned == "Om Namah Shivaya! MantraSetu parivar mein aapka hardik swagat hai"
    print(">>> SUCCESS: Emoji cleaning test passed! <<<")

if __name__ == "__main__":
    test_emoji_cleaning()
