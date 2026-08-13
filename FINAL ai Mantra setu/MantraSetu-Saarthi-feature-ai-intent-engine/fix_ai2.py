import sys, re

with open('app/orchestrator/ai_orchestrator.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix the fields lists to be the 20-field list
new_fields_str = '''[
                        "pandit-galleryFiles",
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
                        "pandit-password",
                        "pandit-confirm"
                    ]'''
text = re.sub(r'\["pandit-name", "pandit-phone", "pandit-email", "pandit-city", "pandit-state", "pandit-exp", "pandit-spec", "pandit-lang"\]', new_fields_str, text)

# Replace active_field
text = text.replace('"active_field": "pandit-name"', '"active_field": "pandit-galleryFiles"')
text = text.replace("'active_field': 'pandit-name'", "'active_field': 'pandit-galleryFiles'")
text = text.replace('"active_field": "pandit-first-name"', '"active_field": "pandit-galleryFiles"')

# Replace greeting
old_greet1 = "Sabse pehle, apna poora naam bataiye."
old_greet2 = "Sabse pehle, apna pehla naam (First Name) bataiye."
new_greet = "Sabse pehle, kya aap apni profile photo upload karna chahenge?"
text = text.replace(old_greet1, new_greet)
text = text.replace(old_greet2, new_greet)

with open('app/orchestrator/ai_orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(text)
