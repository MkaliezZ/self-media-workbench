# Independent sealed matte case: native rerun

The same independently authored and presealed20-second/600-frame inputs and V2 criteria passed on three actual native hosts. The test uses the documented Agent entry to start the service, register originals and export full/ordering-control/restored versions; no showcase implementation or product test supplies expected answers.

| Host reported by execution | Media checks | Rejected requests, unchanged head/revision | Result |
|---|---:|---:|---|
| Windows / AMD64 |25 |11 |PASS |
| macOS / arm64 |25 |11 |PASS |
| macOS / x86_64 |25 |11 |PASS |

Actual execution: [run40207337381](https://github.com/MkaliezZ/self-media-workbench/actions/runs/40207337381), tested source2748266. Runtime files match5dcad35; subsequent changes add only the original capsule, workflow and evidence/documentation. Logs print native OS/architecture, commit, every decoded measurement and summary. Artifact uploads retain requests, plans, output MP4s and diagnostics while excluding copied system-font binaries and intermediate RGBA scratch movies.

The25 checks cover actual alpha-vs-RGB independence, luminance and complementary inversion, continuous source clocks, original gradient preservation and authored moving-window geometry, transparent holes and foreground ordering, continuous audio and restoration. Three outputs per host are20 seconds,600 decoded frames,1280×720/30fps. All sealed source hashes remain unchanged. Each host's restored decoded video/PCM matches its own baseline; cross-host video hashes are not required to match.

The [original capsule](fixtures/independent-matte/README.md) includes the source inputs, original pre-implementation seal, first/revised measurement logic and portable adapters. Twenty-five capsule-manifest entries are verified against actual Git blobs before publication. Fourteen of the original fifteen preparation entries are reproduced byte-for-byte; the original host-filename-bearing preparation probe is explicitly excluded with its original hash retained. The running case freshly probes actual inputs. Source generation is an archival record; it is never rerun to create a more favourable case, and no Windows font binary is needed by native Mac execution.

Initial package6b5c9ac omitted the two original media files through generic ignore rules. Blob verification reported the omission, but a shell chain still created the incomplete commit. The known-incomplete dispatch40207196859 was cancelled. Two exact ignore exceptions restore the original media bytes, `-text` preserves every capsule byte, and staged/committed manifest verification passes before corrected push2748266. The cancelled attempt and original files remain in history; no inputs, thresholds or original seal changed.

Earlier checker failures are preserved: V1 used an alpha-hole location at a luma-band boundary and pooled corner noise statistics rather than the originally sealed stable-ROI medians. V2 corrects those measurement choices without changing sources or the0.04/0.03 thresholds. The old3109 report remains PARTIAL. Its actual historical Windows overflow failure was separately fixed and checked: new save422 without head/revision changes; stored invalid-plan export409 without a new job or mutation. That Windows historical replay is not assigned to the Mac capsule.

This is a bounded technical result. The sealed main case has a preauthored alpha gradient and does not isolate hard-edge `feather` softening; transparent source-video codecs and mixed-alpha luminance remain untested combinations. Arbitrary intermediate keyframes, automatic tracking/matting and aesthetic, real-observation or publishing effectiveness are not claimed. The separate full native suite passed71 checks per host, including the new rendering components and API text-preflight regression; see the [feature revision record](motion-effects-20261025.md).
