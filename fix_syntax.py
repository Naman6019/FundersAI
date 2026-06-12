import sys

with open('backend/app/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

out_lines = []
for i, line in enumerate(lines):
    if '{"\\n\\n### Comparison Snapshot\\n" + comparison_summary if comparison_summary else ""}' in line:
        out_lines.append(line.replace('{"\\n\\n### Comparison Snapshot\\n" + comparison_summary if comparison_summary else ""}', '{chr(10) + chr(10) + "### Comparison Snapshot" + chr(10) + comparison_summary if comparison_summary else ""}'))
    elif '{"\\n\\n### Follow-up Answer\\n" + followup_answer if followup_answer else ""}' in line:
        out_lines.append(line.replace('{"\\n\\n### Follow-up Answer\\n" + followup_answer if followup_answer else ""}', '{chr(10) + chr(10) + "### Follow-up Answer" + chr(10) + followup_answer if followup_answer else ""}'))
    else:
        out_lines.append(line)

with open('backend/app/main.py', 'w', encoding='utf-8') as f:
    f.writelines(out_lines)

print("Fixed syntax error lines.")
