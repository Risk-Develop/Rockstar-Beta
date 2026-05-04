import re

inpath = r'C:\Users\DAVID\.local\share\kilo\tool-output\tool_df2eeac0b001cYEfp6k2JufKTN'
outpath = r'C:\Users\DAVID\Documents\GitHub\Rockstar-Beta\company_system\templates\task_management\personal_board_detail.html.tmp'

with open(inpath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

inside = False
out_lines = []
for line in lines:
    stripped = line.strip()
    if stripped == '<content>':
        inside = True
        continue
    if stripped == '</content>':
        inside = False
        break
    if inside:
        # Match lines that start with a number (line number) followed by colon
        m = re.match(r'^\s*\d+:\s*(.*)', line)
        if m:
            out_lines.append(m.group(1).rstrip('\n'))

with open(outpath, 'w', encoding='utf-8') as out:
    out.write('\n'.join(out_lines) + '\n')

print(f'Extracted {len(out_lines)} lines to {outpath}')
