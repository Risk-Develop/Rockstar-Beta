# Show validateForm function raw lines
with open('company_system/templates/task_management/personal_board_detail.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'function validateForm(formId)' in line:
        start = i
        break

for i in range(start, min(start+30, len(lines))):
    print(f'{i+1:4d}: {repr(line.rstrip())}')
