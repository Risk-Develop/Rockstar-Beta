import re

with open('company_system/templates/task_management/personal_board_detail.html', 'r', encoding='utf-8') as f:
    content = f.read()

match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if match:
    script = match.group(1)
    lines = script.split('\n')
    
    # Track brace balance per line
    balance = 0
    problem_line = None
    
    for i, line in enumerate(lines):
        for ch in line:
            if ch == '{':
                balance += 1
            elif ch == '}':
                balance -= 1
        if balance < 0 and problem_line is None:
            problem_line = i + 1 + 2732
            print(f'First negative balance at line: {problem_line} (balance={balance})')
    
    print(f'Final brace balance: {balance} (should be 0)')
    
    # Find specific unclosed sections using stack
    stack = []
    line_num = 2732
    for i, line in enumerate(lines):
        line_num = i + 2732
        for j, ch in enumerate(line):
            if ch == '{':
                stack.append((line_num, j))
            elif ch == '}':
                if stack:
                    stack.pop()
                else:
                    print(f'Line {line_num}, col {j}: Extra closing brace')
    
    if stack:
        print(f'UNCLOSED braces (latest first):')
        for item in reversed(stack[-10:]):
            print(f'  Line {item[0]}, col {item[1]}: unclosed {{')
    else:
        print('All braces matched')
    
    # Check backticks
    backtick_count = script.count('`')
    print(f'Total backticks: {backtick_count}')
    if backtick_count % 2 != 0:
        print('WARNING: Unbalanced backticks!')
        # Find positions
        stack = []
        for i, ch in enumerate(script):
            line_no = 2732 + script[:i].count('\n')
            if ch == '`':
                if not stack:
                    stack.append(line_no)
                else:
                    stack.pop()
        if stack:
            print(f'Unclosed template literal starting at line(s): {stack}')
    else:
        print('Backticks balanced')
    
    # Check initModals
    idx = script.find('function initModals()')
    if idx >= 0:
        line_no = script[:idx].count('\n') + 1 + 2732
        print(f'initModals defined at line {line_no}')
    else:
        print('initModals NOT found in script block')
    
    # Find calls
    for m in re.finditer(r'initModals\(\)', script):
        line_no = script[:m.start()].count('\n') + 1 + 2732
        print(f'initModals() called at line {line_no}')
