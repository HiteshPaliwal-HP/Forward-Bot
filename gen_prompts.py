import os

diff_path = '_bmad_diff_utf8.patch'
spec_path = r'_bmad-output\implementation-artifacts\1-3-fastapi-application-shell-health-endpoints-docker-build.md'
out_dir = r'_bmad-output\implementation-artifacts'

with open(diff_path, 'r', encoding='utf-8') as f:
    diff_content = f.read()

with open(spec_path, 'r', encoding='utf-8') as f:
    spec_content = f.read()

blind_hunter = f"You are the Blind Hunter. Perform an adversarial review of the following diff:\n\n```diff\n{diff_content}\n```\n"
edge_case = f"You are the Edge Case Hunter. Perform an edge-case focused review of the following diff. You also have project read access (simulate if necessary).\n\n```diff\n{diff_content}\n```\n"
acceptance = f"You are an Acceptance Auditor. Review this diff against the spec and context docs. Check for: violations of acceptance criteria, deviations from spec intent, missing implementation of specified behavior, contradictions between spec constraints and actual code. Output findings as a Markdown list. Each finding: one-line title, which AC/constraint it violates, and evidence from the diff.\n\n### Spec\n\n{spec_content}\n\n### Diff\n\n```diff\n{diff_content}\n```\n"

with open(os.path.join(out_dir, 'prompt-blind-hunter.md'), 'w', encoding='utf-8') as f:
    f.write(blind_hunter)

with open(os.path.join(out_dir, 'prompt-edge-case-hunter.md'), 'w', encoding='utf-8') as f:
    f.write(edge_case)

with open(os.path.join(out_dir, 'prompt-acceptance-auditor.md'), 'w', encoding='utf-8') as f:
    f.write(acceptance)

print("Prompt files generated.")
