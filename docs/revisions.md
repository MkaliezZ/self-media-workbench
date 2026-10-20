# Revision and failure history

## Initial MIT implementation

New unified task API/CLI and an independently authored Python/FFmpeg renderer. The AGPL prototype renderer, private course corpus and user projects are excluded. Windows regression: 27 tests passed. Real local CPU ASR and HTTP export/decode also passed; these do not transfer the prototype's independent acceptance to this implementation.

## Interpreter selection found during integration review

The first installed wrapper used the calling Agent's Python. Agents with another interpreter could then miss the installed workbench dependencies. The wrapper now prefers the checkout's virtual environment, then the interpreter recorded privately at installation. A Windows invocation from a different bundled Python selected the recorded interpreter successfully. The cross-platform smoke also exercises the installed entry. No content answers were provided to the independent evaluator.

Subsequent actual CI failures and independent evaluation findings are appended here; initial failures must not be rewritten as first-pass success.
