Start package $ARGUMENTS.

1. Confirm `docs/packages/$ARGUMENTS.md` exists; if not, stop and say so.
2. Delegate to the `contract-tester` subagent: write `tests/contract/$ARGUMENTS/` on branch `test/$ARGUMENTS` from the spec's acceptance lines and the named contracts. Wait for its summary.
3. Delegate to the `implementer` subagent on branch `feat/$ARGUMENTS` (worktree). If the spec's tier is AMBER, return its plan to me and stop; do not build until I reply "approved".
4. When implementation is complete: run `/audit-prep $ARGUMENTS` and open the PR.

Never merge. Never run anything owner-triggered.
