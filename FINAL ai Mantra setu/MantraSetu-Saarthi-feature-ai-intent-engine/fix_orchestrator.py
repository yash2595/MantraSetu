import sys

with open('app/orchestrator/ai_orchestrator.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

def find_block(search_str, end_strs):
    start = -1
    for i, line in enumerate(lines):
        if search_str in line:
            start = i - 1
            if start < 0 or '#' not in lines[start]:
                start = i
            break
    if start == -1: return -1, -1
    
    end = -1
    for i in range(start+1, len(lines)):
        if any(s in lines[i] for s in end_strs):
            end = i - 1
            break
    return start, end

# The onboarding state block
ob_start, ob_end = find_block('onboarding_state = getattr(session, \"onboarding_state\", None)', ['Check if we are waiting for a Site Tour clarification'])

# The site tour block
tour_start, tour_end = find_block('pending_tour_clarification = getattr(session, \"pending_tour_clarification\", False)', ['pending_clarification = getattr'])

# The pandit block
pandit_start, pandit_end = find_block('pending_clarification = getattr(session, \"pending_pandit_clarification\", False)', ['Check for Pandit role triggers FIRST'])

print(f'OB: {ob_start}-{ob_end}, Tour: {tour_start}-{tour_end}, Pandit: {pandit_start}-{pandit_end}')

if ob_start > 0 and tour_start > 0 and pandit_start > 0:
    ob_lines = lines[ob_start:ob_end+1]
    tour_lines = lines[tour_start:tour_end+1]
    pandit_lines = lines[pandit_start:pandit_end+1]
    
    # We want: tour, pandit, OB
    new_lines = lines[:ob_start] + tour_lines + pandit_lines + ob_lines + lines[pandit_end+1:]
    
    with open('app/orchestrator/ai_orchestrator.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print('Reordered successfully!')
else:
    print('Failed to find blocks')
