This repository is being cleared by a deliberate deletion commit.

What this change does
- Removes all tracked files from the main branch in a single commit so the branch contents are empty while preserving full git history.

Important notes
- Any files that were marked SECRET or were untracked (for example, Emesh/.env) are intentionally not staged or committed by this operation and will remain in your working copy (or ignored) so their contents are not reintroduced into the repository history by this automated action.
- If you need the repository history purged (rewritten) instead of preserving it, that is a destructive force-push operation that requires explicit, irreversible actions. Ask for the step-by-step commands and we will provide them, but we will not execute destructive history rewrites without explicit confirmation.

If you did not request this deletion, stop now and do not push — contact your maintainers.
