# Free target-GPU access investigation — 2026-10-21

Outcome: **AMD/Intel Vulkan and native Intel Mac Metal remain hardware-unverified.** No new target-GPU Chinese ASR, subtitle, pause-cut or restoration acceptance was obtained. No simulated result, CPU fallback or previous NVIDIA/Apple Silicon run is substituted for those results. The maintainer requested free/existing resources only, then ended further resource searching and agreed to community hardware testing. No paid resource, new cloud account, trial activation or provider application was created.

## Observed access

- The repository has zero self-hosted runners. No connected cloud GPU account/configuration was found in the checked local CLI configuration and environment names. This is scoped discovery, not proof that the maintainer owns no other accounts.
- Five existing SSH aliases were checked read-only with existing keys/host trust. Three connections succeeded: their exposed Linux DRM inventory contained no AMD/Intel GPU; two aliases may identify one host. One connection timed out, another rejected existing key permissions. Neither unavailable machine is called GPU-less. Network addresses, aliases and key paths are omitted from the public derivative; the original is retained privately and identified by SHA256.
- [AMD Radeon evaluation](https://www.amd.com/en/developer/resources/cloud-access.html) and [Colfax](https://experience.colfax-intl.com/project/amd-rocm/)/[Comino](https://www.grando.ai/promo/experience-amd-rocm-on-radeon-tm-pro) advertise free access subject to registration/approval. No approved instance was available. The advertised Linux/ROCm offering does not establish Windows Vulkan acceptance.
- [Intel Cloud Services](https://cloud.intel.com/) reached the email sign-in form in the existing browser. No logged-in instance was available. Its [request guide](https://cloud.intel.com/docs/how_to_request.html) requires an account and reservation; current free entitlement/capacity was not visible without login.
- [MacStadium's current FOSS page](https://macstadium.com/company/opensource) describes Apple Silicon, a waitlist and three months of project development. Its old Intel offer is not evidence of current free Intel capacity. Cirrus documents Apple Silicon; CircleCI retired Intel Mac support. These did not provide an accessible native Intel Metal environment.

## Native cloud probe and revisions

The source probe compiles Swift against Metal, enumerates native devices and executes an actual compute kernel with CPU readback validation when a device exists. It never reports CPU execution as Metal. Its status is a prerequisite result; even a completed kernel is not ASR acceptance.

1. `d63ceba`, [run 39481952674](https://github.com/MkaliezZ/self-media-workbench/actions/runs/39481952674): standard `macos-15-intel` and `macos-26-intel` jobs remained queued with no allocated runner. Cancelled before execution after the evidence-scope revision. No compile/kernel/ASR result exists.
2. Pre-execution review found the first manifest listed the compiled binary although the artifact deliberately excluded it. `a08a70a` excludes that binary from the manifest and records its SHA256, commit and probe source hashes in the result. This was an audit packaging repair, not an observed hardware/ASR failure. The first source revision and queue record remain.
3. `a08a70a`, [run 39482450217](https://github.com/MkaliezZ/self-media-workbench/actions/runs/39482450217): both standard Intel images were still queued, with no assigned runner or executed steps, when the maintainer ended the search. Cancellation was requested. There is **no native Metal availability verdict** from this run.
4. The automatic compatibility run 39481950009 had a successful Windows job; queued Mac jobs were cancelled because this change added probe/audit tooling, with no ASR runtime change. It is not presented as a new three-platform compatibility pass.

All three target routes therefore have status **not run / awaiting community hardware access**, rather than passed or product failure. Existing successful platform results remain in [validation history](../docs/validation.md). The [community guide](../docs/cloud-gpu-acceptance.md) defines the same Chinese source, strict GPU gate, source-bound captions and actual cut/restore checks, plus report fields and partial-failure handling.

The adjacent `vendor-cloud-20261021/` directory contains public access observations, a deliberately sanitized SSH derivative and workflow snapshots. Private raw SSH output is retained outside the public checkout. No original ASR was generated in this investigation, so there is no new ASR-quality verdict or media output to attach.
