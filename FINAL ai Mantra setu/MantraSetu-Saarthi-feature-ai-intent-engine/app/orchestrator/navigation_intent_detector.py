import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

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
            return {"target": target, "query": query, "needs_clarification": False}
            
    return {"target": None, "query": None, "needs_clarification": False}
