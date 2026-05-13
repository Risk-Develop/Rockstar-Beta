import re

with open('company_system/templates/task_management/personal_board_detail.html', 'r', encoding='utf-8') as f:
    content = f.read()

match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if match:
    script = match.group(1)
    print('Script length:', len(script))
    # Count backticks by char
    backticks = sum(1 for c in script if c == '`')
    print('Backticks (via char loop):', backticks)
    # Show positions of backticks near problematic areas?
    # Count braces raw again
    ob = script.count('{')
    cb = script.count('}')
    print('Braces raw:', ob, cb)
    # Count parens raw
    op = script.count('(')
    cp = script.count(')')
    print('Parens raw:', op, cp)
