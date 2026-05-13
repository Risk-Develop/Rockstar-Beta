# Count leading spaces for lines 5479-5500
with open('company_system/templates/task_management/personal_board_detail.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(5478, 5501):
    line = lines[i].rstrip('\n')
    leading = len(line) - len(line.lstrip(' '))
    # Show leading spaces count and line content
    print(f'{i+1:4d} (spaces={leading:2d}): {line}')
