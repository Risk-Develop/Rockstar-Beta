# Show lines for validateField and next function start
with open('company_system/templates/task_management/personal_board_detail.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Show 5479 to 5505 with detailed brace tracking
brace_stack = []
for i in range(5478, 5505):
    line = lines[i]
    line_no = i+1
    # Count braces in order with positions
    for j,ch in enumerate(line):
        if ch == '{':
            brace_stack.append((line_no, j, 'open'))
            print(f'Line {line_no}, col {j}: {{  (stack size now {len(brace_stack)})')
        elif ch == '}':
            if brace_stack:
                top = brace_stack.pop()
                print(f'Line {line_no}, col {j}: }}  closes from line {top[0]} col {top[1]} (stack size now {len(brace_stack)})')
            else:
                print(f'Line {line_no}, col {j}: }}  EXTRA - stack empty!')
# After
print(f'\nRemaining open braces on stack: {len(brace_stack)}')
for item in brace_stack:
    print(f'  Unclosed from line {item[0]}, col {item[1]}')
