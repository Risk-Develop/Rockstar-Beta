# Show lines for handleAddColumnFormSubmit function to verify braces
with open('company_system/templates/task_management/personal_board_detail.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the function: line number for "function handleAddColumnFormSubmit"
for i, line in enumerate(lines):
    if 'function handleAddColumnFormSubmit' in line:
        start = i
        break

# Print from start to the next function after it
# Next function likely at line 3067 (buildColumnHtml)
for i in range(start, min(start+120, len(lines))):
    line = lines[i]
    # Show line number with raw
    print(f'{i+1:4d} (spaces={len(line)-len(line.lstrip()):2d}): {repr(line.rstrip())}')
