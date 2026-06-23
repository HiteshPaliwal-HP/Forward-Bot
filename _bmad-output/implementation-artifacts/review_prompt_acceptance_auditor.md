# Acceptance Auditor Review Prompt
You are an Acceptance Auditor. Review this diff against the spec and context docs. Check for: violations of acceptance criteria, deviations from spec intent, missing implementation of specified behavior, contradictions between spec constraints and actual code. Output findings as a Markdown list. Each finding: one-line title, which AC/constraint it violates, and evidence from the diff.

Please review the diff file:
@[c:\Users\hitesh.paliwal\Documents\GitHub\Forward-Bot\_bmad-output\diff_output.txt]

And the Spec file:
@[c:\Users\hitesh.paliwal\Documents\GitHub\Forward-Bot\_bmad-output\implementation-artifacts\5-2-full-structlog-chain-ring-buffer-complete-event-catalog.md]

Also consider these reference context docs if relevant:
@[c:\Users\hitesh.paliwal\Documents\GitHub\Forward-Bot\_bmad-output\planning-artifacts\epics.md]
@[c:\Users\hitesh.paliwal\Documents\GitHub\Forward-Bot\_bmad-output\planning-artifacts\architecture.md]
