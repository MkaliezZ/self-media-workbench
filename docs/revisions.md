# Revision and failure history

## Initial MIT implementation

New unified task API/CLI and an independently authored Python/FFmpeg renderer. The AGPL prototype renderer, private course corpus and user projects are excluded. Windows regression: 27 tests passed. Real local CPU ASR and HTTP export/decode also passed; these do not transfer the prototype's independent acceptance to this implementation.

## Interpreter selection found during integration review

The first installed wrapper used the calling Agent's Python. Agents with another interpreter could then miss the installed workbench dependencies. The wrapper now prefers the checkout's virtual environment, then the interpreter recorded privately at installation. A Windows invocation from a different bundled Python selected the recorded interpreter successfully. The cross-platform smoke also exercises the installed entry. No content answers were provided to the independent evaluator.

Subsequent actual CI failures and independent evaluation findings are appended here; initial failures must not be rewritten as first-pass success.

## Runner allocation

The initial Windows CI completed successfully. macOS 15 ARM/Intel jobs remained queued without runner names or executed steps; this is pending allocation, not a compatibility pass or an observed code failure. A manual macOS 26 ARM/Intel runner set is available to test alternate hosted capacity. Superseded queued workflows may be cancelled; their original statuses remain visible in Actions.

## Independent DSH changed-material round 1

DSH independently chose a synthetic rental-appliance account and a separate synthetic balcony TTS video, without tests, prior evaluation answers or earlier private materials. It completed five content stages, direct script entry, explicit project/session resume, actual CPU medium ASR (109 groups), full-group cut/restore, 18 caption groups and decoded export (98 groups). It caught and revised its own inaccurate median description; this initial content error and rejected requests remain in the private record. The initial report was **conditional**, not a clean pass.

Confirmed product findings and fixes:

- All-current continuation incorrectly started another topic cycle. It now returns complete/null/empty plan; an explicit next-topic request still runs topics. Complete means saved stages, not publication approval.
- Submission revision/source-vs-artifact contracts were underspecified. Schema, Agent instructions and conflict errors now state the project lock and correct evidence binding.
- Entirely unknown metrics no longer need invented collection times/anchors; numeric observations still require both. Null is not zero.
- Export words now preserve ASR ID, original source bounds and original-group probability alongside mapped output bounds.
- Correcting an English token without its original separator could join adjacent words. Corrections now retain existing edge whitespace.

Post-fix Windows regression: 30 tests passed, including completed resume, unknown-vs-numeric evidence, original/export word identity, explicit FFmpeg cut/restore/decode and correction spacing. DSH's original report was written before its 15-minute harness timeout; the timeout receipt is preserved separately and is not reported as a normal final tool exit. A bounded independent retest follows.

## Independent DSH round 2: remaining planned-metric loophole

DSH verified the completed resume fix, schema descriptions, null metrics, original IDs/bounds/probabilities and whitespace with another synthetic 13.46-second herb TTS video (26 actual ASR groups, six caption groups, fully decoded export). It also found a genuine remaining gap: numeric values without evidence/time were accepted when observation_type was planned. Round 2 was therefore still conditional; its accepted negative probe is retained, not rewritten or deleted.

The numeric guard now applies to **all** review types, including standalone/planned; future targets belong in next_experiment/stop_rule rather than observed values. The regression explicitly checks both planned and simulated numeric cases. A final independent focused retest verifies this boundary.
