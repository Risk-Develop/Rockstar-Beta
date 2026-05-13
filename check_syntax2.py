import re

with open('company_system/templates/task_management/personal_board_detail.html', 'r', encoding='utf-8') as f:
    content = f.read()

match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if match:
    script = match.group(1)
    lines = script.split('\n')
    
    # Build stack, but skip braces inside string literals and comments
    stack = []
    in_single = False
    in_double = False
    in_template = False
    in_comment = False
    i_line = 2732
    
    for i, line in enumerate(lines):
        i_line = i + 2732
        j = 0
        while j < len(line):
            ch = line[j]
            
            # Handle comments (simple //)
            if not in_single and not in_double and not in_template:
                if line[j:j+2] == '//':
                    break  # rest of line is comment
                if line[j:j+2] == '/*':
                    in_comment = True
                    j += 2
                    continue
                if in_comment:
                    if line[j:j+2] == '*/':
                        in_comment = False
                        j += 2
                        continue
                    else:
                        j += 1
                        continue
            
            # Handle strings
            if not in_double and not in_template and not in_comment:
                if ch == "'" and not in_single:
                    in_single = True
                elif ch == "'" and in_single:
                    in_single = False
            if not in_single and not in_template and not in_comment:
                if ch == '"' and not in_double:
                    in_double = True
                elif ch == '"' and in_double:
                    in_double = False
            
            # Handle template literals (backticks) - ignore ${} inside
            if not in_single and not in_double and not in_comment:
                if ch == '`' and not in_template:
                    in_template = True
                elif ch == '`' and in_template:
                    in_template = False
                elif in_template and ch == '$' and j+1 < len(line) and line[j+1] == '{':
                    # Skip the ${ pair - but the { inside should be counted as real?
                    # Actually braces inside ${} are real JS braces, so we should count them normally.
                    # We'll just skip the $, not the {
                    j += 1  # skip $
            
            if not in_single and not in_double and not in_template and not in_comment:
                if ch == '{':
                    stack.append((i_line, j, 'open'))
                elif ch == '}':
                    if stack:
                        stack.pop()
                    else:
                        print(f'Line {i_line}, col {j}: Extra closing brace')
            j += 1
    
    print(f'Remaining unclosed braces: {len(stack)}')
    for item in stack[-10:]:
        print(f'  Line {item[0]}, col {item[1]}: open brace')
    
    # Also count braces ignoring strings only for rough check
    print(f"\nRaw counts (no string filtering):")
    raw = script
    print(f" {{ : {raw.count('{')} }} : {raw.count('}')}")
