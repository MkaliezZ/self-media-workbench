# Validation record

The public MIT implementation has its own evaluation history; private-prototype passes do not transfer automatically. Initial local run: 27 protocol, routing, explicit-caption and actual FFmpeg cut/restore/decode tests passed on Windows. Logs are in evaluation/first-local-regression.txt. More results will be appended after independent changed-material and Windows/macOS CI execution.

The CI matrix is not itself proof of macOS availability. Actual OS/architecture, Python, ASR device, decoded output and final job states are recorded by scripts/ci_smoke.py. CI explicitly opts into downloading a small public model; production does not download models automatically. CPU smoke is not GPU validation, TTS is not human listening and no test here proves actual publishing outcomes.
