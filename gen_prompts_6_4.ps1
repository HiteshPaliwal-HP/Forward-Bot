$diff = Get-Content 'diff_6_4_full.patch' -Raw
$spec = Get-Content '_bmad-output\implementation-artifacts\6-4-forwards-list-s2-forward-edit-s3-screens.md' -Raw

$blind = "Please review this code diff. Use the bmad-review-adversarial-general skill. You receive the diff only. No spec, no context docs, no project access.`n`nDiff:`n$diff"
$edge = "Please review this code diff. Use the bmad-review-edge-case-hunter skill. You receive the diff and read access to the project.`n`nDiff:`n$diff"
$auditor = "You are an Acceptance Auditor. Review this code diff against the spec and context docs. Check for: violations of acceptance criteria, deviations from spec intent, missing implementation of specified behavior, contradictions between spec constraints and actual code. Output findings as a Markdown list. Each finding: one-line title, which AC/constraint it violates, and evidence from the diff.`n`nSpec:`n$spec`n`nDiff:`n$diff"

Set-Content -Path '_bmad-output\implementation-artifacts\review_prompt_blind_hunter.txt' -Value $blind
Set-Content -Path '_bmad-output\implementation-artifacts\review_prompt_edge_case_hunter.txt' -Value $edge
Set-Content -Path '_bmad-output\implementation-artifacts\review_prompt_acceptance_auditor.txt' -Value $auditor
