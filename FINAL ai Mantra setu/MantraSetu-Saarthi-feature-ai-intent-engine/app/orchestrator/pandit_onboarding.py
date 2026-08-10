import logging
import random
import re
from typing import Any
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
        return f"Shukriya {sn_ji}!"

    if current_field == "pandit-email":
        return f"Bahut badhiya {pji}!"

    return f"Bahut sundar {fn_ji}!"

def generate_summary_text(first_name: str, collected_data: dict, address_info: dict = None) -> str:
    """Generate the end-of-flow voice confirmation summary text."""
    name_val = collected_data.get("pandit-name", "Panditji")
    phone_val = collected_data.get("pandit-phone", "Not provided")
    email_val = collected_data.get("pandit-email", "Not provided")
    city_val = collected_data.get("pandit-city", "Not provided")
    state_val = collected_data.get("pandit-state", "Not provided")
    exp_val = collected_data.get("pandit-exp", "Not provided")
    spec_val = collected_data.get("pandit-spec", "Not provided")
    
    address_label = address_info.get("first_name_ji", f"{first_name} ji") if address_info else f"{first_name} ji"
    
    return (
        f"{address_label}, chaliye ek baar confirm kar lete hain — aapka naam {name_val} hai, "
        f"mobile number {phone_val}, email {email_val}, city {city_val}, state {state_val}, "
        f"experience {exp_val}, aur specialization {spec_val} hai. Kya yeh sab sahi hai?"
    )

def is_affirmative(user_message: str) -> bool:
    """Check if the user is confirming the summary."""
    msg_lower = user_message.lower().strip()
    affirmative_keywords = [
        "haan", "yes", "sahi", "theek", "okay", "ok", "correct", "confirm", 
        "bilkul", "sab sahi", "ha", "aage badho", "perfect", "done", "everything is correct",
        "हाँ", "हां", "जी", "जी हां", "जी हाँ", "सही", "ठीक", "सब सही", "सब ठीक",
        "आगे बढ़ो", "बढ़िया", "सब सही है", "सही है", "ठीक है", "हां सब सही है", "हाँ सब सही है"
    ]
    negative_keywords = [
        "nahi", "galat", "no", "change", "wrong", "badlo", "dobara", "correction",
        "नहीं", "नही", "गलत", "बदलो", "दुरुस्त", "सुधार", "चेंज"
    ]
    
    has_aff = any(w in msg_lower for w in affirmative_keywords)
    has_neg = any(w in msg_lower for w in negative_keywords)
    res = has_aff and not has_neg
    logger.info("[PANDIT-CONFIRM-DIAGNOSTIC] is_affirmative msg=%r -> has_aff=%s, has_neg=%s, result=%s", user_message, has_aff, has_neg, res)
    print(f"[PANDIT-CONFIRM-DIAGNOSTIC] is_affirmative msg={user_message!r} -> has_aff={has_aff}, has_neg={has_neg}, result={res}")
    return res

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

        # 1. Transliterate Devanagari Hindi phonetic letters to English ASCII
        devanagari_phrases = [
            (r'(एट द रेट|ऍट द रेट|एट rate|एट-द-रेट|ऐट)', '@'),
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
        text = re.sub(r'\b(at the rate of|at the rate|at rate of|at rate|at-the-rate)\b', '@', text, flags=re.IGNORECASE)
        text = re.sub(r'(एट द रेट|ऍट द रेट|एट rate|एट-द-रेट|ऐट)', '@', text)
        text = re.sub(r'(?<=\w)\s+at\s+(?=\w+)', '@', text, flags=re.IGNORECASE)
        
        # 3. Spoken . symbols in English & Hindi Devanagari
        text = re.sub(r'\b(dot|point)\b', '.', text, flags=re.IGNORECASE)
        text = re.sub(r'(डॉट|डाट|बिंदु)', '.', text)
        
        # 4. Spoken dash & underscore
        text = re.sub(r'\b(dash|hyphen|डैश)\b', '-', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(underscore|अंडरस्कोर)\b', '_', text, flags=re.IGNORECASE)
        
        # 5. Fix common domain mishearings & spaced letters
        text = re.sub(r'\b(g mail|g-mail|jimmail|जीमेल|जी मेल|g m a i l|g m a a l)\b', 'gmail', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(yaho|याहू|y a h o o)\b', 'yahoo', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(c o m|कॉम)\b', 'com', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(i n|इन)\b', 'in', text, flags=re.IGNORECASE)
        
        # 6. Auto-insert missing '@' if a known domain is present without '@'
        if '@' not in text:
            text = re.sub(r'(?<=\w)\s+(?=(gmail|yahoo|outlook|hotmail|icloud)\.(com|in|co\.in|org|net))\b', '@', text, flags=re.IGNORECASE)

        # 7. Collapse ALL whitespace inside email strings e.g. "a g h a v 63984 @ g m a i l . c o m" -> "aghav63984@gmail.com"
        text = re.sub(r'\s+', '', text)
        
        # 8. Extract clean email address if matched
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', text)
        if email_match:
            text = email_match.group(0)
            
    elif field in ["pandit-phone", "phone"]:
        # 1. Convert Devanagari digits to ASCII
        devanagari_digits = str.maketrans("०१२३४५६७८९", "0123456789")
        text = text.translate(devanagari_digits)
        
        # 2. Map spoken Hindi words (Devanagari) to digits
        hindi_digit_map = {
            "शून्य": "0", "जीरो": "0", "एक": "1", "दो": "2", "तीन": "3", "चार": "4",
            "पांच": "5", "पाँच": "5", "छह": "6", "छः": "6", "सात": "7", "आठ": "8", "नौ": "9"
        }
        for word, digit in hindi_digit_map.items():
            text = text.replace(word, digit)

        # 3. Map spoken Hindi words in Roman script & English words to digits
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
            
        # 4. Extract digits only and strip spaces
        digits_only = re.sub(r'\D', '', text)
        
        # 5. Strip country codes +91, 91, or leading 0 if 11 or 12 digits
        if len(digits_only) == 11 and digits_only.startswith('0'):
            digits_only = digits_only[1:]
        elif len(digits_only) == 12 and digits_only.startswith('91'):
            digits_only = digits_only[2:]
            
        # 6. Find 10-digit Indian mobile number starting with 5-9
        phone_match = re.search(r'[56789]\d{9}', digits_only)
        if phone_match:
            text = phone_match.group(0)
        elif len(digits_only) == 10:
            text = digits_only
        else:
            text = digits_only
            
    return text

async def extract_field_value(user_message: str, field: str, ai_service: AIService) -> str:
    """Extract a clean field value from user response using the LLM.
    
    If the response is ambiguous, off-topic, or not a valid answer for the field, returns "INVALID".
    """
    user_message_normalized = normalize_spoken_input(user_message, field)
    logger.info("[PANDIT-ONBOARDING] extract_field_value | field: %s | raw: %r | normalized: %r", field, user_message, user_message_normalized)

    field_descs = {
        "pandit-name": "Full Name of the Pandit (person name, e.g. Ramesh Sharma, Sunil, etc.)",
        "pandit-phone": "Mobile number or phone number (10-digit number, e.g. 9876543210, etc.)",
        "pandit-email": "Email address (e.g. sharma@gmail.com, ramesh@yahoo.co.in, etc.)",
        "pandit-city": "Indian city of residence (e.g. Varanasi, Delhi, Mumbai, etc.)",
        "pandit-state": "Indian state of residence (e.g. Uttar Pradesh, Maharashtra, Delhi, etc.)",
        "pandit-lang": "Languages spoken for rituals (choices: Hindi, Sanskrit, English, Gujarati, Marathi, Bengali, Tamil, Telugu). Default is 'Hindi, Sanskrit'.",
        "pandit-exp": "Years of experience. Must match one of these EXACT choices: '1-5 years', '5-10 years', '10-20 years', '20+ years'",
        "pandit-spec": "Primary specialization. Must match one of these EXACT choices: 'Vedic Pujas & Havan', 'Jyotish & Kundali', 'Sanskar Ceremonies', 'Katha & Pravachan'"
    }
    field_desc = field_descs.get(field, field)

    # Deterministic Fast-Path for Phone and Email (0ms Latency & 100% Deterministic Reliability)
    if field in ["pandit-phone", "phone"]:
        digits_only = re.sub(r'\D', '', user_message_normalized)
        if len(digits_only) == 11 and digits_only.startswith('0'):
            digits_only = digits_only[1:]
        elif len(digits_only) == 12 and digits_only.startswith('91'):
            digits_only = digits_only[2:]
            
        phone_match = re.search(r'[56789]\d{9}', digits_only)
        if phone_match:
            phone_val = phone_match.group(0)
            logger.info("[PANDIT-ONBOARDING] Deterministic regex hit for pandit-phone: %s", phone_val)
            return phone_val
        elif len(digits_only) == 10:
            logger.info("[PANDIT-ONBOARDING] Deterministic regex hit for pandit-phone: %s", digits_only)
            return digits_only
            
    if field in ["pandit-email", "email"]:
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', user_message_normalized)
        if email_match:
            extracted_email = email_match.group(0)
            logger.info("[PANDIT-ONBOARDING] Deterministic regex hit for pandit-email: %s", extracted_email)
            return extracted_email

    system_prompt = f"""You are an expert data extraction assistant.
The user is providing an answer for the field '{field}' ({field_desc}) in a Pandit registration form.
Your task is to extract ONLY the clean, structured value for this field in Roman/English script.

STRICT VALIDATION RULES:
1. The user's response MUST contain a valid, reasonable answer for the field '{field}'.
2. If the field is 'pandit-email':
   - Extract a valid email address string (e.g. 'sharma@gmail.com', 'ramesh@yahoo.co.in').
   - Convert spoken representations like 'at the rate', 'at rate', 'at', 'dot', 'dash' into proper email syntax ('@', '.', '-').
   - Collapse spaces inside email addresses (e.g. 'r a m e s h @ g m a i l . c o m' -> 'ramesh@gmail.com').
3. If the field is 'pandit-phone':
   - Extract a 10-digit phone number string (e.g. '9876543210').
   - Remove any spaces, hyphens, or non-digit characters.
4. If the field is 'pandit-exp', you MUST map the user's spoken answer to one of these exact values: '1-5 years', '5-10 years', '10-20 years', '20+ years'. If they say "das saal" or "six years", map to '10-20 years' or '5-10 years' respectively. If not clear or off-topic, return 'INVALID'.
5. If the field is 'pandit-spec', you MUST map the user's spoken answer to one of these exact values: 'Vedic Pujas & Havan', 'Jyotish & Kundali', 'Sanskar Ceremonies', 'Katha & Pravachan'. For example, if they say "havan" or "pujas", map to 'Vedic Pujas & Havan'. If they say "jyotish" or "kundali", map to 'Jyotish & Kundali'. If not clear or off-topic, return 'INVALID'.
6. If the field is 'pandit-lang':
   - If the user agrees, says 'sahi hai', 'theek hai', 'okay', 'yes', 'agreed', 'continue', or approves defaults, return 'Hindi, Sanskrit'.
   - If they mention additional or specific languages (e.g. 'Gujarati bhi add karo', 'sirf Hindi'), extract the final active comma-separated list from choices [Hindi, Sanskrit, English, Gujarati, Marathi, Bengali, Tamil, Telugu]. Default is 'Hindi, Sanskrit'.
7. If the user's response is off-topic, ambiguous, completely unrelated, or says something like "cancel", "ruko", "mujhe nahi pata" etc., you MUST return exactly the word 'INVALID'. Do not try to extract or make up a value.
8. If the answer is completely gibberish or not valid for {field_desc}, return 'INVALID'.

Return ONLY the extracted clean value (or 'INVALID'). Do NOT include any explanations, greetings, or extra words.
"""

    llm_req = LLMRequest(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message_normalized}
        ],
        temperature=0.0,
    )
    
    try:
        response = await ai_service.generate(request=llm_req)
        val = response.content.strip().replace('"', '').replace("'", "")
        logger.info("[PANDIT-ONBOARDING] LLM extraction result for %s: %s", field, val)
        return val
    except Exception as e:
        logger.error("[PANDIT-ONBOARDING] LLM extraction failed", exc_info=True)
        return "INVALID"

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
    full_name = state["collected_data"].get("pandit-name", "Panditji")
    address_info = get_address_forms(full_name)
    first_name = address_info["first_name"]
    fn_ji = address_info["first_name_ji"]
    sn_ji = address_info["surname_ji"]
    pji = address_info["panditji"]

    field_hinglish_names = {
        "pandit-name": "naam",
        "pandit-phone": "mobile number",
        "pandit-email": "email address",
        "pandit-city": "sheher",
        "pandit-state": "state",
        "pandit-exp": "experience",
        "pandit-spec": "specialization",
        "pandit-lang": "languages"
    }

    # -------------------------------------------------------------------------
    # CASE 1: Awaiting Confirmation Summary Response
    # -------------------------------------------------------------------------
    if status == "awaiting_confirmation":
        logger.info("[PANDIT-ONBOARDING] AWAITING CONFIRMATION turn | user_msg: %r", request.user_message)
        if is_affirmative(request.user_message):
            logger.info("[PANDIT-ONBOARDING] Summary CONFIRMED by user. Transitioning to awaiting_final_submission state.")
            state["status"] = "awaiting_final_submission"
            question = (
                f"Bahut badhiya {sn_ji}! Maine aapki saari jaankari confirm kar li hai aur form mein bhar di hai. "
                f"Bas ab aapko sirf apna password banana hai aur apne documents upload karne hain — yeh aapko khud karna hoga. "
                f"Jab aap yeh kar lein, toh mujhe 'maine kar diya hai' ya 'submit kar do' boliye, main form submit kar doonga!"
            )
            nav_directive = {"action": None, "target": None, "query": None, "intent": "PANDIT_ONBOARDING", "fields": None}
            return orchestrator._response_builder.build_response(
                request_id=request.request_id,
                text_override=question,
                response_type=ResponseType.CHAT,
                navigation_directive=nav_directive,
                metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
            )
        else:
            # User wants to correct a field!
            target_field = await detect_correction_field(request.user_message, ai_service)
            logger.info("[PANDIT-ONBOARDING] Field correction requested for: %s", target_field)
            state["status"] = "correcting_field"
            state["correcting_field_name"] = target_field
            hinglish_name = field_hinglish_names.get(target_field, "jankari")
            question = f"Kshama karein {fn_ji}! Kripya apna naya {hinglish_name} bataiye."
            nav_directive = {"action": None, "target": None, "query": None, "intent": "PANDIT_ONBOARDING", "fields": None}
            return orchestrator._response_builder.build_response(
                request_id=request.request_id,
                text_override=question,
                response_type=ResponseType.CHAT,
                navigation_directive=nav_directive,
                metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
            )

    # -------------------------------------------------------------------------
    # CASE 1B: Awaiting Final Submission (User completed password/docs)
    # -------------------------------------------------------------------------
    if status == "awaiting_final_submission":
        logger.info("[PANDIT-ONBOARDING] AWAITING FINAL SUBMISSION turn | user_msg: %r", request.user_message)
        msg_lower = request.user_message.lower()
        submit_triggers = [
            "kar diya", "bana diya", "upload kar diya", "ho gaya", "submit", "done", 
            "complete", "taiyaar", "ready", "hogaya", "kardia", "kardiya",
            "कर दिया", "हो गया", "सबमिट", "बना दिया", "अपलोड कर दिए", "तैयार"
        ]
        is_ready = any(t in msg_lower for t in submit_triggers) or is_affirmative(request.user_message)

        if is_ready:
            logger.info("[PANDIT-ONBOARDING] User confirmed readiness for submission. Triggering SUBMIT_FORM action.")
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
        else:
            logger.info("[PANDIT-ONBOARDING] User in awaiting_final_submission but msg not recognized: %r", request.user_message)
            text = f"Panditji, kripya apna password set karke aur documents upload karke 'maine kar diya hai' boliye, taaki main form submit kar sakoon."
            nav_directive = {"action": None, "target": None, "query": None, "intent": "PANDIT_ONBOARDING", "fields": None}
            return orchestrator._response_builder.build_response(
                request_id=request.request_id,
                text_override=text,
                response_type=ResponseType.CHAT,
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
        
        if val == "INVALID" or not val.strip():
            logger.info("[PANDIT-ONBOARDING] Field correction failed for %s. Re-asking.", target_field)
            hinglish_name = field_hinglish_names.get(target_field, "jankari")
            question = f"Maaf kijiye {fn_ji}, main samajh nahi paya. Kripya apna naya {hinglish_name} dobara bataiye."
            nav_directive = {"action": None, "target": None, "query": None, "intent": "PANDIT_ONBOARDING", "fields": None}
            return orchestrator._response_builder.build_response(
                request_id=request.request_id,
                text_override=question,
                response_type=ResponseType.CHAT,
                navigation_directive=nav_directive,
                metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
            )
            
        # Store corrected value
        state["collected_data"][target_field] = val
        full_name = state["collected_data"].get("pandit-name", "Panditji")
        address_info = get_address_forms(full_name)
        first_name = address_info["first_name"]
            
        logger.info("[PANDIT-ONBOARDING] Field %s corrected to: %r. Returning to confirmation summary.", target_field, val)
        state["status"] = "awaiting_confirmation"
        state["correcting_field_name"] = None
        
        hinglish_name = field_hinglish_names.get(target_field, "jankari")
        summary_body = generate_summary_text(first_name, state["collected_data"], address_info)
        question = f"Dhanyawad {address_info['surname_ji']}! Maine {hinglish_name} update kar diya hai. {summary_body}"
        
        nav_directive = {
            "action": "FILL_FORM",
            "target": target_field,
            "query": val,
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
    idx = state["current_field_index"]
    current_field = fields[idx]
    
    raw_msg = request.user_parameters.get("raw_user_message", request.user_message) if isinstance(request.user_parameters, dict) else request.user_message
    val = await extract_field_value(raw_msg, current_field, ai_service)
    
    if val == "INVALID" or not val.strip():
        logger.info("[PANDIT-ONBOARDING] STEP FAILED | Extraction returned INVALID for field: %s. Re-asking same field.", current_field)
        
        if current_field == "pandit-phone":
            digits_part = re.sub(r'\D', '', normalize_spoken_input(raw_msg, "pandit-phone"))
            if digits_part:
                question = f"Maine suna: '{digits_part}', lekin mobile number 10 digits ka hona chahiye. Kripya apna 10-digit mobile number dobara bataiye."
            else:
                question = f"Maaf kijiye {fn_ji}, main mobile number samajh nahi paya. Kripya apna 10-digit mobile number dobara bataiye."
        elif current_field == "pandit-email":
            email_part = normalize_spoken_input(raw_msg, "pandit-email")
            if email_part and email_part != raw_msg:
                question = f"Maine suna: '{email_part}', kripya apna poora email address (jaise name@gmail.com) dobara bataiye."
            else:
                question = f"Maaf kijiye {sn_ji}, main email address samajh nahi paya. Kripya apna email address (jaise ramesh@gmail.com) dobara bataiye."
        else:
            fallback_prompts = {
                "pandit-name": "Maaf kijiye, main samajh nahi paya. Kripya apna poora naam dobara bataiye.",
                "pandit-city": f"Maaf kijiye {pji}, main samajh nahi paya. Kripya apna sheher dobara bataiye.",
                "pandit-state": f"Maaf kijiye {fn_ji}, main samajh nahi paya. Kripya apna state ya rajya dobara bataiye.",
                "pandit-lang": f"Maaf kijiye {sn_ji}, samajh nahi paya. Kripya bataiye kya Hindi aur Sanskrit sahi hai ya koi aur bhasha add karni hai?",
                "pandit-exp": f"Maaf kijiye {pji}, samajh nahi paya. Aapka experience kitna hai? Options hain: 1-5 years, 5-10 years, 10-20 years, ya 20+ years.",
                "pandit-spec": f"Maaf kijiye {fn_ji}, samajh nahi paya. Aapki primary specialization kaunsi hai? Options hain: Vedic Pujas & Havan, Jyotish & Kundali, Sanskar Ceremonies, ya Katha & Pravachan."
            }
            question = fallback_prompts.get(current_field, f"Maaf kijiye {fn_ji}, samajh nahi paya. Dobara bataiye.")
        
        nav_directive = {"action": None, "target": None, "query": None, "intent": "PANDIT_ONBOARDING", "fields": None}
        return orchestrator._response_builder.build_response(
            request_id=request.request_id,
            text_override=question,
            response_type=ResponseType.CHAT,
            navigation_directive=nav_directive,
            metadata=ResponseMetadata(fast_path=False, latency_ms=0.0)
        )
        
    state["collected_data"][current_field] = val
    if current_field == "pandit-name":
        full_name = val
        address_info = get_address_forms(full_name)
        first_name = address_info["first_name"]
        fn_ji = address_info["first_name_ji"]
        sn_ji = address_info["surname_ji"]
        pji = address_info["panditji"]

    state["current_field_index"] += 1
    next_idx = state["current_field_index"]
    
    if next_idx < len(fields):
        next_field = fields[next_idx]
        reaction = get_contextual_reaction(current_field, val, address_info)
        
        question_variations = {
            "pandit-phone": [
                f"{reaction} Ab apna mobile number bataiye.",
                f"{reaction} Kripya apna mobile number share karein.",
                f"{reaction} Ab aapka mobile number kya hai?"
            ],
            "pandit-email": [
                f"{reaction} Ab apna email address bataiye.",
                f"{reaction} Kripya apna email address share karein.",
                f"{reaction} Ab aapka email address bataiye."
            ],
            "pandit-city": [
                f"{reaction} Aap kis sheher se hain?",
                f"{reaction} Aapka sheher kaunsa hai?",
                f"{reaction} Aap kis city se belong karte hain?"
            ],
            "pandit-state": [
                f"{reaction} Aapka state ya rajya kaunsa hai?",
                f"{reaction} Kripya apna state ya rajya bataiye.",
                f"{reaction} Aap kis state se hain?"
            ],
            "pandit-exp": [
                f"{reaction} Aapka kitne saal ka experience hai? Options hain: 1-5 years, 5-10 years, 10-20 years, ya 20+ years.",
                f"{reaction} Aapko puja aur karmakand mein kitna experience ya anubhav hai? Options: 1-5 years, 5-10 years, 10-20 years, ya 20+ years."
            ],
            "pandit-spec": [
                f"{reaction} Aapki primary specialization kaunsi hai? Options hain: Vedic Pujas & Havan, Jyotish & Kundali, Sanskar Ceremonies, ya Katha & Pravachan.",
                f"{reaction} Aapki mukhya visheshagyata kis mein hai? Options: Vedic Pujas & Havan, Jyotish & Kundali, Sanskar Ceremonies, ya Katha & Pravachan."
            ],
            "pandit-lang": [
                f"{reaction} Hum default roop se Hindi aur Sanskrit language add kar rahe hain, kyunki zyada tar Pandit ji inhi bhashaon mein seva dete hain. Agar aapko koi aur bhasha badalni ya add karni ho, toh mujhe bataiye, ya 'sahi hai' boliye."
            ]
        }
        opts = question_variations.get(next_field, [f"{reaction} Ab apna {next_field} bataiye."])
        question = random.choice(opts)
    else:
        # All 8 fields collected! Set status to awaiting_confirmation & render summary!
        state["status"] = "awaiting_confirmation"
        question = generate_summary_text(first_name, state["collected_data"], address_info)
        logger.info("[PANDIT-ONBOARDING] ALL 8 FIELDS COLLECTED | Transitioning to awaiting_confirmation state.")
        
    nav_directive = {
        "action": "FILL_FORM",
        "target": current_field,
        "query": val,
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
