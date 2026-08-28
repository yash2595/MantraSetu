"""TTS Cache Manager for caching pre-generated static audio prompts."""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.voice.tts.schemas import VoiceSynthesisRequest

logger = logging.getLogger(__name__)

# Directory where cached TTS mp3 files are stored
DEFAULT_CACHE_DIR = Path(__file__).parent / ".cache"


STATIC_ONBOARDING_PROMPTS = [
    # ── Onboarding Field Prompts ──
    "Namaste! Aap chahein to apni profile photo upload kar sakte hain, ye optional hai. Agar upload karna hai to 'Choose Picture' par click kijiye, nahi to bas 'skip' ya 'aage badho' boliye.",
    "Koi baat nahi Panditji. Ab apna pehla naam (First Name) bataiye.",
    "Bahut sundar photo! Maine aapki profile photo set kar di hai. Ab apna pehla naam (First Name) bataiye.",
    "Mujhe koi photo nahi mili, kya aapne 'Choose Picture' par click karke photo select ki hai? Ya phir 'skip' boliye.",
    "Ab apna pehla naam (First Name) bataiye.",
    "Ab apna upanaam ya last name bataiye.",
    "Ab apna email address bataiye.",
    "Ab apna 10-digit mobile number bataiye.",
    "Aapka gender kya hai? Purush, Mahila, ya Anya?",
    "Aap pooja kis maadhyam se karwana chahte hain? Offline, Online, ya Dono (Both)?",
    "Aap abhi kis sheher (City) mein rehte hain?",
    "Aap kis rajya (State) se hain?",
    "Aap kin service areas mein puja karwane ke liye uplabdh hain? Jaise Delhi NCR, Online Puja, ya Mumbai?",
    "Aapka kitne saalon ka experience ya anubhav hai?",
    "Kya aapne kisi Gurukul, Sansthan ya Veshveshwariya se shiksha li hai? Kripya bataiye.",
    "Aap kin bhashaon mein puja karwa sakte hain? Jaise Hindi, Sanskrit, English, Marathi?",
    "Aapki visheshtayein ya specializations kya hain? Jaise Vedic Puja, Vivah, Greh Pravesh, Havan?",
    "Kya aapki koi vishesh upalabdhi ya award hai? Agar hai to bataiye, nahi to 'nahi' ya 'skip' boliye.",
    "Kripya apni agli upalabdhi (achievement) batayein.",
    "Kripya apne baare mein thoda batayein (Bio), jaise aapki spiritual journey ya visheshta.",
    "Kripya apna Shastri / Acharya Degree certificate upload kijiye.",
    "Maine certificate dekh liya hai. Kripya apna Aadhaar Card document upload kijiye.",
    "Kripya apna Aadhaar Card document upload kijiye.",
    "Dhanyawad! Aadhaar card document attach ho gaya hai. Ab apni mandir ya puja ki 2-3 photo gallery mein upload kijiye.",
    "Ab apni mandir ya puja ki 2-3 photo gallery mein upload kijiye.",
    "Bahut sundar gallery photos! Ab apna 8-digit password set karein.",
    "Ab apna 8-digit password set karein.",
    "Kripya confirm password enter karein.",

    # ── Ceremonial Greetings & Clarifications ──
    "Namaste! MantraSetu mein aapka swagat hai. Aaj main aapki kya seva kar sakta hoon?",
    "Om Namah Shivaya! Swagat hai Panditji. Kya aapka pehle se MantraSetu par account hai? Kripya 'Haan' (login ke liye) ya 'Nahi' (naye registration ke liye) bataiye.",
    "Om Namah Shivaya! MantraSetu parivar mein aapka hardik swagat hai, Panditji. Aapki jaankari poori tarah surakshit rahegi aur sirf verification ke liye upyog hogi. Chaliye, ab hum aapka registration shuru karte hain. Namaste! Aap chahein to apni profile photo upload kar sakte hain, ye optional hai. Agar upload karna hai to 'Choose Picture' par click kijiye, nahi to bas 'skip' ya 'aage badho' boliye.",
    "Uttam Panditji! Main aapko login page par le jaa raha hoon. Kripya apne credentials se login kariye.",
    "Namaste! Kya aap ek Panditji hain ya ek devotee jo humari services dekhna chahte hain?",
    "Refresh karne se aapka current flow pause ho sakta hai. Kya aap sach mein page refresh karna chahte hain? Kripya 'Haan' ya 'Nahi' bataiye.",
    "Theek hai, main page refresh kar raha hoon.",
    "Theek hai Panditji, hum refresh nahi kar rahe. Wahi se continue karte hain.",
    "Theek hai, chaliye naye page par chalte hain.",
    "Theek hai, wahi se continue karte hain.",
    "Panditji, kya aapka pehle se MantraSetu par account hai? Kripya 'Haan' (login ke liye) ya 'Nahi' (naye registration ke liye) bataiye.",
    "Theek hai, main aapko le ja raha hoon.",

    # ── Error & Validation Messages ──
    "Maaf kijiye, main mobile number samajh nahi paya. Kripya 10-digit mobile number bataiye.",
    "Maaf kijiye, main email address samajh nahi paya. Kripya sahi email address bataiye.",
    "Kripya confirm password enter karke mujhe 'ho gaya' ya 'submit kar do' boliye.",
    "Password kam se kam 8 characters ka hona chahiye. Kripya naya password set karein.",
    "Panditji, aapne password galat daala hai, dono password match nahi ho rahe. Kripya dobara try karein.",
    "Kya saari jaankari sahi hai? Form submit karne ke liye 'Haan' ya 'Submit' boliye, ya kisi detail ko badalne ke liye field ka naam bataiye."
]


class TTSCacheManager:
    """Enterprise TTS cache manager supporting disk persistence and in-memory fast retrieval."""

    def __init__(self, cache_dir: Path | str | None = None) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: dict[str, bytes] = {}
        self._load_disk_cache()

    def get_cache_key(self, cleaned_text: str, voice: str, language: str, provider: str) -> str:
        """Compute SHA256 hash cache key from text, voice, language, and provider name."""
        content = f"{provider}:{voice}:{language}:{cleaned_text.strip()}"
        key = hashlib.sha256(content.encode("utf-8")).hexdigest()
        logger.debug("[CACHE-KEY-TRACE] key=%s | raw_string=%r", key[:8], content[:60])
        return key

    def _load_disk_cache(self) -> None:
        """Load pre-generated .mp3 files from disk into memory on startup."""
        count = 0
        try:
            for file_path in self.cache_dir.glob("*.mp3"):
                key = file_path.stem
                try:
                    data = file_path.read_bytes()
                    if data:
                        self._memory_cache[key] = data
                        count += 1
                except Exception as err:
                    logger.warning("Failed to read cached file %s: %s", file_path, err)
            logger.info("TTSCacheManager loaded %d cached audio prompts into memory.", count)
        except Exception as e:
            logger.error("Error loading disk cache: %s", e)

    def get(self, key: str) -> bytes | None:
        """Retrieve cached audio bytes by key from memory or disk."""
        if key in self._memory_cache:
            return self._memory_cache[key]
        
        file_path = self.cache_dir / f"{key}.mp3"
        if file_path.exists():
            try:
                data = file_path.read_bytes()
                if data:
                    self._memory_cache[key] = data
                    return data
            except Exception as e:
                logger.warning("Failed to read audio from disk cache key %s: %s", key, e)
        return None

    def put(self, key: str, data: bytes) -> None:
        """Store audio bytes into both in-memory cache and persistent disk file."""
        if not data or not key:
            return
        
        self._memory_cache[key] = data
        file_path = self.cache_dir / f"{key}.mp3"
        try:
            file_path.write_bytes(data)
            logger.debug("Saved TTS audio cache key %s (%d bytes) to disk.", key[:8], len(data))
        except Exception as e:
            logger.warning("Failed to write TTS cache file %s: %s", file_path, e)

    async def pregenerate_prompts(
        self,
        tts_provider: Any,
        prompts: list[str] | None = None,
        voice: str = "pandit",
        language: str = "hi",
    ) -> None:
        """Pre-generate TTS audio for all static onboarding prompts if missing from cache."""
        from app.voice.tts.voice_response_pipeline import clean_text_for_tts
        from app.voice.tts.schemas import VoiceSynthesisRequest, AudioEncoding
        import uuid

        target_prompts = prompts or STATIC_ONBOARDING_PROMPTS
        provider_name = tts_provider.provider_name
        cached_count = 0
        generated_count = 0
        t0 = time.time()

        for raw_text in target_prompts:
            cleaned_text = clean_text_for_tts(raw_text)
            key = self.get_cache_key(cleaned_text, voice, language, provider_name)
            
            if self.get(key) is not None:
                cached_count += 1
                continue

            # Synthesize audio chunk sequence and save to cache
            req = VoiceSynthesisRequest(
                request_id=uuid.uuid4(),
                session_id="pregen_sess",
                conversation_id=uuid.uuid4(),
                text=cleaned_text,
                language=language,
                voice=voice,
                encoding=AudioEncoding.MP3,
            )

            audio_data = b""
            try:
                import asyncio
                async with asyncio.timeout(10.0):
                    async for chunk in tts_provider.stream(req):
                        if chunk.data:
                            audio_data += chunk.data
                
                if audio_data:
                    self.put(key, audio_data)
                    generated_count += 1
            except Exception as e:
                logger.warning("Failed to pre-generate audio for prompt %r: %s", cleaned_text[:30], e)

        elapsed_ms = int((time.time() - t0) * 1000)
        logger.info(
            "TTSCacheManager pre-generation complete in %dms | Already Cached: %d | Newly Generated: %d",
            elapsed_ms,
            cached_count,
            generated_count,
        )


# Singleton instance
_tts_cache_manager_instance = TTSCacheManager()


def get_tts_cache_manager() -> TTSCacheManager:
    """Dependency provider returning singleton TTSCacheManager instance."""
    return _tts_cache_manager_instance
