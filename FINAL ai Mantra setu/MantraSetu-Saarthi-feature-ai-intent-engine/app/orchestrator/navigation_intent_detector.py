import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Basic routing keywords mapping
_NAV_KEYWORDS = {
    "/": ["home", "main page", "shuruat", "wapas jao", "home page"],
    "/kundali-creation": ["kundali", "janam patri", "patrika", "birth chart", "kundli"],
    "/puja": ["puja", "pooja", "pandit book", "pandit bulao", "book pandit"],
    "/muhurat-finder": ["muhurat", "shubh samay", "auspicious time", "shubh muhurat", "muhurth"],
    "/login": ["login", "sign in", "andar aao", "log in"],
    "/dashboard": ["dashboard", "mera profile", "meri jankari", "meri jaankari", "meri details"],
    "/profile": ["profile"],
    "/about": ["about us", "hamare bare mein", "aapke bare mein"],
    "/contact": ["contact", "sampark", "call karo", "help", "madad"],
    # Signups
    "/signup?role=pandit": ["pandit banna", "pandit registration", "pandit sign up", "pandit signup", "pandit join", "join as pandit", "register as pandit"],
    "/signup": ["devotee banna", "bhakt banna", "devotee sign up", "devotee registration", "register as devotee", "devotee signup", "devotee join", "open signup"]
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
    if "refresh" in msg_lower or "reload" in msg_lower or "kaunsa" in msg_lower or "kya" in msg_lower or "jankari" in msg_lower or "samagri" in msg_lower:
        # Let these be handled by location_query, refresh, or RAG logic
        if not ("kundali" in msg_lower or "puja" in msg_lower or "pandit banna" in msg_lower):
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
            
    # Check other targets
    for target, keywords in _NAV_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            return {"target": target, "needs_clarification": False}
            
    return {"target": None, "needs_clarification": False}
