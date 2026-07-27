# Charter — harness-runner

Executes registered golden packs; emits the five-layer scorecard. Header always carries commit SHA, golden dataset version, model configuration. Annotates PASS-BY-STARVATION wherever an invariant passes on missing upstream data. Runs headless in CI on engine-path PRs and post-deploy against the deployed SHA. Never edits fixtures or thresholds; threshold changes arrive only via owner-signed decision-log entries.
