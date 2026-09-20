Prepare the audit bundle for package $ARGUMENTS on the current branch.

Produce, in this order, and put the result in the PR description:
1. Package ID, tier, fence (files touched vs fence declared in the spec; list any file outside it).
2. Contract lines implemented — each with a pointer (file, symbol).
3. Tests: `tests/contract/$ARGUMENTS/` result, whole-suite result, guard result (paste the last line of each).
4. Migration: revision id, up/down proof lines, backfill idempotency note (or "none").
5. Proposed test changes — tests believed wrong, with reasons. Not edited.
6. Not done — anything in the spec not delivered, and why.
7. Owner-triggered verification — exact commands for the live fixture run, if the spec requires one.
8. Decision log — any locked decision touched (should be none) and any new decision proposed.

Then tag the PR `package/$ARGUMENTS` and `needs-cc-audit`. Do not merge.
