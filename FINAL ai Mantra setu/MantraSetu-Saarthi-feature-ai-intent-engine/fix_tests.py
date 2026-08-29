import re

content = open('tests/test_pandit_onboarding.py', encoding='utf-8').read()

# Fix test_location_awareness_query
content = re.sub(
    r'(session\.onboarding_state\["current_field_index"\] = 1.*?)(\s*mock_extract\.return_value = "Ramesh")',
    r'\1\n        session.onboarding_state["collected_data"] = {"pandit-avatar": "skipped"}\2',
    content,
    flags=re.DOTALL
)

# Fix test_consecutive_failed_attempts_fallback
# It already has current_field_index = 1, we just need to make sure collected_data has skipped
# Actually, the regex above will match both if they have the same pattern. Wait, the second one has "INVALID", not "Ramesh"
content = re.sub(
    r'(session\.onboarding_state\["current_field_index"\] = 1.*?)(\s*mock_extract\.return_value = "INVALID")',
    r'\1\n        session.onboarding_state["collected_data"] = {"pandit-avatar": "skipped"}\2',
    content,
    flags=re.DOTALL
)

# Fix test_onboarding_lifecycle for avatar skip
content = re.sub(
    r'(# Avatar skip triggers a confirmation prompt.*?)(# Answer confirmation.*?)(# 3\. Second answer)',
    r'# Avatar skip advances directly to first name\n        self.assertEqual(resp.navigation_directive["action"], "FILL_FORM")\n        self.assertEqual(resp.navigation_directive["active_field"], "pandit-first-name")\n        \n        self.assertEqual(session.onboarding_state["current_field_index"], 1)\n        self.assertEqual(session.onboarding_state["collected_data"]["pandit-avatar"], "skipped")\n        \n        \3',
    content,
    flags=re.DOTALL
)

open('tests/test_pandit_onboarding.py', 'w', encoding='utf-8').write(content)
print("Done")
