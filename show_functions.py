# Show a known correct function (e.g., showToast at line 2772)
with open('company_system/templates/task_management/personal_board_detail.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# showToast lines 2772-2778
for i in range(2771, 2779):
    line = lines[i]
    print(f'{i+1:4d}: {repr(line)}')

print("---")
# show another function with proper closing (toggleViewMode lines 3173-3201)
for i in range(3172, 3202):
    line = lines[i]
    print(f'{i+1:4d}: {repr(line)}')
