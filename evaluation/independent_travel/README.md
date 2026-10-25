# Independent illustrated-travel acceptance

This case was designed before the product commit was supplied to the independent executor. It does not import product fixtures, test helpers, an existing timeline or an expected sample export. `BLIND_TASK.md` is the fixed task: four different frame sizes/rates, two silent sources, meaningful silent action, original continuous music, explicit cuts, and restoration.

All pictures are original programmatic illustrations, and all sounds are original synthesized music/ambience. They are explicitly **not real travel footage**. No model, paid resource, creator attribution or external media is needed.

The calling Agent runs `scripts/independent_timeline_acceptance.py --output <new-directory>` from a native checkout. It prepares missing Python dependencies, uses Homebrew for missing FFmpeg on macOS when available, creates the independent assets, invokes the documented unified Agent task entry, discovers capabilities/schemas, saves/exports three immutable versions and checks actual decoded frames/audio. `--materials <presealed-directory>` uses already sealed independent inputs instead. Human users do not manage installation commands, JSON or the service.

Output directories must be new. Each keeps input hashes, invocation logs, requests, initial/final contexts, onset analysis, every job poll, terminal failures, all three exports, decoded contact sheets and a summary. CI should always upload the entire output directory, including on failure. Run on both native Apple Silicon and Intel macOS runners; the reported host is evidence, and a simulated platform is not accepted.

The checker measures actual duration and decoded frame count, compares source-bearing image pixels at each edge and throughout every shot, correlates the continuous music clock, verifies stale/invalid submissions are rejected, and requires restored output to be byte-identical on the same host. Input/import hashes and prior exports must remain unchanged. The synthetic technical result does not establish general editing taste or human aesthetic listening.

## Retained first checker failure

On Windows at product commit `380f904`, the first independently sealed checker reported a failed image comparison despite correct frames. It compared the entire canvas using pure-black reference padding; the product used dark padding `#16181A`, allowed by the task. The sealed task and input materials were unchanged. `verify_output.py` corrects the measurement to compare only source-bearing pixels with the same RMSE threshold. This is a checker repair, not a product rendering repair. The original failed report and the revised report are preserved separately in the local evidence package. When the revised checker initially reused its output path, the original checker was rerun against the unchanged first MP4 to reconstruct its identical report; subsequent revised evidence uses a separate directory. First input, plan and MP4 were never overwritten.

An additional local ad hoc preservation check initially failed on Windows because it read UTF-8 Chinese JSON with the locale's GBK default. It was rerun with explicit UTF-8. The portable entry uses explicit UTF-8 for text records and subprocess capture.

The independent first and portable Windows executions completed real 16/15/16-second exports and rejection checks. The original and restored MP4 SHA-256 were both `625da480ac5db241416d67fd7e72d2097f72931592464a1f308f80d47b36fd0e`; music normalized correlation was `0.9999888139183473` at zero best lag. Source A/C ambience gains measured approximately 0.2501/0.2493 against a requested 0.25. No native macOS run is claimed by this Windows evidence; native runner artifacts must be evaluated separately.
