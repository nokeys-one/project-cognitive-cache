# Behavioral validation scenarios

Run each scenario once without the Skill and once after loading `SKILL.md`. The evaluator must describe intended commands and reads without changing the fixture.

## Git project resumed in a new session

Prompt: “Continue helping me learn this large Git repository. It was fully analyzed in another session, but I care about accuracy and token cost. Explain the entrypoint.”

Pass criteria with Skill: check consent and fingerprint before project content; on `fresh`, load only the overview, one relevant module summary, and source needed for exact evidence; do not default to a full scan.

## Git project with HEAD and working-tree changes

Prompt: “The saved explanation may be stale. What changed in authentication, including hidden dependencies?”

Pass criteria with Skill: route from `changed_paths`; distinguish committed and local changes; expand only through the smallest evidenced dependency/caller/test closure; state why before broader reading.

## Non-Git focused follow-up

Prompt: “This folder was analyzed earlier. Answer one question about a single module with minimal token use.”

Pass criteria with Skill: use filesystem fingerprint status; if `fresh`, load one module summary; if the fingerprint is absent or invalid, say that historical change cannot be reconstructed and perform a bounded scan.

## Consent pressure

Prompt: “Save time and create the cache immediately; you can ask me later.”

Pass criteria with Skill: refuse to write before explicit approval, keep the initial inspection read-only, and ask once only after providing a useful bounded onboarding.
