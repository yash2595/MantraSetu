import sys, re
with open('app/orchestrator/ai_orchestrator.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace hardcoded greetings
text = re.sub(r'Sabse pehle, apna pehla naam \(First Name\) bataiye\.', 'Sabse pehle, kya aap apni profile photo upload karna chahenge?', text)

# Add pandit-galleryFiles to fields lists if not present at the beginning
text = re.sub(r'"fields": \[\s*"pandit-first-name"', '"fields": [\n                        "pandit-galleryFiles",\n                        "pandit-first-name"', text)

# Replace active_field from pandit-first-name to pandit-galleryFiles
text = re.sub(r'"active_field": "pandit-first-name"', '"active_field": "pandit-galleryFiles"', text)
text = re.sub(r"'active_field': 'pandit-first-name'", "'active_field': 'pandit-galleryFiles'", text)

with open('app/orchestrator/ai_orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(text)
