# Change Review

## Finding

### P2 — Exclude the generated report from subsequent reviews

`.claude/agents/change_reviewer.md:10` asks Codex to review *all* changes since the last commit and write the result to `planning/REVIEW_BY_CHANGE_REVIEWER_AGENT.md`. After the first run, that report is itself an uncommitted change. Running the agent again before committing therefore causes Codex to include its previous review in the review scope and overwrite the same file, which can produce self-referential or stale findings unrelated to the implementation changes.

Update the command prompt to explicitly exclude `planning/REVIEW_BY_CHANGE_REVIEWER_AGENT.md` from the reviewed changes (or remove the old report before collecting the diff). This keeps repeated review runs idempotent and limits feedback to the changes the user actually wants reviewed.

## Summary

No other actionable issues were found in the new agent definition.
