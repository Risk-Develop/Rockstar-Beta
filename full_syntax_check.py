import re

with open('company_system/templates/task_management/personal_board_detail.html', 'r', encoding='utf-8') as f:
    content = f.read()

match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if match:
    script = match.group(1)
    lines = script.split('\n')
    
    # State tracking
    in_single = False
    in_double = False
    in_template = False
    in_comment = False
    line_no = 2732
    
    # For brace tracking ignoring strings/comments
    brace_stack = []
    paren_stack = []
    # Unicode escapes detection?
    
    # We'll also track string start positions to detect unclosed
    single_start = None
    double_start = None
    template_start = None
    
    for i, line in enumerate(lines):
        line_no = i + 2732
        j = 0
        while j < len(line):
            ch = line[j]
            
            # Handle comments (only // for simplicity; no block comments? They might exist)
            if not in_single and not in_double and not in_template:
                # Check for block comment start
                if j+1 < len(line) and line[j:j+2] == '/*':
                    in_comment = True
                    j += 2
                    continue
                if in_comment:
                    if j+1 < len(line) and line[j:j+2] == '*/':
                        in_comment = False
                        j += 2
                        continue
                    else:
                        j += 1
                        continue
                # Check for line comment
                if ch == '/' and j+1 < len(line) and line[j+1] == '/':
                    break  # ignore rest of line
            
            # Handle single quote string
            if not in_double and not in_template and not in_comment:
                if ch == "'" and not in_single:
                    in_single = True
                    single_start = (line_no, j)
                elif ch == "'" and in_single:
                    in_single = False
                    single_start = None
            
            # Handle double quote string
            if not in_single and not in_template and not in_comment:
                if ch == '"' and not in_double:
                    in_double = True
                    double_start = (line_no, j)
                elif ch == '"' and in_double:
                    in_double = False
                    double_start = None
            
            # Handle template literals
            if not in_single and not in_double and not in_comment:
                if ch == '`' and not in_template:
                    in_template = True
                    template_start = (line_no, j)
                elif ch == '`' and in_template:
                    in_template = False
                    template_start = None
                elif in_template and ch == '\\':
                    # Skip escaped char
                    j += 2
                    continue
            
            # Count braces/parens only outside strings/comments
            if not in_single and not in_double and not in_template and not in_comment:
                if ch == '{':
                    brace_stack.append((line_no, j))
                elif ch == '}':
                    if brace_stack:
                        brace_stack.pop()
                    else:
                        print(f'Line {line_no}, col {j}: Extra closing brace')
                elif ch == '(':
                    paren_stack.append((line_no, j))
                elif ch == ')':
                    if paren_stack:
                        paren_stack.pop()
                    else:
                        print(f'Line {line_no}, col {j}: Extra closing paren')
            j += 1
    
    print(f'Brace stack remaining: {len(brace_stack)}')
    if brace_stack:
        print('Unclosed { at:')
        for item in brace_stack[-5:]:
            print(f'  line {item[0]}, col {item[1]}')
    print(f'Paren stack remaining: {len(paren_stack)}')
    
    if in_single:
        print(f'Unclosed single quote starting at line {single_start[0]}, col {single_start[1]}')
    if in_double:
        print(f'Unclosed double quote starting at line {double_start[0]}, col {double_start[1]}')
    if in_template:
        print(f'Unclosed template literal starting at line {template_start[0]}, col {template_start[1]}')
