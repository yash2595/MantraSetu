import asyncio
import logging
import random
import re
import time
from typing import Any, Callable
from app.llm.models import LLMRequest
from app.services.ai_service import AIService
from app.orchestrator.orchestrator_models import (
    OrchestratorRequest,
    OrchestratorResponse,
    ResponseMetadata,
    ResponseType,
)

logger = logging.getLogger(__name__)

def get_address_forms(full_name: str) -> dict:
    """Extract natural forms of address: First Name ji, Surname ji, and Panditji."""
    parts = [p for p in full_name.strip().split() if p]
    first_name = parts[0] if parts else "Panditji"
    surname = parts[-1] if len(parts) > 1 else ""
    
    first_name_ji = f"{first_name} ji"
    surname_ji = f"{surname} ji" if surname else first_name_ji
    
    return {
        "first_name": first_name,
        "surname": surname,
        "first_name_ji": first_name_ji,
        "surname_ji": surname_ji,
        "panditji": "Panditji"
    }

def get_contextual_reaction(current_field: str, val: str, address_info: dict) -> str:
    """Generate a warm, contextual reaction prefix using varied forms of address & specialization respect lines."""
    val_lower = val.lower().strip()
    fn_ji = address_info.get("first_name_ji", "Panditji")
    sn_ji = address_info.get("surname_ji", fn_ji)
    pji = address_info.get("panditji", "Panditji")
    
    if current_field == "pandit-city":
        spiritual_cities = [
            "varanasi", "kashi", "haridwar", "ujjain", "rishikesh", "mathura", 
            "ayodhya", "vrindavan", "puri", "rameshwaram", "kedarnath", "badrinath", 
            "gaya", "tirupati", "nashik", "dwarka", "prayagraj", "allahabad"
        ]
        if any(sc in val_lower for sc in spiritual_cities):
            return f"Wah, {val} se! Bahut hi punya sthaan hai."
        return f"Bahut badhiya, {val} ek uttam sthaan hai."

    if current_field == "pandit-exp":
        if "10" in val or "20" in val or "lamba" in val_lower or "20+" in val:
            return f"Itna lamba anubhav! Bahut hi aadar-yogya hai {pji}."
        return f"Bahut badhiya {fn_ji}! Aapka anubhav bhakton ke kaam aayega."

    if current_field == "pandit-spec":
        if "jyotish" in val_lower or "kundali" in val_lower:
            return "Jyotish Shastra jaisa gehra vishay — aapke gyaan se bahut logon ko disha milegi."
        elif "vedic" in val_lower or "havan" in val_lower:
            return "Vedic parampara ko jeevit rakhna bahut punya ka kaam hai."
        elif "sanskar" in val_lower:
            return "Sanskaron ka margdarshan karna bahut zimmedari ka kaam hai."
        elif "katha" in val_lower or "pravachan" in val_lower:
            return "Aapki vaani se bahut logon ko gyaan milta hoga."
        return f"Bahut sundar {fn_ji}! Aapki yeh visheshagyata bahut saraahniya hai."

    if current_field == "pandit-state":
        return f"Dhanyawad {sn_ji}! {val} se jude Panditji humare prant ki shaan hain."

    if current_field == "pandit-phone":
        formatted_phone = format_phone_for_speech(val)
        return f"Shukriya {sn_ji}! Maine aapka mobile number {formatted_phone} record kar liya hai."

    if current_field == "pandit-email":
        return f"Bahut badhiya {pji}! Maine aapka email address {val} record kar liya hai."

    return f"Bahut sundar {fn_ji}!"


def format_phone_for_speech(phone: str) -> str:
    """Format 10-digit phone number as space-separated digit groups (e.g. '999 888 7776') for TTS and spoken text."""
    if not phone or phone == "Not provided":
        return phone
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) == 10:
        return f"{digits[:3]} {digits[3:6]} {digits[6:]}"
    elif len(digits) > 0:
        return " ".join(digits)
    return phone

INDIAN_CITIES_DATASET: dict[str, list[str]] = {
    # Unambiguous cities (mapping to exactly 1 state)
    "varanasi": ["Uttar Pradesh"],
    "kashi": ["Uttar Pradesh"],
    "haridwar": ["Uttarakhand"],
    "rishikesh": ["Uttarakhand"],
    "ujjain": ["Madhya Pradesh"],
    "mathura": ["Uttar Pradesh"],
    "ayodhya": ["Uttar Pradesh"],
    "vrindavan": ["Uttar Pradesh"],
    "puri": ["Odisha"],
    "rameshwaram": ["Tamil Nadu"],
    "kedarnath": ["Uttarakhand"],
    "badrinath": ["Uttarakhand"],
    "gaya": ["Bihar"],
    "tirupati": ["Andhra Pradesh"],
    "nashik": ["Maharashtra"],
    "dwarka": ["Gujarat"],
    "prayagraj": ["Uttar Pradesh"],
    "allahabad": ["Uttar Pradesh"],
    "delhi": ["Delhi"],
    "new delhi": ["Delhi"],
    "mumbai": ["Maharashtra"],
    "pune": ["Maharashtra"],
    "kolkata": ["West Bengal"],
    "chennai": ["Tamil Nadu"],
    "bengaluru": ["Karnataka"],
    "bangalore": ["Karnataka"],
    "hyderabad": ["Telangana"],
    "ahmedabad": ["Gujarat"],
    "jaipur": ["Rajasthan"],
    "hapur": ["Uttar Pradesh"],
    "lucknow": ["Uttar Pradesh"],
    "kanpur": ["Uttar Pradesh"],
    "patna": ["Bihar"],
    "bhopal": ["Madhya Pradesh"],
    "indore": ["Madhya Pradesh"],
    "nagpur": ["Maharashtra"],
    "surat": ["Gujarat"],
    "vadodara": ["Gujarat"],
    "agra": ["Uttar Pradesh"],
    "meerut": ["Uttar Pradesh"],
    "noida": ["Uttar Pradesh"],
    "ghaziabad": ["Uttar Pradesh"],
    "gurugram": ["Haryana"],
    "gurgaon": ["Haryana"],
    "faridabad": ["Haryana"],
    "chandigarh": ["Punjab"],
    "ludhiana": ["Punjab"],
    "amritsar": ["Punjab"],
    "dehradun": ["Uttarakhand"],
    "shimla": ["Himachal Pradesh"],
    "ranchi": ["Jharkhand"],
    "jamshedpur": ["Jharkhand"],
    "bhubaneswar": ["Odisha"],
    "guwahati": ["Assam"],
    "thiruvananthapuram": ["Kerala"],
    "kochi": ["Kerala"],
    "coimbatore": ["Tamil Nadu"],
    "madurai": ["Tamil Nadu"],
    "mysuru": ["Karnataka"],
    "mysore": ["Karnataka"],
    "srinagar": ["Jammu and Kashmir"],
    "jammu": ["Jammu and Kashmir"],
    "jodhpur": ["Rajasthan"],
    "udaipur": ["Rajasthan"],
    "kota": ["Rajasthan"],
    "gwalior": ["Madhya Pradesh"],
    "jabalpur": ["Madhya Pradesh"],
    "raipur": ["Chhattisgarh"],
    "cuttack": ["Odisha"],
    "siliguri": ["West Bengal"],
    "asansol": ["West Bengal"],
    "dhanbad": ["Jharkhand"],
    "bokaro": ["Jharkhand"],
    "shillong": ["Meghalaya"],
    "imphal": ["Manipur"],
    "agartala": ["Tripura"],
    "aizawl": ["Mizoram"],
    "kohima": ["Nagaland"],
    "gangtok": ["Sikkim"],
    "itanagar": ["Arunachal Pradesh"],
    "panaji": ["Goa"],
    "margao": ["Goa"],
    "mangalore": ["Karnataka"],
    "mangaluru": ["Karnataka"],
    "hubli": ["Karnataka"],
    "dharwad": ["Karnataka"],
    "belgaum": ["Karnataka"],
    "belagavi": ["Karnataka"],
    "thrissur": ["Kerala"],
    "kollam": ["Kerala"],
    "kozhikode": ["Kerala"],
    "calicut": ["Kerala"],
    "tiruchirappalli": ["Tamil Nadu"],
    "trichy": ["Tamil Nadu"],
    "salem": ["Tamil Nadu"],
    "tirunelveli": ["Tamil Nadu"],
    "vellore": ["Tamil Nadu"],
    "vijayawada": ["Andhra Pradesh"],
    "visakhapatnam": ["Andhra Pradesh"],
    "vizag": ["Andhra Pradesh"],
    "guntur": ["Andhra Pradesh"],
    "warangal": ["Telangana"],
    "nizamabad": ["Telangana"],
    "karimnagar": ["Telangana"],
    "bareilly": ["Uttar Pradesh"],
    "aligarh": ["Uttar Pradesh"],
    "moradabad": ["Uttar Pradesh"],
    "saharanpur": ["Uttar Pradesh"],
    "gorakhpur": ["Uttar Pradesh"],
    "jhansi": ["Uttar Pradesh"],
    "mathura vrindavan": ["Uttar Pradesh"],
    "muzaffarnagar": ["Uttar Pradesh"],
    "rohtak": ["Haryana"],
    "panipat": ["Haryana"],
    "karnal": ["Haryana"],
    "hisar": ["Haryana"],
    "sonipat": ["Haryana"],

    # Genuinely ambiguous cities (same name in multiple states)
    "bilaspur": ["Chhattisgarh", "Himachal Pradesh", "Uttar Pradesh", "Haryana"],
    "aurangabad": ["Maharashtra", "Bihar"],
    "pratapgarh": ["Uttar Pradesh", "Rajasthan"],
    "hamirpur": ["Himachal Pradesh", "Uttar Pradesh"],
    "balrampur": ["Uttar Pradesh", "Chhattisgarh"],
}

def get_state_for_city(city_name: str) -> tuple[str, Any]:
    """Look up city in INDIAN_CITIES_DATASET.
    Returns:
      ("SINGLE", "State Name") if unambiguous
      ("AMBIGUOUS", ["State1", "State2", ...]) if city exists in multiple states
      ("UNKNOWN", None) if city is not found in dataset
    """
    if not city_name:
        return ("UNKNOWN", None)
    c_lower = city_name.strip().lower()
    
    if c_lower in INDIAN_CITIES_DATASET:
        states = INDIAN_CITIES_DATASET[c_lower]
        return ("SINGLE", states[0]) if len(states) == 1 else ("AMBIGUOUS", states)
            
    for k, states in INDIAN_CITIES_DATASET.items():
        if k in c_lower or c_lower in k:
            return ("SINGLE", states[0]) if len(states) == 1 else ("AMBIGUOUS", states)
                
    return ("UNKNOWN", None)

def format_value_for_display(val: Any) -> str:
    """Formats raw field values (strings, lists, list-strings) into natural speech/text without brackets or quotes."""
    if val is None:
        return ""
    if isinstance(val, (list, tuple, set)):
        items = [str(x).strip() for x in val if str(x).strip()]
        if not items:
            return ""
        if len(items) == 1:
            return items[0]
        elif len(items) == 2:
            return f"{items[0]} aur {items[1]}"
        else:
            return f"{', '.join(items[:-1])} aur {items[-1]}"
    elif isinstance(val, str):
        val_str = val.strip()
        if val_str.startswith("[") and val_str.endswith("]"):
            try:
                import ast
                parsed = ast.literal_eval(val_str)
                if isinstance(parsed, (list, tuple, set)):
                    return format_value_for_display(parsed)
            except Exception:
                pass
        return val_str
    return str(val)

def is_upload_confirmed(user_message: str) -> bool:
    msg_lower = user_message.lower().strip()
    completion_keywords = [
        "ho gaya", "kardiya", "kar diya", "upload kar diya", "upload ho gaya", "done", "complete", "yes", "ok", "kuchh bhi", "ho gya", "kardi", "uploaded", "okay", "confirmed",
        "हो गया", "कर दिया", "डन", "अपलोड कर दिया", "अपलोड हो गया", "submit", "सबमिट"
    ]
    return any(k in msg_lower for k in completion_keywords)

def generate_summary_text(first_name: str, collected_data: dict, address_info: dict = None) -> str:
    """Generate the end-of-flow voice confirmation summary text."""
    first_name_val = collected_data.get("pandit-first-name", "Panditji")
    last_name_val = collected_data.get("pandit-last-name", "")
    full_name = f"{first_name_val} {last_name_val}".strip()
    
    phone_raw = collected_data.get("pandit-phone", "Not provided")
    phone_val = format_phone_for_speech(phone_raw)
    email_val = collected_data.get("pandit-email", "Not provided")
    gender_val = collected_data.get("pandit-gender", "Not provided")
    avail_val = collected_data.get("pandit-availability", "Not provided")
    city_val = collected_data.get("pandit-city", "Not provided")
    state_val = collected_data.get("pandit-state", "Not provided")
    
    areas = collected_data.get("pandit-service-areas", [])
    areas_str = format_value_for_display(areas)
    
    exp_val = collected_data.get("pandit-exp", "Not provided")
    gurukul_val = collected_data.get("pandit-gurukul", "Not provided")
    
    langs = collected_data.get("pandit-languages", [])
    langs_str = format_value_for_display(langs)
    
    specs = collected_data.get("pandit-spec", [])
    specs_str = format_value_for_display(specs)
    
    achvs = collected_data.get("pandit-achievements", [])
    achvs_str = format_value_for_display(achvs)
    
    bio_val = collected_data.get("pandit-bio", "Not provided")
    address_label = address_info.get("first_name_ji", f"{first_name} ji") if address_info else f"{first_name} ji"
    
    return (
        f"{address_label}, chaliye ek baar confirm kar lete hain — aapka naam {full_name} hai, "
        f"gender {gender_val}, mobile number {phone_val}, email {email_val}, availability mode {avail_val}, "
        f"city {city_val}, state {state_val}, service areas {areas_str}, experience {exp_val}, "
        f"education {gurukul_val}, languages {langs_str}, specialization {specs_str}, "
        f"achievements {achvs_str}, aur bio {bio_val} hai. Kya yeh sab sahi hai?"
    )

def is_affirmative(user_message: str) -> bool:
    """Check if the user response is an affirmative confirmation or progress command."""
    user_text = (user_message or "").lower().strip()
    AFFIRMATIVE_WORDS = [
        "haan", "ha", "haa", "han", "hama", "hanji", "haji",
        "yes", "yeah", "yep", "ya", "yah",
        "sahi", "sahi hai", " sahi",
        "theek", "theek hai", "thik", "thik hai",
        "bilkul", "bilkul sahi",
        "correct", "right",
        "aage", "aage badho", "aage bado", "age badho", "age bado", "aage badh", "aage chalo", "aage badhiye",
        "next", "done", "ok", "okay",
        "ho gaya", "kar do", "kar diya",
        "continue", "proceed",
        "move", "move on",
        "accha", "achha", "acha",
        "हाँ", "हां", "जी", "जी हां", "जी हाँ", "सही", "ठीक", "सब सही", "सब ठीक",
        "आगे बढ़ो", "आगे बढो", "बढ़िया", "सब सही है", "सही है", "ठीक है", "हां सब सही है", "हाँ सब सही है", "वेरीफाई"
    ]
    negative_keywords = ["nahi", "galat", "wrong", "badlo", "dobara", "correction", "नहीं", "नही", "गलत", "बदलो"]

    has_aff = any(word in user_text for word in AFFIRMATIVE_WORDS)
    has_neg = any(word in user_text for word in negative_keywords)
    res = has_aff and not (has_neg and not ("aage" in user_text or "yes" in user_text or "haan" in user_text or "theek" in user_text or "sahi" in user_text or "done" in user_text))

    logger.info(f"[CONFIRM-CHECK] user_text='{user_text}' is_affirmative={res}")
    return res

def is_negative(user_message: str) -> bool:
    """Check if the user response contains a negative confirmation or rejection phrase."""
    user_text = (user_message or "").lower().strip()
    REJECTION_PHRASES = [
        "nahi", "nahin", "nhi", "na", "no", "nope", "not",
        "galat", "galat hai", "wrong", "incorrect", "badlo", "change",
        "dobara", "phir se", "re-enter", "nahi galat hai", "no wrong", "galat hai nahi",
        "नहीं", "नही", "ना", "गलत", "गलत है", "बदलो", "दोबारा", "फिर से"
    ]
    return any(phrase in user_text for phrase in REJECTION_PHRASES)

def is_pure_negative(user_message: str) -> bool:
    """Check if user message is ONLY a rejection phrase without an inline replacement value."""
    user_text = (user_message or "").lower().strip()
    text_no_apostrophe = re.sub(r"['’`]", "", user_text)
    text_nopunct = re.sub(r"[^\w\s\u0900-\u097f]", " ", text_no_apostrophe)
    cleaned = re.sub(
        r'(?<![\w\u0900-\u097f])(nahi|nahin|nhi|na|no|nope|not|galat|hai|is|that|thats|wrong|incorrect|badlo|change|dobara|phir|se|re-enter|ji|jee|jiya|जी|नहीं|नही|ना|गलत|है|बदलो|दोबारा|फिर|से)(?![\w\u0900-\u097f])',
        '', text_nopunct, flags=re.IGNORECASE
    ).strip()
    cleaned = re.sub(r'\s+', '', cleaned).strip()
    return is_negative(user_message) and len(cleaned) == 0


async def detect_correction_field(user_message: str, ai_service: AIService) -> str:
    """Detect which field the user wants to correct."""
    msg_lower = user_message.lower()
    if any(k in msg_lower for k in ["phone", "mobile", "number", "फ़ोन", "फोन", "मोबाइल", "नंबर"]):
        return "pandit-phone"
    if any(k in msg_lower for k in ["email", "mail", "ईमेल", "मेल"]):
        return "pandit-email"
    if any(k in msg_lower for k in ["name", "naam", "नाम"]):
        return "pandit-name"
    if any(k in msg_lower for k in ["city", "sheher", "shahar", "शहर"]):
        return "pandit-city"
    if any(k in msg_lower for k in ["state", "rajya", "राज्य"]):
        return "pandit-state"
    if any(k in msg_lower for k in ["exp", "experience", "anubhav", "अनुभव"]):
        return "pandit-exp"
    if any(k in msg_lower for k in ["spec", "specialization", "visheshagyata", "विशेषज्ञता"]):
        return "pandit-spec"
    if any(k in msg_lower for k in ["lang", "language", "bhasha", "भाषा"]):
        return "pandit-lang"
        
    prompt = f"""The user is reviewing their registered details and wants to change a field.
User Message: "{user_message}"
Choose the exact target field to correct from this list:
'pandit-name', 'pandit-phone', 'pandit-email', 'pandit-city', 'pandit-state', 'pandit-exp', 'pandit-spec', 'pandit-lang'.
Return ONLY the exact field string."""
    llm_req = LLMRequest(
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_message}],
        temperature=0.0
    )
    try:
        response = await ai_service.generate(request=llm_req)
        val = response.content.strip().replace('"', '').replace("'", "")
        return val if val in ["pandit-name", "pandit-phone", "pandit-email", "pandit-city", "pandit-state", "pandit-exp", "pandit-spec", "pandit-lang"] else "pandit-phone"
    except Exception:
        return "pandit-phone"

def normalize_spoken_input(user_message: str, field: str) -> str:
    """Pre-process spoken transcripts for emails and phone numbers before LLM extraction."""
    text = user_message.strip()
    
    if field in ["pandit-email", "email"]:

        # Remove common email filler prefixes
        text = re.sub(r'^(mera\s+)?(email\s+address|email\s+id|email)\s+(hai\s+)?', '', text, flags=re.IGNORECASE).strip()

        # 0. Convert spoken digit words inside emails (e.g. "one two one two three four at the rate gmail dot com" -> "121234 at the rate gmail dot com")
        english_digit_words = [
            (r'\b(zero|shunya|jiro)\b', '0'),
            (r'\b(one|ek|ekk)\b', '1'),
            (r'\b(two|do|doo)\b', '2'),
            (r'\b(three|teen|tin)\b', '3'),
            (r'\b(four|char|chaar)\b', '4'),
            (r'\b(five|panch|paanch)\b', '5'),
            (r'\b(six|chhe|che)\b', '6'),
            (r'\b(seven|saat|sat)\b', '7'),
            (r'\b(eight|aath|ath)\b', '8'),
            (r'\b(nine|nau|now)\b', '9')
        ]
        for pattern, digit in english_digit_words:
            text = re.sub(pattern, digit, text, flags=re.IGNORECASE)

        # 1. Transliterate Devanagari Hindi phonetic letters to English ASCII
        devanagari_phrases = [
            (r'(एट द रेट|ऍट द रेट|एट rate|एट-द-रेट|ऐट|एट)', '@'),
            (r'(जी\s*एम\s*ए\s*[एआई]\s*एल\s*सी\s*ओ\s*एम|जीएमएएएलसीओएम)', 'gmail.com'),
            (r'(जी\s*एम\s*ए\s*[एआई]\s*एल|जीएमएएएल|जीमेल|जी\s*मेल)', 'gmail'),
            (r'(सी\s*ओ\s*एम|सीओएम|कॉम)', 'com'),
            (r'(डॉट|डाट|बिंदु)', '.'),
        ]
        for pattern, repl in devanagari_phrases:
            text = re.sub(pattern, repl, text, flags=re.IGNORECASE)

        devanagari_letters = [
            ("ए", "a"), ("बी", "b"), ("सी", "c"), ("डी", "d"), ("ई", "e"), ("एफ", "f"),
            ("जी", "g"), ("एच", "h"), ("आई", "i"), ("जे", "j"), ("के", "k"), ("एल", "l"),
            ("एम", "m"), ("एन", "n"), ("ओ", "o"), ("पी", "p"), ("क्यू", "q"), ("आर", "r"),
            ("एस", "s"), ("टी", "t"), ("यू", "u"), ("वी", "v"), ("डब्लू", "w"), ("डब्ल्यू", "w"),
            ("एक्स", "x"), ("वाय", "y"), ("जेड", "z"),
            ("ग", "g"), ("ह", "h"), ("व", "v"), ("र", "r"), ("स", "s"), ("म", "m"), ("न", "n"),
            ("ल", "l"), ("ब", "b"), ("त", "t"), ("प", "p"), ("द", "d"), ("क", "k"), ("ट", "t")
        ]
        for dev_let, eng_let in devanagari_letters:
            text = text.replace(dev_let, eng_let)
            
        # 2. Spoken @ symbols in English & Hindi Devanagari
        text = re.sub(r'\b(at the rate of|at the rate|at rate of|at rate|at-the-rate|at)\b', '@', text, flags=re.IGNORECASE)
        text = re.sub(r'(एट द रेट|ऍट द रेट|एट rate|एट-द-रेट|ऐट)', '@', text)
        text = re.sub(r'(?<=\w)\s+at\s+(?=\w+)', '@', text, flags=re.IGNORECASE)
        
        # 3. Spoken . symbols in English & Hindi Devanagari
        text = re.sub(r'\b(dot|point|doot|dott)\b', '.', text, flags=re.IGNORECASE)
        text = re.sub(r'(डॉट|डाट|बिंदु)', '.', text)
        
        # 4. Spoken dash & underscore
        text = re.sub(r'\b(dash|hyphen|डैश)\b', '-', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(underscore|under score|अंडरस्कोर)\b', '_', text, flags=re.IGNORECASE)
        
        # 5. Fix common domain mishearings & spaced letters
        text = re.sub(r'\b(g mail|g-mail|jimmail|jmail|जीमेल|जी मेल|g m a i l|g m a a l)\b', 'gmail', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(yaho|याहू|y a h o o)\b', 'yahoo', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(out look|out-look)\b', 'outlook', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(hot mail|hot-mail)\b', 'hotmail', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(i cloud|i-cloud)\b', 'icloud', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(c o m|कॉम)\b', 'com', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(i n|इन)\b', 'in', text, flags=re.IGNORECASE)
        
        # 6. Auto-insert missing '@' if a known domain is present without '@'
        if '@' not in text:
            text = re.sub(r'(?<=\w)\s+(?=(gmail|yahoo|outlook|hotmail|icloud|mantrasetu)\.(com|in|co\.in|org|net))\b', '@', text, flags=re.IGNORECASE)

        # 7. Check for clean email match first before collapsing spaces
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', text, flags=re.IGNORECASE)
        if email_match:
            return email_match.group(0)

        # 8. Fallback: Collapse ALL whitespace inside email strings e.g. "1 2 1 2 3 4 @ g m a i l . c o m" -> "121234@gmail.com"
        text_no_space = re.sub(r'\s+', '', text)
        email_match = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', text_no_space, flags=re.IGNORECASE)
        if email_match:
            return email_match.group(0)
            
        text = text_no_space
            
    elif field in ["pandit-phone", "phone"]:
        # 1. Convert Devanagari digits to ASCII
        devanagari_digits = str.maketrans("०१२३४५६७८९", "0123456789")
        text = text.translate(devanagari_digits)

        # 2. Convert spoken multipliers e.g. "double 7" -> "77", "triple 9" -> "999", "double zero" -> "00"
        # First convert digit words following "double"/"triple"
        digit_word_to_char = {
            "zero": "0", "shunya": "0", "jiro": "0", "0": "0",
            "one": "1", "ek": "1", "1": "1",
            "two": "2", "do": "2", "2": "2",
            "three": "3", "teen": "3", "3": "3",
            "four": "4", "char": "4", "4": "4",
            "five": "5", "panch": "5", "5": "5",
            "six": "6", "chhe": "6", "6": "6",
            "seven": "7", "saat": "7", "7": "7",
            "eight": "8", "aath": "8", "8": "8",
            "nine": "9", "nau": "9", "9": "9"
        }
        for word, char in digit_word_to_char.items():
            text = re.sub(r'\b(double|डबल)\s+' + word + r'\b', char * 2, text, flags=re.IGNORECASE)
            text = re.sub(r'\b(triple|ट्रिपल)\s+' + word + r'\b', char * 3, text, flags=re.IGNORECASE)
        
        # 3. Map spoken Hindi words (Devanagari) to digits
        hindi_digit_map = {
            "शून्य": "0", "जीरो": "0", "एक": "1", "दो": "2", "तीन": "3", "चार": "4",
            "पांच": "5", "पाँच": "5", "छह": "6", "छः": "6", "सात": "7", "आठ": "8", "नौ": "9"
        }
        for word, digit in hindi_digit_map.items():
            text = text.replace(word, digit)
        roman_hindi_digit_map = [
            (r'\b(shunya|zero|jiro)\b', '0'),
            (r'\b(ek|ekk|one)\b', '1'),
            (r'\b(do|doo|two)\b', '2'),
            (r'\b(teen|tin|three)\b', '3'),
            (r'\b(char|chaar|four)\b', '4'),
            (r'\b(panch|paanch|five)\b', '5'),
            (r'\b(chhe|che|chh|six)\b', '6'),
            (r'\b(saat|sat|seven)\b', '7'),
            (r'\b(aath|ath|eight)\b', '8'),
            (r'\b(nau|now|nine)\b', '9')
        ]
        for pattern, digit in roman_hindi_digit_map:
            text = re.sub(pattern, digit, text, flags=re.IGNORECASE)
            
        # 5. Extract digits only and strip spaces
        digits_only = re.sub(r'\D', '', text)
        
        # 6. Strip country codes +91, 91, or leading 0 if 11 or 12 digits
        if len(digits_only) == 11 and digits_only.startswith('0'):

            digits_only = digits_only[1:]
        elif len(digits_only) == 12 and digits_only.startswith('91'):
            digits_only = digits_only[2:]
            
        # 6. Find 10-digit Indian mobile number starting with 5-9
        if len(digits_only) == 10 and re.match(r'^[56789]', digits_only):
            text = digits_only
        else:
            phone_match = re.search(r'\b[56789]\d{9}\b', text)
            if phone_match:
                text = phone_match.group(0)
            else:
                text = digits_only
            
    return text

DEVANAGARI_CONSONANTS = {
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng', 'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'nya',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n', 'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm', 'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h'
}

DEVANAGARI_VOWELS_INDEPENDENT = {
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ऋ': 'ri', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au'
}

DEVANAGARI_MATRAS = {
    'ा': 'a', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'ृ': 'ri', 'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ं': 'n', 'ँ': 'n'
}

def to_roman_text(text: str) -> str:
    """Ensure text is always in English/Roman script. Transliterates Devanagari Hindi characters to English letters."""
    if not text or text == "INVALID" or text.startswith("QUESTION:"):
        return text
    if any('\u0900' <= char <= '\u097f' for char in text):
        res = []
        n = len(text)
        for i, char in enumerate(text):
            if char in DEVANAGARI_CONSONANTS:
                base = DEVANAGARI_CONSONANTS[char]
                next_char = text[i+1] if i + 1 < n else None
                if next_char and (next_char in DEVANAGARI_MATRAS or next_char == '्'):
                    res.append(base)
                else:
                    if next_char is None and len(text) > 1:
                        res.append(base)
                    else:
                        res.append(base + 'a')
            elif char in DEVANAGARI_VOWELS_INDEPENDENT:
                res.append(DEVANAGARI_VOWELS_INDEPENDENT[char])
            elif char in DEVANAGARI_MATRAS:
                res.append(DEVANAGARI_MATRAS[char])
            elif char == '्':
                continue
            elif '\u0900' <= char <= '\u097f':
                continue
            else:
                res.append(char)
        transliterated = "".join(res).strip().title()
        logger.info("[ROMAN-CONVERTER] Converted Devanagari '%s' to English Roman text: '%s'", text, transliterated)
        return transliterated
    return text

def convertSpokenEmailToText(spoken: str) -> str:
    """Convert spoken email strings (e.g. 'yash mishra 2147 at gmail dot com') to clean email ('yashmishra2147@gmail.com')."""
    if not spoken:
        return ""
    text = to_roman_text(spoken).lower().strip()
    
    text = re.sub(r'\b(at the rate of|at the rate|at rate of|at rate|at-the-rate|at)\b', '@', text, flags=re.IGNORECASE)
    text = re.sub(r'(?<=\w)\s+at\s+(?=\w+)', '@', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(dot|point|doot|dott)\b', '.', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(dash|hyphen)\b', '-', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(underscore|under score)\b', '_', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(g mail|g-mail|jimmail|jmail)\b', 'gmail', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(yaho)\b', 'yahoo', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(c o m)\b', 'com', text, flags=re.IGNORECASE)
    
    if '@' not in text:
        text = re.sub(r'(?<=\w)\s+(?=(gmail|yahoo|outlook|hotmail|icloud|mantrasetu)\.(com|in|co\.in|org|net))\b', '@', text, flags=re.IGNORECASE)
        
    email_clean = re.sub(r'\s+', '', text)
    match = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', email_clean)
    if match:
        return match.group(0)
    return email_clean

async def extract_field_value(user_message: str, field: str, ai_service: AIService) -> str:
    """Extract a clean field value from user response using the LLM.
    
    If the response is ambiguous, off-topic, or not a valid answer for the field, returns "INVALID".
    """
    user_message_normalized = normalize_spoken_input(user_message, field)
    logger.info("[PANDIT-ONBOARDING] extract_field_value | field: %s | raw: %r | normalized: %r", field, user_message, user_message_normalized)

    if is_pure_negative(user_message):
        logger.info("[PANDIT-ONBOARDING] extract_field_value received pure negative rejection message %r. Returning INVALID.", user_message)
        return "INVALID"

    if field in ["pandit-certFile", "pandit-aadhaarFile", "pandit-galleryFiles", "pandit-password", "pandit-confirm"]:
        logger.info("[PANDIT-ONBOARDING] Bypassing LLM extraction for confirmation-only field: %s", field)
        return to_roman_text(user_message_normalized)

    if field in ["pandit-email", "email"]:
        email_val = convertSpokenEmailToText(user_message_normalized)
        if email_val and "@" in email_val:
            logger.info("[PANDIT-ONBOARDING] Spoken email conversion result: %s", email_val)
            return email_val

    field_descs = {
        "pandit-first-name": "First name of the Pandit (e.g. Ramesh, Sunil, Amit, etc.)",
        "pandit-last-name": "Last name / surname of the Pandit (e.g. Sharma, Shastri, Mishra, etc.)",
        "pandit-email": "Email address (e.g. sharma@gmail.com, ramesh@yahoo.co.in, etc.)",
        "pandit-phone": "Mobile number or phone number (10-digit number, e.g. 9876543210, etc.)",
        "pandit-gender": "Gender of the Pandit (choices: Male, Female, Other)",
        "pandit-availability": "Availability mode of the Pandit (choices: Offline, Online, Both)",
        "pandit-city": "Indian city of residence (e.g. Varanasi, Delhi, Mumbai, etc.)",
        "pandit-state": "Indian state of residence (e.g. Uttar Pradesh, Maharashtra, Delhi, etc.)",
        "pandit-service-areas": "Service areas where the Pandit can perform rituals, comma-separated if multiple (e.g. Delhi NCR, Online Puja, Mumbai, etc.)",
        "pandit-exp": "Years of experience (e.g. 10 years, 5 years, etc.)",
        "pandit-gurukul": "Educational background or Gurukul attended (e.g. Acharya, Sampurnanand Sanskrit Vishwavidyalaya, etc.)",
        "pandit-languages": "Languages spoken for rituals, comma-separated if multiple (choices: Hindi, Sanskrit, English, Gujarati, Marathi, Bengali, Tamil, Telugu)",
        "pandit-spec": "Specializations, comma-separated if multiple (choices: Vedic Pujas & Havan, Jyotish & Kundali, Sanskar Ceremonies, Katha & Pravachan)",
        "pandit-achievements": "Achievements or awards received by the Pandit (e.g. Performed 500+ pujas, Gold medalist in Sanskrit, etc.)",
        "pandit-bio": "Brief biography or description of the Pandit's spiritual journey",
    }
    field_desc = field_descs.get(field, field)

    # Deterministic Fast-Path for First Name & Last Name (0ms Latency)
    if field in ["pandit-first-name", "first-name"]:
        clean = re.sub(r'^(mera|my|apna|मेरा|अपना)\s+(naam|name|नाम)\s+(hai|is|है)\s*', '', user_message_normalized, flags=re.IGNORECASE).strip()
        clean = re.sub(r'\b(hai|is|है|जी|shri|pandit|पंडित|श्री)\b', '', clean, flags=re.IGNORECASE).strip()
        words = clean.split()
        if 1 <= len(words) <= 2 and all(len(w) >= 2 for w in words):
            if words[0].lower() not in ["nahi", "nahin", "galat", "no", "wrong", "nhi", "नहीं", "नही", "गलत"]:
                extracted_name = to_roman_text(words[0].capitalize())
                logger.info("[PANDIT-ONBOARDING] Deterministic fast-path for pandit-first-name: %s", extracted_name)
                return extracted_name

    if field in ["pandit-last-name", "last-name"]:
        clean = re.sub(r'^(mera|my|apna|मेरा|अपना)\s+(upnaam|last name|surname|उपनाम|सरनेम)\s+(hai|is|है)\s*', '', user_message_normalized, flags=re.IGNORECASE).strip()
        clean = re.sub(r'\b(hai|is|है|जी|shri|pandit|पंडित|श्री)\b', '', clean, flags=re.IGNORECASE).strip()
        words = clean.split()
        if 1 <= len(words) <= 2 and all(len(w) >= 2 for w in words):
            if words[-1].lower() not in ["nahi", "nahin", "galat", "no", "wrong", "nhi", "नहीं", "नही", "गलत"]:
                extracted_name = to_roman_text(words[-1].capitalize())
                logger.info("[PANDIT-ONBOARDING] Deterministic fast-path for pandit-last-name: %s", extracted_name)
                return extracted_name

    # Deterministic Fast-Path for Phone and Email (0ms Latency & 100% Deterministic Reliability)
    if field in ["pandit-phone", "phone"]:
        digits_only = re.sub(r'\D', '', user_message_normalized)
        if len(digits_only) == 11 and digits_only.startswith('0'):
            digits_only = digits_only[1:]
        elif len(digits_only) == 12 and digits_only.startswith('91'):
            digits_only = digits_only[2:]
            
        if len(digits_only) == 10 and re.match(r'^[56789]', digits_only):
            logger.info("[PANDIT-ONBOARDING] Deterministic regex hit for pandit-phone: %s", digits_only)
            return digits_only
        elif len(digits_only) > 10:
            logger.info("[PANDIT-ONBOARDING] Phone input contains too many digits (%d): %s", len(digits_only), digits_only)
            return digits_only
        else:
            phone_match = re.search(r'\b[56789]\d{9}\b', user_message_normalized)
            if phone_match:
                phone_val = phone_match.group(0)
                logger.info("[PANDIT-ONBOARDING] Deterministic regex hit for pandit-phone: %s", phone_val)
                return phone_val
            elif len(digits_only) > 0:
                logger.info("[PANDIT-ONBOARDING] Invalid phone digits: %s", digits_only)
                return digits_only

            
    if field in ["pandit-email", "email"]:
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', user_message_normalized)
        if email_match:
            extracted_email = email_match.group(0)
            logger.info("[PANDIT-ONBOARDING] Deterministic regex hit for pandit-email: %s", extracted_email)
            return extracted_email

    # Deterministic Fast-Path for Specialization (pandit-spec)
    if field in ["pandit-spec", "specialization"]:
        msg_lower = user_message_normalized.lower()
        matched_specs = []
        if any(w in msg_lower for w in ["jyotish", "kundali", "kundli", "astrology", "horoscope", "grah", "rashifal", "milan"]):
            matched_specs.append("Jyotish & Kundali")
        if any(w in msg_lower for w in ["sanskar", "samskara", "shadi", "vivah", "namakaran", "janeu", "mundan", "ceremony"]):
            matched_specs.append("Sanskar Ceremonies")
        if any(w in msg_lower for w in ["katha", "pravachan", "bhagwat", "ramayan", "satyanarayan", "kirtan", "gita"]):
            matched_specs.append("Katha & Pravachan")
        if any(w in msg_lower for w in ["puja", "pujas", "pooja", "poojas", "havan", "hawan", "vedic", "karmakand", "karma kand", "anushthan", "anusthan", "purohit", "yagya", "yajna", "homam"]):
            matched_specs.append("Vedic Pujas & Havan")
        if matched_specs:
            result_specs = ", ".join(matched_specs)
            logger.info("[PANDIT-ONBOARDING] Deterministic match for pandit-spec: %s", result_specs)
            return result_specs

    # Deterministic Fast-Path for Experience (pandit-exp)
    if field in ["pandit-exp", "experience"]:
        msg_lower = user_message_normalized.lower()
        if any(w in msg_lower for w in ["20+", "20 plus", "25", "30", "40", "50", "tees", "pachees", "bees se zyada", "20 saal se zyada"]):
            logger.info("[PANDIT-ONBOARDING] Deterministic match for pandit-exp: 20+ years")
            return "20+ years"
        elif any(w in msg_lower for w in ["10-20", "10 to 20", "1020", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "das saal", "10 saal", "solah", "pandrah", "bees"]):
            logger.info("[PANDIT-ONBOARDING] Deterministic match for pandit-exp: 10-20 years")
            return "10-20 years"
        elif any(w in msg_lower for w in ["5-10", "5 to 10", "510", "6", "7", "8", "9", "chhe", "saat", "aath", "nau", "5 saal", "6 saal", "7 saal", "8 saal", "9 saal"]):
            logger.info("[PANDIT-ONBOARDING] Deterministic match for pandit-exp: 5-10 years")
            return "5-10 years"
        elif any(w in msg_lower for w in ["1-5", "1 to 5", "15", "1", "2", "3", "4", "5", "ek", "do", "teen", "char", "panch", "1 saal", "2 saal", "3 saal", "4 saal"]):
            logger.info("[PANDIT-ONBOARDING] Deterministic match for pandit-exp: 1-5 years")
            return "1-5 years"

    # Deterministic Fast-Path for Gender (pandit-gender)
    if field in ["pandit-gender", "gender"]:
        msg_lower = user_message_normalized.lower()
        if any(w in msg_lower for w in ["female", "mahila", "aurat", "stree", "woman", "lady", "महिला", "औरत", "स्त्री"]):
            logger.info("[PANDIT-ONBOARDING] Deterministic match for pandit-gender: Female")
            return "Female"
        elif any(w in msg_lower for w in ["other", "transgender", "third gender", "anya", "अन्य"]):
            logger.info("[PANDIT-ONBOARDING] Deterministic match for pandit-gender: Other")
            return "Other"
        elif any(w in msg_lower for w in ["male", "purush", "aadmi", "man", "gents", "पुरुष", "आदमी"]):
            logger.info("[PANDIT-ONBOARDING] Deterministic match for pandit-gender: Male")
            return "Male"

    # Deterministic Fast-Path for Languages (pandit-languages)
    if field in ["pandit-languages", "pandit-lang", "language", "languages"]:
        msg_lower = user_message_normalized.lower()
        if any(w in msg_lower for w in ["sahi", "theek", "thik", "okay", "yes", "agreed", "continue", "haan", "default"]):
            logger.info("[PANDIT-ONBOARDING] Deterministic match for pandit-lang: Hindi, Sanskrit")
            return "Hindi, Sanskrit"

    system_prompt = f"""You are an expert data extraction assistant.
The user is providing an answer for the field '{field}' ({field_desc}) in a Pandit registration form.
Your task is to extract ONLY the clean, structured value for this field in Roman/English script.

STRICT VALIDATION RULES:
1. The user's response MUST contain a valid, reasonable answer for the field '{field}'.
   - Extract a 10-digit phone number string (e.g. '9876543210').
   - Remove any spaces, hyphens, or non-digit characters.
4. If the field is 'pandit-exp', you MUST map the user's spoken answer to one of these exact values: '1-5 years', '5-10 years', '10-20 years', '20+ years'. If they say "das saal" or "six years", map to '10-20 years' or '5-10 years' respectively. If not clear or off-topic, return 'INVALID'.
5. If the field is 'pandit-spec', you MUST map the user's spoken answer to one of these exact values: 'Vedic Pujas & Havan', 'Jyotish & Kundali', 'Sanskar Ceremonies', 'Katha & Pravachan'. For example, if they say "havan" or "pujas", map to 'Vedic Pujas & Havan'. If they say "jyotish" or "kundali", map to 'Jyotish & Kundali'. If not clear or off-topic, return 'INVALID'.
6. If the field is 'pandit-lang':
   - If the user agrees, says 'sahi hai', 'theek hai', 'okay', 'yes', 'agreed', 'continue', or approves defaults, return 'Hindi, Sanskrit'.
   - If they mention additional or specific languages (e.g. 'Gujarati bhi add karo', 'sirf Hindi'), extract the final active comma-separated list from choices [Hindi, Sanskrit, English, Gujarati, Marathi, Bengali, Tamil, Telugu]. Default is 'Hindi, Sanskrit'.
7. If the user asks a CLEAR, explicit question mid-onboarding (e.g. "puja booking kaise hoti hai?", "MantraSetu kya hai?"), you MUST briefly answer their question and prefix your response with exactly "QUESTION: ". For example: "QUESTION: Puja booking aap hamari app se kar sakte hain." DO NOT use this for gibberish or mumbled words.
8. If the user's response is off-topic, ambiguous, completely unrelated, or says something like "cancel", "ruko", "mujhe nahi pata" etc. (and is NOT a clear question), you MUST return exactly the word 'INVALID'. Do not try to extract or make up a value.
9. If the answer is completely gibberish or not valid for {field_desc}, return 'INVALID'.

Return ONLY the extracted clean value, the QUESTION: string, or 'INVALID'. Do NOT include any explanations, greetings, or extra words.
"""

    llm_req = LLMRequest(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message_normalized}
        ],
        temperature=0.0,
    )
    
    try:
        response = await asyncio.wait_for(ai_service.generate(request=llm_req), timeout=10.0)
        if not response or not response.content:
            logger.warning("[PANDIT-ONBOARDING] LLM extraction returned empty/None response. Returning INVALID.")
            return "INVALID"
        val = response.content.strip().replace('"', '').replace("'", "")
        logger.info("[PANDIT-ONBOARDING] LLM extraction result for %s: %s", field, val)
        
        # Safety fallback: If the LLM returns a long rambling sentence but forgot the QUESTION: prefix,
        # it shouldn't be accepted as a valid name/field.
        if len(val) > 100 and not val.startswith("QUESTION:"):
            logger.warning("[PANDIT-ONBOARDING] LLM returned unusually long response without QUESTION: prefix. Defaulting to INVALID.")
            return "INVALID"
            
        return to_roman_text(val)
    except Exception as e:
        logger.error("[PANDIT-ONBOARDING] LLM extraction failed or timed out: %s. Returning INVALID.", e)
        return "INVALID"

# ── CENTRALIZED FIELD VALIDATION REGISTRY ──
field_hinglish_names = {
    "pandit-first-name": "pehla naam",
    "pandit-last-name": "last name",
    "pandit-email": "email address",
    "pandit-phone": "mobile number",
    "pandit-gender": "gender",
    "pandit-availability": "availability mode",
    "pandit-city": "sheher",
    "pandit-state": "state ya rajya",
    "pandit-service-areas": "service areas",
    "pandit-exp": "experience",
    "pandit-gurukul": "education ya gurukul background",
    "pandit-languages": "bhashayein",
    "pandit-spec": "specialization",
    "pandit-achievements": "achievements",
    "pandit-bio": "bio",
    "pandit-certFile": "shiksha pramanpatra",
    "pandit-aadhaarFile": "pehchan praman",
    "pandit-galleryFiles": "gallery photos aur videos",
    "pandit-password": "password",
    "pandit-confirm": "confirm password"
}

class FieldValidationResult:
    def __init__(self, is_valid: bool, cleaned_value: Any = None, error_message: str | None = None):
        self.is_valid = is_valid
        self.cleaned_value = cleaned_value
        self.error_message = error_message

FIELD_VALIDATION_REGISTRY: dict[str, Callable[[str, dict], FieldValidationResult]] = {}

def register_field_validator(field_name: str, validator_fn: Callable[[str, dict], FieldValidationResult]):
    FIELD_VALIDATION_REGISTRY[field_name] = validator_fn

# 1. Phone Validator Entry
def _validate_phone(val: str, params: dict) -> FieldValidationResult:
    digits = re.sub(r'\D', '', val)
    if len(digits) == 11 and digits.startswith('0'):
        digits = digits[1:]
    elif len(digits) == 12 and digits.startswith('91'):
        digits = digits[2:]
    if len(digits) == 10 and re.match(r'^[56789]', digits):
        return FieldValidationResult(True, cleaned_value=digits)
    formatted = format_phone_for_speech(digits) if digits else ""
    if digits:
        err = f"Maine suna: '{formatted}', lekin mobile number 10 digits ka hona chahiye. Kripya apna 10-digit mobile number dobara bataiye."
    else:
        err = "Maaf kijiye, main mobile number samajh nahi paya. Kripya apna 10-digit mobile number dobara bataiye."
    return FieldValidationResult(False, error_message=err)

register_field_validator("pandit-phone", _validate_phone)

# 2. Email Validator Entry
def _validate_email(val: str, params: dict) -> FieldValidationResult:
    match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', val)
    if match:
        return FieldValidationResult(True, cleaned_value=match.group(0))
    if val and val != "INVALID" and "@" in val:
        err = f"Maine suna: '{val}', lekin email address mein '@' aur domain (jaise name@gmail.com) hona zaroori hai. Kripya valid email address dobara bataiye."
    else:
        err = "Maaf kijiye, main email address samajh nahi paya. Kripya apna email address (jaise ramesh@gmail.com) dobara bataiye."
    return FieldValidationResult(False, error_message=err)

register_field_validator("pandit-email", _validate_email)

# 3. Choice Validator Generator
def _make_choice_validator(choices: list[str], label: str) -> Callable[[str, dict], FieldValidationResult]:
    def validator(val: str, params: dict) -> FieldValidationResult:
        if not val or val == "INVALID":
            return FieldValidationResult(False, error_message=f"Maaf kijiye, main {label} samajh nahi paya. Dobara bataiye.")
        val_lower = val.lower().strip()
        
        # 1. Exact match check first
        for ch in choices:
            if ch.lower() == val_lower:
                return FieldValidationResult(True, cleaned_value=ch)
                
        # 2. Word boundary / substring check (preventing "male" inside "female")
        matched = []
        for ch in choices:
            ch_lower = ch.lower()
            if re.search(r'\b' + re.escape(ch_lower) + r'\b', val_lower) or val_lower in ch_lower:
                matched.append(ch)
        if matched:
            return FieldValidationResult(True, cleaned_value=matched[0])
            
        choices_str = ", ".join(choices)
        return FieldValidationResult(False, error_message=f"Maaf kijiye, main '{val}' ko valid {label} ke roop mein nahi mila. Valid choices hain: {choices_str}. Dobara bataiye.")
    return validator

register_field_validator("pandit-gender", _make_choice_validator(["Male", "Female", "Other"], "gender"))
register_field_validator("pandit-availability", _make_choice_validator(["Offline", "Online", "Both"], "availability mode"))

# 4. Multi-Choice Validator Generator (Languages & Specs)
def _make_multi_choice_validator(choices: list[str], label: str) -> Callable[[str, dict], FieldValidationResult]:
    def validator(val: str, params: dict) -> FieldValidationResult:
        if not val or val == "INVALID":
            return FieldValidationResult(False, error_message=f"Maaf kijiye, main {label} samajh nahi paya. Dobara bataiye.")
        parts = [p.strip() for p in val.split(",") if p.strip()]
        valid_matches = []
        invalid_matches = []
        for p in parts:
            p_lower = p.lower()
            found = False
            # 1. Exact match check first
            for ch in choices:
                if ch.lower() == p_lower:
                    if ch not in valid_matches:
                        valid_matches.append(ch)
                    found = True
                    break
            if not found:
                # 2. Word boundary / substring check
                for ch in choices:
                    ch_lower = ch.lower()
                    if re.search(r'\b' + re.escape(ch_lower) + r'\b', p_lower) or p_lower in ch_lower:
                        if ch not in valid_matches:
                            valid_matches.append(ch)
                        found = True
                        break
            if not found:
                invalid_matches.append(p)
        if invalid_matches:
            choices_str = ", ".join(choices)
            return FieldValidationResult(False, error_message=f"Maaf kijiye, main '{invalid_matches[0]}' ko valid {label} ke roop mein nahi mila. Valid options hain: {choices_str}. Kripya dobara batayein.")
        if valid_matches:
            return FieldValidationResult(True, cleaned_value=valid_matches)
        return FieldValidationResult(False, error_message=f"Maaf kijiye, main {label} samajh nahi paya. Dobara bataiye.")
    return validator

register_field_validator("pandit-languages", _make_multi_choice_validator(["Hindi", "Sanskrit", "English", "Gujarati", "Marathi", "Bengali", "Tamil", "Telugu"], "languages"))
register_field_validator("pandit-spec", _make_multi_choice_validator(["Vedic Pujas & Havan", "Jyotish & Kundali", "Sanskar Ceremonies", "Katha & Pravachan"], "specialization"))

# 5. Confirmation and Password Validators
def _make_confirmation_validator(label: str) -> Callable[[str, dict], FieldValidationResult]:
    def validator(val: str, params: dict) -> FieldValidationResult:
        if val and val != "INVALID" and is_upload_confirmed(val):
            return FieldValidationResult(True, cleaned_value="Done")
        return FieldValidationResult(False, error_message=f"Kripya screen par {label} complete kijiye aur mujhe 'ho gaya' boliye.")
    return validator

register_field_validator("pandit-certFile", _make_confirmation_validator("certificate upload"))
register_field_validator("pandit-aadhaarFile", _make_confirmation_validator("ID proof upload"))
register_field_validator("pandit-galleryFiles", _make_confirmation_validator("gallery uploads"))
register_field_validator("pandit-password", _make_confirmation_validator("password set"))

def _validate_confirm_password(val: str, params: dict) -> FieldValidationResult:
    if not val or val == "INVALID" or not is_upload_confirmed(val):
        return FieldValidationResult(False, error_message="Kripya confirm password enter karke mujhe 'ho gaya' ya 'submit kar do' boliye.")
    pwd = params.get("pandit-password") or params.get("password")
    cpwd = params.get("pandit-confirm") or params.get("confirm_password") or params.get("confirm")
    if pwd and len(pwd) < 8:
        return FieldValidationResult(False, error_message="Password kam se kam 8 characters ka hona chahiye. Kripya naya password set karein.")
    if pwd and cpwd and pwd != cpwd:
        return FieldValidationResult(False, error_message="Aapka password aur confirm password match nahi kar rahe. Kripya screen par matching password type kijiye.")
    return FieldValidationResult(True, cleaned_value="Confirmed")

def _validate_pandit_avatar(val: str, params: dict) -> FieldValidationResult:
    input_lower = (val or "").lower()
    if params.get("avatar_attached") == "true" or is_upload_confirmed(val) or "photo" in input_lower or "upload" in input_lower or "ho gaya" in input_lower:
        return FieldValidationResult(True, cleaned_value="Uploaded")
    if any(k in input_lower for k in ["skip", "baad mein", "aage", "nahi", "leave"]):
        return FieldValidationResult(True, cleaned_value="Skipped")
    return FieldValidationResult(True, cleaned_value="Skipped")

register_field_validator("pandit-avatar", _validate_pandit_avatar)
register_field_validator("pandit-confirm", _validate_confirm_password)

# 6. Standard Non-Empty Validators
def _make_non_empty_validator(hinglish_label: str) -> Callable[[str, dict], FieldValidationResult]:
    def validator(val: str, params: dict) -> FieldValidationResult:
        if val and val != "INVALID" and val.strip():
            return FieldValidationResult(True, cleaned_value=val.strip())
        return FieldValidationResult(False, error_message=f"Maaf kijiye, main {hinglish_label} samajh nahi paya. Dobara bataiye.")
    return validator

register_field_validator("pandit-first-name", _make_non_empty_validator("pehla naam"))
register_field_validator("pandit-last-name", _make_non_empty_validator("last name"))
register_field_validator("pandit-city", _make_non_empty_validator("sheher"))
register_field_validator("pandit-state", _make_non_empty_validator("state ya rajya"))
register_field_validator("pandit-service-areas", _make_non_empty_validator("service areas"))
register_field_validator("pandit-exp", _make_non_empty_validator("experience"))
register_field_validator("pandit-gurukul", _make_non_empty_validator("education ya Gurukul background"))
register_field_validator("pandit-achievements", _make_non_empty_validator("achievement"))
register_field_validator("pandit-bio", _make_non_empty_validator("bio"))

# ── UNIFIED GENERIC FIELD VALIDATOR HANDLER ──
def validate_and_process_field(field_name: str, raw_val: str, user_params: dict, retry_map: dict) -> tuple[bool, Any, str | None]:
    if raw_val and raw_val.startswith("QUESTION:"):
        answer = raw_val.replace("QUESTION:", "").strip()
        hinglish_name = field_hinglish_names.get(field_name, "jankari")
        return False, None, f"{answer} Ab wapas aate hain, kripya apna {hinglish_name} bataiye."

    validator = FIELD_VALIDATION_REGISTRY.get(field_name)
    if not validator:
        if raw_val and raw_val != "INVALID":
            return True, raw_val, None
        return False, None, f"Maaf kijiye, main samajh nahi paya. Dobara bataiye."

    res = validator(raw_val, user_params)
    if not res.is_valid:
        current_retries = retry_map.get(field_name, 0) + 1
        retry_map[field_name] = current_retries
        logger.info("[CENTRAL-VALIDATOR] Validation FAILED for field: %s (attempt %d/3). Error: %s", field_name, current_retries, res.error_message)

        max_allowed_retries = 2 if field_name in ["pandit-first-name", "pandit-last-name", "pandit-name"] else 3
        if current_retries >= max_allowed_retries:
            if field_name in ["pandit-first-name", "pandit-last-name", "pandit-name"]:
                return False, None, "Kripya apna naam type karein"
            hinglish_name = field_hinglish_names.get(field_name, "jankari")
            fallback_msg = f"Lagta hai {hinglish_name} ko samajhne mein dikkat ho rahi hai. Kripya screen par highlight ki gayi field par click karke ise manually fill kar dijiye, taaki hum aage badh sakein."
            return False, None, fallback_msg


        return False, None, res.error_message

    retry_map[field_name] = 0
    return True, res.cleaned_value, None

def sync_next_field_index(state: dict) -> int:
    """Deterministically find the index of the first uncollected field to avoid step index shift."""
    fields = state.get("fields", [])
    collected = state.get("collected_data", {})
    for idx, f in enumerate(fields):
        if f not in collected or collected[f] is None:
            state["current_field_index"] = idx
            return idx
    state["current_field_index"] = len(fields)
    return len(fields)

async def process_onboarding_step(
    request: OrchestratorRequest,
    session: Any,
    orchestrator: Any,
) -> OrchestratorResponse | None:
    """Process one step in the guided Pandit onboarding sequence."""
    state = session.onboarding_state
    if not state:
        logger.warning("[PANDIT-ONBOARDING] process_onboarding_step called but no onboarding_state found.")
        return None

    ai_service = orchestrator._llm_intent_detector._ai
    status = state.get("status", "collecting")
    
    user_params = request.user_parameters if isinstance(request.user_parameters, dict) else {}
    client_active_field = user_params.get("active_field")
    
    # 21 fields in order (starting with pandit-avatar)
    default_fields = [
        "pandit-avatar",
        "pandit-first-name",
        "pandit-last-name",
        "pandit-email",
        "pandit-phone",
        "pandit-gender",
        "pandit-availability",
        "pandit-city",
        "pandit-state",
        "pandit-service-areas",
        "pandit-exp",
        "pandit-gurukul",
        "pandit-languages",
        "pandit-spec",
        "pandit-achievements",
        "pandit-bio",
        "pandit-certFile",
        "pandit-aadhaarFile",
        "pandit-galleryFiles",
        "pandit-password",
        "pandit-confirm"
    ]
    fields = state.get("fields", default_fields)
    state["fields"] = fields

    idx = state.get("current_field_index", 0)
    current_field = client_active_field if (client_active_field and client_active_field in fields) else (fields[idx] if idx < len(fields) else "pandit-first-name")

    
    first_name_val = state["collected_data"].get("pandit-first-name", "Panditji")
    last_name_val = state["collected_data"].get("pandit-last-name", "")
    full_name = f"{first_name_val} {last_name_val}".strip()
    address_info = get_address_forms(full_name)
    first_name = address_info["first_name"]
    fn_ji = address_info["first_name_ji"]
    sn_ji = address_info["surname_ji"]
    pji = address_info["panditji"]

    # Map hinglish names for fallback and correction prompts
    field_hinglish_names_step = {
        "pandit-avatar": "profile photo",
        "pandit-first-name": "pehla naam",
        "pandit-last-name": "last name",
        "pandit-email": "email address",
        "pandit-phone": "mobile number",
        "pandit-gender": "gender",
        "pandit-availability": "availability mode",
        "pandit-city": "sheher",
        "pandit-state": "state ya rajya",
        "pandit-service-areas": "service areas",
        "pandit-exp": "experience",
        "pandit-gurukul": "education ya gurukul background",
        "pandit-languages": "bhashayein",
        "pandit-spec": "specialization",
        "pandit-achievements": "achievements",
        "pandit-bio": "bio",
        "pandit-certFile": "shiksha pramanpatra",
        "pandit-aadhaarFile": "pehchan praman",
        "pandit-galleryFiles": "gallery photos aur videos",
        "pandit-password": "password",
        "pandit-confirm": "confirm password"
    }

    # -------------------------------------------------------------------------
    # CASE 0: Awaiting Individual Field Confirmation ("Maine suna — X. Kya ye sahi hai?")
    # -------------------------------------------------------------------------
    if status == "awaiting_field_confirmation":
        tentative_field = state.get("tentative_field", current_field)
        tentative_value = state.get("tentative_value", "")
        logger.info("[PANDIT-ONBOARDING] AWAITING FIELD CONFIRMATION for %s -> %r | user_msg: %r", tentative_field, tentative_value, request.user_message)
        
        if is_affirmative(request.user_message):
            logger.info("[PANDIT-ONBOARDING] Field %s value %r CONFIRMED by user.", tentative_field, tentative_value)
            state["collected_data"][tentative_field] = tentative_value
            state["tentative_field"] = None
            state["tentative_value"] = None
            state["status"] = "collecting"
            
            # Advance to next field
            next_idx = sync_next_field_index(state)
            if next_idx < len(fields):
                next_field = fields[next_idx]
                session.update_location(page="/signup?role=pandit", field=next_field)
                next_hname = field_hinglish_names_step.get(next_field, next_field)
                question = f"Perfect! Ab aage chalte hain. Ab apna {next_hname} bataiye."
                nav_directive = {"action": "FILL_FORM", "target": tentative_field, "query": tentative_value, "active_field": next_field, "intent": "PANDIT_ONBOARDING"}
            else:
                question = "Perfect! Main abhi aapka registration submit kar raha hoon."
                nav_directive = {"action": "NAVIGATE", "target": "/signup?role=pandit", "active_field": None, "intent": "PANDIT_ONBOARDING"}
            
            orchestrator._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
            return orchestrator._response_builder.build_response(
                request_id=request.request_id,
                text_override=question,
                response_type=ResponseType.NAVIGATION_DIRECTIVE,
                navigation_directive=nav_directive,
                metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
            )
        elif is_pure_negative(request.user_message):
            logger.info("[PANDIT-ONBOARDING] User REJECTED tentative value for field %s without inline correction: %r", tentative_field, request.user_message)
            state["tentative_field"] = None
            state["tentative_value"] = None
            state["status"] = "collecting"
            
            field_hname = field_hinglish_names_step.get(tentative_field, tentative_field)
            question = f"Maaf kijiye! Kripya apna sahi {field_hname} dobara bataiye."
            nav_directive = {"action": None, "target": None, "query": None, "active_field": tentative_field, "intent": "PANDIT_ONBOARDING", "fields": None}
            session.update_location(page="/signup?role=pandit", field=tentative_field)
            return orchestrator._response_builder.build_response(
                request_id=request.request_id,
                text_override=question,
                response_type=ResponseType.CHAT,
                navigation_directive=nav_directive,
                metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
            )
        else:
            logger.info("[PANDIT-ONBOARDING] User provided new answer or correction for field %s during confirmation: %r", tentative_field, request.user_message)
            new_val = await extract_field_value(request.user_message, tentative_field, ai_service)
            is_valid, cleaned_new_val, err_msg = validate_and_process_field(
                tentative_field,
                new_val,
                request.user_parameters if isinstance(request.user_parameters, dict) else {},
                state.setdefault("field_retry_count", {})
            )
            if is_valid and cleaned_new_val and cleaned_new_val != "INVALID":
                old_tentative = state.get("tentative_value", "")
                logger.info(f"[TENTATIVE] old='{old_tentative}' new='{cleaned_new_val}'")
                state["tentative_value"] = cleaned_new_val
                disp_val = format_value_for_display(cleaned_new_val)
                question = f"Maine suna — {disp_val}. Kya ye sahi hai?"

                nav_directive = {"action": "FILL_FORM", "target": tentative_field, "query": cleaned_new_val, "active_field": tentative_field, "intent": "PANDIT_ONBOARDING"}
                orchestrator._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
                return orchestrator._response_builder.build_response(
                    request_id=request.request_id,
                    text_override=question,
                    response_type=ResponseType.NAVIGATION_DIRECTIVE,
                    navigation_directive=nav_directive,
                    metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
                )

            state["tentative_field"] = None
            state["tentative_value"] = None
            state["status"] = "collecting"
            question = f"Ek baar phir boliye, thoda clearly"
            nav_directive = {"action": "FILL_FORM", "target": tentative_field, "query": "", "active_field": tentative_field, "intent": "PANDIT_ONBOARDING"}
            return orchestrator._response_builder.build_response(
                request_id=request.request_id,
                text_override=question,
                response_type=ResponseType.CHAT,
                navigation_directive=nav_directive,
                metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
            )


    # -------------------------------------------------------------------------
    # CASE 1: Awaiting Confirmation Summary Response (End of Step 2)
    # -------------------------------------------------------------------------
    if status == "awaiting_confirmation" or (client_active_field in ["summary", "pandit-summary"] and is_affirmative(request.user_message)):

        logger.info("[PANDIT-ONBOARDING] AWAITING CONFIRMATION turn | user_msg: %r", request.user_message)
        if is_affirmative(request.user_message):
            logger.info("[PANDIT-ONBOARDING] Step 1 & 2 Summary CONFIRMED by user. Moving to Step 3 uploads.")
            state["status"] = "collecting"
            cert_file_idx = fields.index("pandit-certFile")
            state["current_field_index"] = cert_file_idx # Start of Step 3 (pandit-certFile)
            state.setdefault("field_retry_count", {})["pandit-certFile"] = 0
            
            next_field = fields[cert_file_idx] # "pandit-certFile"
            question = (
                f"Bahut badhiya {sn_ji}! Maine aapki saari details check kar li hain aur form mein save kar di hain. "
                f"Chaliye ab Step 3 par chalte hain. Kripya screen par apna Shiksha Pramanpatra (Certificate) upload kijiye aur mujhe 'ho gaya' boliye."
            )
            nav_directive = {
                "action": "NAVIGATE",
                "target": "/signup?role=pandit",
                "active_field": next_field,
                "intent": "PANDIT_ONBOARDING",
                "fields": None
            }
            session.update_location(page="/signup?role=pandit", field=next_field)
            orchestrator._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
            return orchestrator._response_builder.build_response(
                request_id=request.request_id,
                text_override=question,
                response_type=ResponseType.NAVIGATION_DIRECTIVE,
                navigation_directive=nav_directive,
                metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
            )
        else:
            # User wants to correct a field!
            target_field = await detect_correction_field(request.user_message, ai_service)
            # Map target field safely to the new names
            if target_field == "pandit-name":
                target_field = "pandit-first-name"
            elif target_field == "pandit-lang":
                target_field = "pandit-languages"
                
            logger.info("[PANDIT-ONBOARDING] Field correction requested for: %s", target_field)
            state["status"] = "correcting_field"
            state["correcting_field_name"] = target_field
            state.setdefault("field_retry_count", {})[target_field] = 0
            hinglish_name = field_hinglish_names_step.get(target_field, "jankari")
            question = f"Kshama karein {fn_ji}! Kripya apna naya {hinglish_name} bataiye."
            nav_directive = {"action": None, "target": None, "query": None, "active_field": target_field, "intent": "PANDIT_ONBOARDING", "fields": None}
            return orchestrator._response_builder.build_response(
                request_id=request.request_id,
                text_override=question,
                response_type=ResponseType.CHAT,
                navigation_directive=nav_directive,
                metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
            )

    # -------------------------------------------------------------------------
    # CASE 1C: Awaiting City-State Ambiguous Clarification
    # -------------------------------------------------------------------------
    if status == "awaiting_city_state_clarification":
        logger.info("[PANDIT-ONBOARDING] AWAITING CITY STATE CLARIFICATION turn | user_msg: %r", request.user_message)
        ambiguous_city = state.get("ambiguous_city", "city")
        possible_states = state.get("possible_states", ["Uttar Pradesh"])
        primary_state = possible_states[0]
        
        user_msg_lower = request.user_message.lower().strip()
        matched_state = primary_state
        
        for st in possible_states:
            if st.lower() in user_msg_lower:
                matched_state = st
                break
                
        state["collected_data"]["pandit-state"] = matched_state
        state["status"] = "collecting"
        state["ambiguous_city"] = None
        state["possible_states"] = None
        
        # Advance index past pandit-state if needed
        if state["current_field_index"] < len(fields) and fields[state["current_field_index"]] == "pandit-state":
            state["current_field_index"] += 1
            
        next_idx = state["current_field_index"]
        next_field = fields[next_idx] if next_idx < len(fields) else "pandit-service-areas"
        
        reaction = f"Bahut badhiya {fn_ji}!"
        question = f"{reaction} Aap kin service areas mein puja karwane ke liye uplabdh hain? Jaise Delhi NCR, Online Puja, ya Mumbai?"
        
        nav_directive = {
            "action": "FILL_FORM",
            "target": "pandit-state",
            "query": matched_state,
            "active_field": next_field,
            "intent": "PANDIT_ONBOARDING",
            "fields": [
                {"target": "pandit-city", "query": ambiguous_city},
                {"target": "pandit-state", "query": matched_state}
            ]
        }
        orchestrator._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
        return orchestrator._response_builder.build_response(
            request_id=request.request_id,
            text_override=question,
            response_type=ResponseType.NAVIGATION_DIRECTIVE,
            navigation_directive=nav_directive,
            metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
        )

    # -------------------------------------------------------------------------
    # CASE 2: Correcting a Specific Field Value
    # -------------------------------------------------------------------------
    if status == "correcting_field":
        target_field = state.get("correcting_field_name", "pandit-phone")
        logger.info("[PANDIT-ONBOARDING] CORRECTING FIELD turn | field: %s | user_msg: %r", target_field, request.user_message)
        val = await extract_field_value(request.user_message, target_field, ai_service)
        
        is_valid, cleaned_val, err_msg = validate_and_process_field(
            target_field,
            val,
            request.user_parameters if isinstance(request.user_parameters, dict) else {},
            state["field_retry_count"]
        )
        
        if not is_valid:
            logger.info("[PANDIT-ONBOARDING] Field correction failed for %s. Re-asking.", target_field)
            return orchestrator._response_builder.build_response(
                request_id=request.request_id,
                text_override=err_msg,
                response_type=ResponseType.CHAT,
                navigation_directive={"action": None, "target": None, "query": None, "active_field": target_field, "intent": "PANDIT_ONBOARDING", "fields": None},
                metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
            )
            
        state["collected_data"][target_field] = cleaned_val
        first_name_val = state["collected_data"].get("pandit-first-name", "Panditji")
        last_name_val = state["collected_data"].get("pandit-last-name", "")
        full_name = f"{first_name_val} {last_name_val}".strip()
        address_info = get_address_forms(full_name)
        first_name = address_info["first_name"]
            
        logger.info("[PANDIT-ONBOARDING] Field %s corrected to: %r. Returning to confirmation summary.", target_field, cleaned_val)
        state["status"] = "awaiting_confirmation"
        state["correcting_field_name"] = None
        
        hinglish_name = field_hinglish_names_step.get(target_field, "jankari")
        summary_body = generate_summary_text(first_name, state["collected_data"], address_info)
        question = f"Dhanyawad {address_info['surname_ji']}! Maine {hinglish_name} update kar diya hai. {summary_body}"
        
        nav_directive = {
            "action": "FILL_FORM",
            "target": target_field,
            "query": str(cleaned_val),
            "active_field": None,
            "intent": "PANDIT_ONBOARDING",
            "fields": None
        }
        orchestrator._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
        
        return orchestrator._response_builder.build_response(
            request_id=request.request_id,
            text_override=question,
            response_type=ResponseType.NAVIGATION_DIRECTIVE,
            navigation_directive=nav_directive,
            metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
        )

    # -------------------------------------------------------------------------
    # CASE 3: Standard Field Collection Sequence
    # -------------------------------------------------------------------------
    fields = state["fields"]

    # ── Active Field Tag & DOM Input Sync ──
    user_params = request.user_parameters if isinstance(request.user_parameters, dict) else {}
    client_active_field = user_params.get("active_field")
    raw_msg = user_params.get("raw_user_message", request.user_message)
    dom_data = user_params.get("dom_form_data", {})
    collected = state.setdefault("collected_data", {})
    
    # Merge non-empty DOM values into collected_data so manually filled fields are recognized
    for k, v in dom_data.items():
        if v and str(v).strip() and (k not in collected or not collected[k]):
            collected[k] = str(v).strip()
    
    if client_active_field and client_active_field in fields:
        state["current_field_index"] = fields.index(client_active_field)
        logger.info("[PANDIT-ONBOARDING] Using client active_field: %s (index %d)", client_active_field, state["current_field_index"])
    else:
        sync_next_field_index(state)
        logger.info("[PANDIT-ONBOARDING] Synced next field index to %d -> %s", state["current_field_index"], fields[state["current_field_index"]])

    idx = state["current_field_index"]
    current_field = fields[idx]
    retry_map = state.setdefault("field_retry_count", {})
    
    # ── Achievements loop Haan/Nahi sub-state check ──
    if current_field == "pandit-achievements" and state.get("awaiting_more_achievements"):
        raw_msg = user_params.get("raw_user_message", request.user_message)
        if is_affirmative(raw_msg):
            state["awaiting_more_achievements"] = False
            state["field_retry_count"]["pandit-achievements"] = 0
            question = f"Dhanyawad {fn_ji}! Kripya apni agli upalabdhi (achievement) batayein."
            nav_directive = {"action": None, "target": None, "query": None, "active_field": "pandit-achievements", "intent": "PANDIT_ONBOARDING", "fields": None}
            return orchestrator._response_builder.build_response(
                request_id=request.request_id,
                text_override=question,
                response_type=ResponseType.CHAT,
                navigation_directive=nav_directive,
                metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
            )
        else:
            state["awaiting_more_achievements"] = False
            state["current_field_index"] += 1
            next_idx = state["current_field_index"]
            next_field = fields[next_idx]
            reaction = f"Theek hai {fn_ji}."
            question = f"{reaction} Kripya apne baare mein thoda batayein (Bio), jaise aapki spiritual journey ya visheshta."
            nav_directive = {"action": None, "target": None, "query": None, "active_field": next_field, "intent": "PANDIT_ONBOARDING", "fields": None}
            session.update_location(page="/signup?role=pandit", field=next_field)
            orchestrator._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
            return orchestrator._response_builder.build_response(
                request_id=request.request_id,
                text_override=question,
                response_type=ResponseType.NAVIGATION_DIRECTIVE,
                navigation_directive=nav_directive,
                metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
            )

    # ── Profile Photo (pandit-avatar) special handling ──
    if current_field == "pandit-avatar":
        msg_lower = request.user_message.lower().strip()
        skip_kw = [
            "skip", "aage", "badho", "badh", "aage badho", "next", "continue", "chhod", 
            "baad", "bina", "rehne", "nahi", "no", "leave", "pass", "agla", "chalo", "aage chalo",
            "move", "ahead", "badao", "badhao", "badhe", "badho ji", "badhiye", "aage badhiye",
            "आगे", "बढ़ो", "बढो", "आगे बढ़ो", "आगे बढो", "स्किप", "छोड़ो", "नहीं", "नेक्स्ट", "आगे चलो",
            "बाद", "बिना", "रहने", "अगला", "बढ़ाओ", "चलो", "पास", "आगे बढ़िए", "बढ़िए", "बढिए"
        ]
        is_skip = any(k in msg_lower for k in skip_kw)
        logger.info("[PANDIT-AVATAR-DIAGNOSTIC] msg=%r | is_skip=%s", request.user_message, is_skip)
        
        upload_kw = ["upload", "picture", "photo", "ho gaya", "done", "kar diya", "choose", "selected", "file", "अपलोड", "फोटो", "हो गया"]
        is_upload_intent = any(k in msg_lower for k in upload_kw)
        
        is_file_attached_in_dom = (
            dom_data.get("avatar_attached") == "true" or
            dom_data.get("profilePhotoPreview") or
            dom_data.get("panditAvatar")
        )
        
        if is_skip:
            state["collected_data"]["pandit-avatar"] = "skipped"
            state["current_field_index"] += 1
            next_field = fields[state["current_field_index"]]
            question = f"Koi baat nahi {pji}. Ab apna pehla naam (First Name) bataiye."
            nav_directive = {
                "action": "FILL_FORM",
                "target": "pandit-avatar",
                "query": "skipped",
                "active_field": next_field,
                "intent": "PANDIT_ONBOARDING",
                "fields": None
            }
            session.update_location(page="/signup?role=pandit", field=next_field)
            orchestrator._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
            return orchestrator._response_builder.build_response(
                request_id=request.request_id,
                text_override=question,
                response_type=ResponseType.NAVIGATION_DIRECTIVE,
                navigation_directive=nav_directive,
                metadata=ResponseMetadata(fast_path=True, latency_ms=0.0)
            )
        elif is_upload_intent:
            if is_file_attached_in_dom:
                state["collected_data"]["pandit-avatar"] = "uploaded"
                state["current_field_index"] += 1
                next_field = fields[state["current_field_index"]]
                question = f"Bahut sundar photo! Maine aapki profile photo set kar di hai. Ab apna pehla naam (First Name) bataiye."
                nav_directive = {
                    "action": "FILL_FORM",
                    "target": "pandit-avatar",
                    "query": "uploaded",
                    "active_field": next_field,
                    "intent": "PANDIT_ONBOARDING",
                    "fields": None
                }
                session.update_location(page="/signup?role=pandit", field=next_field)
                orchestrator._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
                return orchestrator._response_builder.build_response(
                    request_id=request.request_id,
                    text_override=question,
                    response_type=ResponseType.NAVIGATION_DIRECTIVE,
                    navigation_directive=nav_directive,
                    metadata=ResponseMetadata(fast_path=True, latency_ms=0.0)
                )
            else:
                # No file selected in DOM! Do NOT advance active_field!
                question = "Mujhe koi photo nahi mili, kya aapne 'Choose Picture' par click karke photo select ki hai? Ya phir 'skip' boliye."
                nav_directive = {
                    "action": None,
                    "target": None,
                    "query": None,
                    "active_field": "pandit-avatar",
                    "intent": "PANDIT_ONBOARDING",
                    "fields": None
                }
                return orchestrator._response_builder.build_response(
                    request_id=request.request_id,
                    text_override=question,
                    response_type=ResponseType.CHAT,
                    navigation_directive=nav_directive,
                    metadata=ResponseMetadata(fast_path=True, latency_ms=0.0)
                )
        else:
            question = f"Namaste! Aap chahein to apni profile photo upload kar sakte hain, ye optional hai. Agar upload karna hai to 'Choose Picture' par click kijiye, nahi to bas 'skip' ya 'aage badho' boliye."
            nav_directive = {"action": None, "target": None, "query": None, "active_field": "pandit-avatar", "intent": "PANDIT_ONBOARDING", "fields": None}
            return orchestrator._response_builder.build_response(
                request_id=request.request_id,
                text_override=question,
                response_type=ResponseType.CHAT,
                navigation_directive=nav_directive,
                metadata=ResponseMetadata(fast_path=True, latency_ms=0.0)
            )

    # Check for manual DOM input value first or voice confirmation ("fill kar diya", "aage badho", "done")
    manual_dom_val = dom_data.get(current_field) or dom_data.get(current_field.replace("pandit-", ""))
    
    if manual_dom_val and str(manual_dom_val).strip():
        logger.info("[PANDIT-ONBOARDING] Found manual DOM value for field %s: %r", current_field, manual_dom_val)
        val = str(manual_dom_val).strip()
    elif is_upload_confirmed(raw_msg):
        logger.info("[PANDIT-ONBOARDING] Voice upload/fill confirmation detected: %r", raw_msg)
        existing_val = state["collected_data"].get(current_field) or manual_dom_val
        val = str(existing_val).strip() if existing_val and str(existing_val).strip() else "Confirmed"
    else:
        llm_start_time = time.time()
        logger.info("[PANDIT-ONBOARDING] Extracting field value via LLM/Regex for active_field: %s | msg: %r", current_field, raw_msg)
        val = await extract_field_value(raw_msg, current_field, ai_service)
        llm_elapsed_ms = int((time.time() - llm_start_time) * 1000)
        logger.info(f"[TIMING-LLM] Field extraction completed in {llm_elapsed_ms}ms | field={current_field} | extracted={val!r}")
    
    is_valid, cleaned_val, err_msg = validate_and_process_field(
        current_field,
        val,
        user_params,
        retry_map
    )

    if not is_valid:
        # Check for navigation intent fallback ONLY after validation fails
        from app.orchestrator.navigation_intent_detector import is_navigation_command, resolve_navigation_target
        if is_navigation_command(request.user_message):
            nav_result = resolve_navigation_target(request.user_message)
            if nav_result["needs_clarification"]:
                return orchestrator._response_builder.build_response(
                    request_id=request.request_id,
                    text_override=nav_result["clarification_msg"],
                    response_type=ResponseType.CHAT,
                    navigation_directive={"action": None, "target": None, "query": None, "active_field": None, "intent": "CLARIFY_NAVIGATION"},
                    metadata=ResponseMetadata(fast_path=True, latency_ms=0.0)
                )
            elif nav_result["target"]:
                target_route = nav_result["target"]
                session.pending_nav_target = target_route
                return orchestrator._response_builder.build_response(
                    request_id=request.request_id,
                    text_override="Aapka form abhi poora nahi hua hai. Kya aap isko chhod kar naye page par jana chahte hain?",
                    response_type=ResponseType.CHAT,
                    navigation_directive={"action": None, "target": None, "query": None, "active_field": None, "intent": "NAVIGATE_CONFIRMATION"},
                    metadata=ResponseMetadata(fast_path=True, latency_ms=0.0)
                )

        nav_directive = {"action": None, "target": None, "query": None, "active_field": current_field, "intent": "PANDIT_ONBOARDING", "fields": None}
        return orchestrator._response_builder.build_response(
            request_id=request.request_id,
            text_override=err_msg,
            response_type=ResponseType.CHAT,
            navigation_directive=nav_directive,
            metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
        )

    val = cleaned_val
    
    # Custom Achievements Collection Logic
    if current_field == "pandit-achievements":
        ach_list = state["collected_data"].get("pandit-achievements", [])
        if not isinstance(ach_list, list):
            ach_list = [ach_list] if ach_list else []
        ach_list.append(val)
        state["collected_data"]["pandit-achievements"] = ach_list
        state["awaiting_more_achievements"] = True
        state["field_retry_count"]["pandit-achievements"] = 0
        
        question = f"Maine aapki upalabdhi add kar li hai. Kya aap koi aur achievement add karna chahte hain? Haan ya Nahi."
        nav_directive = {
            "action": "FILL_FORM",
            "target": "pandit-achievements",
            "query": val,
            "active_field": "pandit-achievements",
            "intent": "PANDIT_ONBOARDING",
            "fields": None
        }
        orchestrator._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
        return orchestrator._response_builder.build_response(
            request_id=request.request_id,
            text_override=question,
            response_type=ResponseType.NAVIGATION_DIRECTIVE,
            navigation_directive=nav_directive,
            metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
        )
        
    # Set tentative field state for confirmation ("Maine suna — [val]. Kya ye sahi hai?")
    old_tentative = state.get("tentative_value", "")
    logger.info(f"[TENTATIVE] old='{old_tentative}' new='{val}'")
    state["tentative_field"] = current_field
    state["tentative_value"] = val
    state["status"] = "awaiting_field_confirmation"

    disp_val = format_value_for_display(val)
    question = f"Maine suna — {disp_val}. Kya ye sahi hai?"
    nav_directive = {
        "action": "FILL_FORM",
        "target": current_field,
        "query": val,
        "active_field": current_field,
        "intent": "PANDIT_ONBOARDING",
        "fields": None
    }
    orchestrator._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
    return orchestrator._response_builder.build_response(
        request_id=request.request_id,
        text_override=question,
        response_type=ResponseType.NAVIGATION_DIRECTIVE,
        navigation_directive=nav_directive,
        metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
    )


    # ── SPECIAL HANDLING FOR CITY -> STATE AUTO DERIVATION / CLARIFICATION ──
    if current_field == "pandit-city":
        match_type, state_res = get_state_for_city(val)
        logger.info("[PANDIT-ONBOARDING] City-State lookup for %r -> match_type: %s, res: %r", val, match_type, state_res)
        
        if match_type == "SINGLE":
            state["collected_data"]["pandit-state"] = state_res
            state["current_field_index"] += 2
            next_idx = state["current_field_index"]
            next_field = fields[next_idx] if next_idx < len(fields) else "pandit-service-areas"
            
            reaction = get_contextual_reaction(current_field, val, address_info)
            question = f"{reaction} Aap kin service areas mein puja karwane ke liye uplabdh hain? Jaise Delhi NCR, Online Puja, ya Mumbai?"
            
            nav_directive = {
                "action": "FILL_FORM",
                "target": current_field,
                "query": val,
                "active_field": next_field,
                "intent": "PANDIT_ONBOARDING",
                "fields": [
                    {"target": "pandit-city", "query": val},
                    {"target": "pandit-state", "query": state_res}
                ]
            }
            orchestrator._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
            return orchestrator._response_builder.build_response(
                request_id=request.request_id,
                text_override=question,
                response_type=ResponseType.NAVIGATION_DIRECTIVE,
                navigation_directive=nav_directive,
                metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
            )
        elif match_type == "AMBIGUOUS":
            state["status"] = "awaiting_city_state_clarification"
            state["ambiguous_city"] = val
            state["possible_states"] = state_res
            primary_state = state_res[0]
            
            question = f"{val} naam ke kai jagah hain, kya aap {primary_state} wale {val} ki baat kar rahe hain?"
            nav_directive = {
                "action": "FILL_FORM",
                "target": "pandit-city",
                "query": val,
                "active_field": "pandit-city",
                "intent": "PANDIT_ONBOARDING",
                "fields": None
            }
            orchestrator._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
            return orchestrator._response_builder.build_response(
                request_id=request.request_id,
                text_override=question,
                response_type=ResponseType.NAVIGATION_DIRECTIVE,
                navigation_directive=nav_directive,
                metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
            )
        else:
            logger.info("[PANDIT-ONBOARDING] City %r not in dataset. Falling back to asking state.", val)
            state["current_field_index"] += 1
            next_idx = state["current_field_index"]
            next_field = fields[next_idx]
            reaction = get_contextual_reaction(current_field, val, address_info)
            question = f"{reaction} Kripya apna state ya rajya bataiye."
            nav_directive = {
                "action": "FILL_FORM",
                "target": current_field,
                "query": val,
                "active_field": next_field,
                "intent": "PANDIT_ONBOARDING",
                "fields": None
            }
            orchestrator._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
            return orchestrator._response_builder.build_response(
                request_id=request.request_id,
                text_override=question,
                response_type=ResponseType.NAVIGATION_DIRECTIVE,
                navigation_directive=nav_directive,
                metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
            )

    next_idx = sync_next_field_index(state)
    logger.info(f"[PANDIT-ONBOARDING] Deterministic sync_next_field_index -> {next_idx} (next missing field)")
    
    # ── Transition to Step 2 Summary Confirmation ──
    cert_file_idx = fields.index("pandit-certFile")
    if next_idx == cert_file_idx:
        next_field = None
        state["status"] = "awaiting_confirmation"
        question = generate_summary_text(first_name, state["collected_data"], address_info)
        logger.info("[PANDIT-ONBOARDING] STEP 2 COMPLETE | Transitioning to awaiting_confirmation state.")
    elif next_idx < len(fields):
        next_field = fields[next_idx]
        session.update_location(page="/signup?role=pandit", field=next_field)
        reaction = get_contextual_reaction(current_field, str(val), address_info)
        
        question_variations = {
            "pandit-first-name": [f"Panditji, aapka first name kya hai?"],
            "pandit-last-name": [f"{reaction} Aapka last name kya hai?"],
            "pandit-email": [f"{reaction} Aapka email address kya hai?"],
            "pandit-phone": [f"{reaction} Aapka 10-digit mobile number bataiye."],
            "pandit-gender": [f"{reaction} Aapka gender kya hai? Options: Male, Female, ya Other."],
            "pandit-availability": [f"{reaction} Aapki availability mode kya hai? Offline, Online, ya Both?"],
            "pandit-city": [f"{reaction} Aap kis city mein rehte hain? Jaise Varanasi, Haridwar, ya Delhi."],
            "pandit-state": [f"{reaction} Aap kis state se hain?"],
            "pandit-service-areas": [f"{reaction} Aap kin service areas mein puja ke liye available hain?"],
            "pandit-exp": [f"{reaction} Aapka puja aur karmakand mein kitne saal ka experience hai?"],
            "pandit-gurukul": [f"{reaction} Aapka educational background ya Gurukul kaunsa hai?"],
            "pandit-languages": [f"{reaction} Hum default Hindi aur Sanskrit add kar rahe hain. Koi aur language add karni hai?"],
            "pandit-spec": [f"{reaction} Aapki primary specialization kaunsi hai? Options: Vedic Pujas & Havan, Jyotish & Kundali, Sanskar Ceremonies, ya Katha & Pravachan."],
            "pandit-achievements": [f"{reaction} Aapki koi main achievement hai toh bataiye."],
            "pandit-bio": [f"{reaction} Apne baare mein thoda bataiye (Bio)."],
            "pandit-certFile": [f"Ab documents upload karte hain. Screen par Certificate upload kijiye aur 'ho gaya' boliye."],
            "pandit-aadhaarFile": [f"Ab Aadhaar card ya ID proof upload kijiye, aur 'ho gaya' boliye."],
            "pandit-galleryFiles": [f"Gallery ke liye photos ya videos upload kijiye, aur 'ho gaya' boliye."],
            "pandit-password": [f"Security ke liye screen par password set kijiye, aur 'ho gaya' boliye."],
            "pandit-confirm": [f"Confirm password enter kijiye aur 'submit kar do' boliye."]
        }

        opts = question_variations.get(next_field, [f"{reaction} Ab apna {next_field} bataiye."])
        question = random.choice(opts)
    else:
        # All Step 3 fields completed! Trigger submission directly!
        session.onboarding_state = None
        text = f"Bahut badhiya {pji}! Main abhi aapka registration submit kar raha hoon."
        nav_directive = {
            "action": "SUBMIT_FORM",
            "target": "[data-testid='button-submit-pandit-signup']",
            "intent": "PANDIT_ONBOARDING",
            "fields": None
        }
        orchestrator._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
        return orchestrator._response_builder.build_response(
            request_id=request.request_id,
            text_override=text,
            response_type=ResponseType.NAVIGATION_DIRECTIVE,
            navigation_directive=nav_directive,
            metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
        )
        
    query_val = str(val)
    if isinstance(val, list):
        query_val = ", ".join(val)
        
    nav_directive = {
        "action": "FILL_FORM",
        "target": current_field,
        "query": query_val,
        "active_field": next_field,
        "intent": "PANDIT_ONBOARDING",
        "fields": None
    }
    orchestrator._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
    
    return orchestrator._response_builder.build_response(
        request_id=request.request_id,
        text_override=question,
        response_type=ResponseType.NAVIGATION_DIRECTIVE,
        navigation_directive=nav_directive,
        metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
    )
