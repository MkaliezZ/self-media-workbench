# Evidence subsets

These are byte-preserving copies selected from the original cloud artifacts. See the [Chinese report](../chinese-acceptance-20261021.md) for verdicts and limitations.

- `round1-80e5ae5`: failed numeric-comparison run 39472668879. Actual raw ASR/export succeeded before the driver stopped. The untouched original metrics remain alongside a separately named revised comparison.
- `round2-9f37d82`: run 39473665015. Automatic technical checks passed, but actual subtitles failed independent semantic review by crossing sentence/hold B.
- `final-c8f5b99`: final run 39473993837 with sentence-aware grouping, real source-bound corrections, A cut/restore and B preservation.
- `independent-round2` and `independent-final`: separate downloaded-file review, manifest recomputation, source/cut/restore checks and local complete MP4 decode results.
- `public-subset-manifest.json`: SHA256/size of the files actually published in this directory, excluding that manifest itself.

The original `evidence-manifest.json` and `artifact-manifest.json` inside platform directories describe the **complete cloud download**, not this smaller public selection. Missing files when running their verifier against this subset are expected; do not relabel them corrupt. Full original packages, including all MP4s, requests, logs and source copies, remain locally under `chinese-media-audit-20261021/run-<id>/`. The local `original-archives.json` also hashes ZIP snapshots for all three runs. Hosted cloud artifacts have finite retention, so local original packages are the durable full copies.
