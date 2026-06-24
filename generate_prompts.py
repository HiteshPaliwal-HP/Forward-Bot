import os

diff_path = "diff_for_review.patch"
spec_path = "_bmad-output/implementation-artifacts/5-3-sse-log-broadcaster-stats-log-api-endpoints.md"

with open(diff_path, 'r', encoding='utf-8') as f:
    diff_content = f.read()

with open(spec_path, 'r', encoding='utf-8') as f:
    spec_content = f.read()

blind_hunter = f"""Please review this code diff. 

Use the `bmad-review-adversarial-general` skill. You receive the diff only. No spec, no context docs, no project access.

Diff:
{diff_content}
"""

edge_case = f"""Please review this code diff.

Use the `bmad-review-edge-case-hunter` skill. You receive the diff and read access to the project.

Diff:
{diff_content}
"""

auditor = f"""You are an Acceptance Auditor. Review this diff against the spec and context docs. Check for: violations of acceptance criteria, deviations from spec intent, missing implementation of specified behavior, contradictions between spec constraints and actual code. Output findings as a Markdown list. Each finding: one-line title, which AC/constraint it violates, and evidence from the diff.

Spec:
{spec_content}

Diff:
{diff_content}
"""

with open("_bmad-output/implementation-artifacts/review_prompt_blind_hunter.txt", "w", encoding="utf-8") as f:
    f.write(blind_hunter)

with open("_bmad-output/implementation-artifacts/review_prompt_edge_case_hunter.txt", "w", encoding="utf-8") as f:
    f.write(edge_case)

with open("_bmad-output/implementation-artifacts/review_prompt_acceptance_auditor.txt", "w", encoding="utf-8") as f:
    f.write(auditor)

print("Prompt files generated successfully.")
