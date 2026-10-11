# Factory Agent Capabilities Reference Adapter V1

**Purpose:** optional consumer/agent_capabilities_adapter.py receives Prompt Maker's independent agent-reference sidecar. The existing consumer/adapter.py, pinned consumer subset, profile mapping, existing scaffolds, and generation contracts are NOT changed.

## Fail-closed preflight
- Exact Blueprint raw-byte SHA-256, producer schema and project identity.
- Strict handoff and authority structure. No execution permission, admitted runtime, selected skills, fake Visual QA PASS, or production-ready claims.
- Only user-confirmed supported Factory technology is eligible; undecided or unsupported writes no files.
- Output must be a brand-new directory. Any existing path or symlink is rejected.
- External QA feedback, when supplied with digest references, is stored as UNVERIFIED_EXTERNAL_REPORT and never trusted for acceptance.

On success the unchanged consumer materializes the project and validates its output. This optional adapter writes exactly two additive files in docs/ai:
AGENT_CAPABILITIES_REFERENCE_V1.json
AGENT_CAPABILITIES_REFERENCE_PROVENANCE_V1.json

These record SHA-256 of Blueprint, handoff and attached reference. Existing MATERIALIZATION_PROVENANCE.json and BLUEPRINT_CONSUMER_SUBSET.json are preserved. No passwords, SQL execution, agent runtime calls, or Workspace admission are involved.

## Invocation
python consumer/agent_capabilities_adapter.py --blueprint BP.json --handoff PM.json --output NEW_DIR
Optional advisory feedback: --feedback REPORT.json

Run regression tests: python -m unittest discover -s tests -p test_agent_capabilities_adapter.py -v
The known existing Windows Python hanging-preflight timeout failure is not a new regression and is not fixed by this reference-only track.

The output is a **candidate starting scaffold**, not an implementation of production UI or approval for release.
