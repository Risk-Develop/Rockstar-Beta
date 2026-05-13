# Print toggleViewMode function lines with accurate indexing
with open('company_system/templates/task_management/personal_board_detail.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find function definitions manually
for i, line in enumerate(lines):
    if 'function toggleViewMode()' in line:
        start = i
        break

# Print from that line until we see a line that is just '}\n' after blank?
for i in range(start, min(start+40, len(lines))):
    print(f'{i+1:4d}: {repr(lines[i])}')
