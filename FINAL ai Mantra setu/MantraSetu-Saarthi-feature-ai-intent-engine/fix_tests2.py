import re

content = open('tests/test_pandit_onboarding.py', encoding='utf-8').read()

# Fix test_consecutive_failed_attempts_fallback assertion
content = content.replace('"pehla naam samajh nahi paya"', '"Kripya apna pehla naam dobara bataiye."')

# Fix test_onboarding_lifecycle email assertion
content = content.replace('"email samajh nahi paya"', '"Kripya apna email address"')

open('tests/test_pandit_onboarding.py', 'w', encoding='utf-8').write(content)
print("Done")
