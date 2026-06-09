$diff = Get-Content -Raw "c:\Users\hitesh.paliwal\Documents\GitHub\Forward-Bot\_bmad-output\review_diff.txt"
$spec = Get-Content -Raw "c:\Users\hitesh.paliwal\Documents\GitHub\Forward-Bot\_bmad-output\implementation-artifacts\2-1-source-registration-retrieval.md"

$blindHunterPrompt = @"
# Blind Hunter Review

Review the following diff using the bmad-review-adversarial-general skill guidelines. You have NO project context — just this diff.

## Diff Output
```diff
$diff
```
"@

$edgeCaseHunterPrompt = @"
# Edge Case Hunter Review

Review the following diff using the bmad-review-edge-case-hunter skill guidelines. You have read access to the project.

## Diff Output
```diff
$diff
```
"@

$acceptanceAuditorPrompt = @"
# Acceptance Auditor Review

You are an Acceptance Auditor. Review this diff against the spec and context docs. Check for: violations of acceptance criteria, deviations from spec intent, missing implementation of specified behavior, contradictions between spec constraints and actual code. Output findings as a Markdown list. Each finding: one-line title, which AC/constraint it violates, and evidence from the diff.

## Spec File Content
```markdown
$spec
```

## Diff Output
```diff
$diff
```
"@

Set-Content -Path "c:\Users\hitesh.paliwal\Documents\GitHub\Forward-Bot\_bmad-output\implementation-artifacts\prompt-blind-hunter.md" -Value $blindHunterPrompt
Set-Content -Path "c:\Users\hitesh.paliwal\Documents\GitHub\Forward-Bot\_bmad-output\implementation-artifacts\prompt-edge-case-hunter.md" -Value $edgeCaseHunterPrompt
Set-Content -Path "c:\Users\hitesh.paliwal\Documents\GitHub\Forward-Bot\_bmad-output\implementation-artifacts\prompt-acceptance-auditor.md" -Value $acceptanceAuditorPrompt
