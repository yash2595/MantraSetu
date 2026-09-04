import logging
import re
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def extract_dob(msg: str) -> Optional[str]:
    """Extract date of birth from user message."""
    if not msg:
        return None
    # 1. Standard numeric formats: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    date_patterns = [
        r'\b\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\b',
        r'\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, msg)
        if match:
            return match.group(0)

    # 2. Textual month formats: 15 August 1995, 15th Aug 1995, August 15 1995
    months = r'(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
    text_patterns = [
        rf'\b\d{{1,2}}(?:st|nd|rd|th)?\s+{months}(?:\s+\d{{2,4}})?\b',
        rf'\b{months}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:\s+\d{{2,4}})?\b',
    ]
    for pattern in text_patterns:
        match = re.search(pattern, msg, re.IGNORECASE)
        if match:
            return match.group(0)

    return None

_MUHURAT_EVENTS = [
    ("griha pravesh", "Griha Pravesh"),
    ("grihapravesh", "Griha Pravesh"),
    ("ghar pravesh", "Griha Pravesh"),
    ("housewarming", "Griha Pravesh"),
    ("makaan", "Griha Pravesh"),
    ("nayi dukan", "Business Opening"),
    ("shaadi", "Vivah"),
    ("shadi", "Vivah"),
    ("vivah", "Vivah"),
    ("wedding", "Vivah"),
    ("marriage", "Vivah"),
    ("naamkaran", "Naamkaran"),
    ("namkaran", "Naamkaran"),
    ("naming", "Naamkaran"),
    ("naam karan", "Naamkaran"),
    ("mundan", "Mundan"),
    ("business", "Business Opening"),
    ("vyapar", "Business Opening"),
    ("shop", "Business Opening"),
    ("office", "Business Opening"),
    ("vehicle", "Vehicle Purchase"),
    ("gadi", "Vehicle Purchase"),
    ("car", "Vehicle Purchase"),
    ("property", "Property Purchase"),
    ("zameen", "Property Purchase"),
    ("sagai", "Engagement"),
    ("engagement", "Engagement"),
    ("janeu", "Janeu Sanskar"),
    ("upanayana", "Janeu Sanskar"),
]

def extract_muhurat_event(msg: str) -> Optional[str]:
    """Extract Muhurat event type from user message."""
    if not msg:
        return None
    msg_lower = msg.lower()
    for kw, val in _MUHURAT_EVENTS:
        if kw in msg_lower:
            return val
    return None

# Basic routing keywords mapping
_NAV_KEYWORDS = {
    "/": ["home", "main page", "shuruat", "wapas jao", "home page", "homepage", "mukhya prishth", "मुख्य पृष्ठ"],
    "/kundali-creation": ["kundali", "janam patri", "patrika", "birth chart", "kundli", "kundali creation", "kundali banao", "kundli creation", "कुंडली"],
    "/puja": ["puja", "pooja", "pandit book", "pandit bulao", "book pandit", "puja booking", "pooja booking", "पूजा"],
    "/muhurat-finder": ["muhurat", "shubh samay", "auspicious time", "shubh muhurat", "muhurth", "muhurat finder", "मुहूर्त"],
    "/login?role=pandit": ["pandit login", "panditji login", "login as pandit", "login as a pandit", "pandit pehle se", "pandit sign in", "पंडित लॉगिन"],
    "/login": ["login", "sign in", "andar aao", "log in", "login page", "लॉगिन"],
    "/dashboard": ["dashboard", "mera profile", "meri jankari", "meri jaankari", "meri details", "डैशबोर्ड"],
    "/profile": ["profile", "meri profile"],
    "/about": ["about us", "hamare bare mein", "aapke bare mein"],
    "/contact": ["contact", "sampark", "call karo", "help", "madad", "संपर्क"],
    # Signups
    "/signup?role=pandit": [
        "pandit banna", "pandit banne", "pandit registration", "pandit sign up", "pandit signup", "pandit join",
        "join as pandit", "register as pandit", "register as a pandit", "panditji register", "pandit account",
        "pandit onboarding", "pandit onboard", "pandit kaise", "onboarding page", "pandit page", "pandit ji banna",
        "onboarding start", "onboarding shuru", "onboard karo", "onboarding karo", "onboarding pe", "onboarding par",
        "onboarding", "onboard", "pandit ke roop mein register", "pandit ke roop mein", "pandit ke liye register",
        "पंडित बनना", "पंडित रजिस्ट्रेशन", "पंडित के रूप में रजिस्टर", "पंडित के रूप में जुड़ना"
    ],
    "/signup": [
        "devotee banna", "bhakt banna", "devotee sign up", "devotee registration", "register as devotee",
        "devotee signup", "devotee join", "open signup", "signup page", "sign up page", "registration page",
        "signup dikhao", "sign up dikhao", "साइन अप पेज", "रजिस्ट्रेशन पेज"
    ]
}

# Ambiguous cases
_AMBIGUOUS_KEYWORDS = {
    "signup_ambiguous": ["signup", "sign up", "register", "registration", "naya account", "new account", "khata kholo", "judna chahta"]
}

def is_navigation_command(msg: str) -> bool:
    """Check if the user is trying to navigate to another page."""
    if not msg:
        return False
        
    msg_lower = msg.lower()
    
    # Exclude false positives (like "refresh page" or "kaunsa page" or RAG queries)
    if "refresh" in msg_lower or "reload" in msg_lower or "kaunsa" in msg_lower or "jankari" in msg_lower or "samagri" in msg_lower:
        # Let these be handled by location_query, refresh, or RAG logic unless navigation intent is explicit
        if not ("kundali" in msg_lower or "puja" in msg_lower or "pandit" in msg_lower or "onboard" in msg_lower or "signup" in msg_lower or "sign up" in msg_lower):
            return False
        # If it's explicitly asking for info (RAG), don't treat it as navigation
        if "jankari" in msg_lower or "samagri" in msg_lower:
            return False
            
    # Check unambiguous targets
    for target, keywords in _NAV_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            return True
            
    # Check ambiguous targets
    for kw in _AMBIGUOUS_KEYWORDS["signup_ambiguous"]:
        if kw in msg_lower:
            return True
            
    return False

def resolve_navigation_target(msg: str) -> dict:
    """Resolve the exact target or return a clarification message."""
    if not msg:
        return {"target": None, "needs_clarification": False}
        
    msg_lower = msg.lower()
    
    # Multi-intent check (e.g. both puja and kundali)
    has_puja = any(kw in msg_lower for kw in _NAV_KEYWORDS["/puja"])
    has_kundali = any(kw in msg_lower for kw in _NAV_KEYWORDS["/kundali-creation"])
    if has_puja and has_kundali:
        return {
            "target": None,
            "needs_clarification": True,
            "clarification_msg": "Aap pehle Puja book karna chahenge ya Kundali banwana chahenge? Main dono mein sahayata kar sakta hoon."
        }

    # Priority for specific signups over generic signup
    for target in ["/signup?role=pandit", "/signup"]:
        if any(kw in msg_lower for kw in _NAV_KEYWORDS[target]):
            return {"target": target, "needs_clarification": False}
            
    # Generic signup check
    for kw in _AMBIGUOUS_KEYWORDS["signup_ambiguous"]:
        if kw in msg_lower:
            return {
                "target": None, 
                "needs_clarification": True, 
                "clarification_msg": "Aap Panditji ke roop mein judna chahte hain ya Bhakt (Devotee) ke roop mein?"
            }
            
    query = None
    query_entity_map = {
        "durga": "Durga Puja",
        "satyanarayan": "Satyanarayan",
        "varanasi": "Varanasi",
        "shaadi": "Marriage",
        "marriage": "Marriage",
        "griha pravesh": "Griha Pravesh",
    }
    for kw, val in query_entity_map.items():
        if kw in msg_lower:
            query = val
            break

    # Check other targets
    for target, keywords in _NAV_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            if target == "/puja":
                from app.orchestrator.pandit_onboarding import INDIAN_CITIES_DATASET
                detected_city = None
                for city_key in INDIAN_CITIES_DATASET.keys():
                    if city_key in msg_lower:
                        detected_city = city_key.capitalize()
                        break
                
                service_name = query or "Puja"
                if not detected_city:
                    return {
                        "target": None,
                        "query": query,
                        "service": service_name,
                        "location": None,
                        "needs_clarification": True,
                        "clarification_msg": f"Kis city mein {service_name} book karni hai?"
                    }
                else:
                    puja_query = f"{query} in {detected_city}" if query else detected_city
                    return {
                        "target": target,
                        "query": puja_query,
                        "service": service_name,
                        "location": detected_city,
                        "needs_clarification": False
                    }

            if target == "/kundali-creation":
                detected_dob = extract_dob(msg)
                if not detected_dob:
                    return {
                        "target": None,
                        "query": query,
                        "needs_clarification": True,
                        "clarification_msg": "Aapki janm tareekh (Date of Birth) kya hai?"
                    }
                else:
                    return {"target": target, "query": detected_dob, "needs_clarification": False}

            if target == "/muhurat-finder":
                detected_event = extract_muhurat_event(msg)
                if not detected_event:
                    return {
                        "target": None,
                        "query": query,
                        "needs_clarification": True,
                        "clarification_msg": "Kis event ke liye Muhurat chahiye — shaadi, griha pravesh, ya kuch aur?"
                    }
                else:
                    return {"target": target, "query": detected_event, "needs_clarification": False}
                    
            return {"target": target, "query": query, "needs_clarification": False}
            
    return {"target": None, "query": None, "needs_clarification": False}
