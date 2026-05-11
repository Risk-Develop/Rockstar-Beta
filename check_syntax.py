import re, subprocess, sys

with open('company_system/templates/task_management/personal_board_list.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find last <script> tag (inline JS) after extra_scripts block
# Search from near the end
idx = content.rfind('<script>')
if idx == -1:
    print('No <script> found')
    sys.exit(1)
# Ensure it's not the Sortable script? The inline script is the one that starts with function personalBoardsData.
# We'll extract the content between <script> and </script>
close_idx = content.find('</script>', idx)
if close_idx == -1:
    print('No closing script tag')
    sys.exit(1)

script_content = content[idx + len('<script>'):close_idx]

print('Script length:', len(script_content))

# Count braces
open_braces = script_content.count('{')
close_braces = script_content.count('}')
open_parens = script_content.count('(')
close_parens = script_content.count(')')
print('Braces:', open_braces, 'open', close_braces, 'close')
print('Parens:', open_parens, 'open', close_parens, 'close')

# Clean Django template tags to make valid JS
# Replace {{ ... }} with 0 (could be numbers)
script_clean = re.sub(r'\{\{\s*[^}]+\s*\}\}', '0', script_content)
# Replace {% ... %} with empty string or 0; some are blocks, but we only need to remove them for syntax check
script_clean = re.sub(r'\{%\s*[^%]+%\}', '0', script_clean)

# Write to temp file
temp_file = 'temp_inline_script.js'
with open(temp_file, 'w', encoding='utf-8') as f:
    f.write(script_clean)

# Run node --check
result = subprocess.run(['node', '--check', temp_file], capture_output=True, text=True)
print('Node check returned:', result.returncode)
if result.stdout:
    print('stdout:', result.stdout)
if result.stderr:
    print('stderr:', result.stderr)
