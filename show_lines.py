# Show raw lines around the suspect area
with open('company_system/templates/task_management/personal_board_detail.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(5478, 5502):
    line = lines[i]
    # Show line number and repr to see spaces
    print(f'{i+1:4d}: {repr(line)}')
