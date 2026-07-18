# Token And Resource Efficiency Policy

## Purpose

This policy reduces avoidable model, computer, and operator cost without
hiding delivery evidence, weakening safety checks, or collecting private
transcripts. It is platform-neutral: it does not require Claude Code,
`token-diet`, or any provider-specific transcript reader.

## Core Rules

1. Delegate only when parallelism, isolation, or specialist capability has a
   clear benefit. Do not create ceremonial sub-agents for trivially local work.
2. Use the context kit and progressive disclosure. Read the compact entry
   files first, then load detailed specifications only for the current scope.
3. Prefer deterministic scripts for deterministic work such as validation,
   formatting, dependency analysis, and state inspection. Reserve model calls
   for judgment, design, ambiguity, and synthesis.
4. Keep command output useful but bounded. A summary must retain the command,
   exit code, failures or warnings, test pass/fail totals, and artifact paths.
   Original logs must remain recoverable when they are relevant to review.
5. Move durable reference material into linked, tiered documents instead of
   repeatedly loading it into every task. Do not delete needed evidence merely
   to shorten context.
6. Treat model selection as a project-level, opt-in cost decision. A project
   may define tiers and escalation rules, but the core workflow does not
   hardcode a provider or model.

## Evidence And Privacy Boundaries

- Never filter away security findings, validation failures, warnings that can
  affect acceptance, or the location of original evidence.
- Do not collect prompts, responses, credentials, cookies, private session
  transcripts, or absolute local paths solely to optimize token use.
- Any transcript-based tool needs a separate privacy review, explicit source
  allowlist, local-storage policy, retention limit, and rollback path before
  adoption.
- Output filtering must begin in audit-only mode. Preserve originals, publish
  the filter rules, and provide a one-command disable path.

## Measurement

Record a baseline before claiming an efficiency improvement. Use the least
intrusive trustworthy measurements available:

- elapsed time, retries, handoffs, and manual interventions
- provider-reported usage or cost, when available and authorized
- polling frequency, command duration, and compute-heavy steps

Mark values as measured, estimated, or unknown. Do not infer token totals for
providers whose local data cannot support that claim.

## Review Trigger

Apply this policy during review when a change affects agent count, model
selection, polling cadence, long-running commands, always-loaded context, or
output handling. Confirm that the change has a bounded purpose, preserves
review evidence, states its measurement basis, and has a disable or rollback
path when it changes runtime behavior.

## Adoption Levels

1. **Baseline now:** follow the core rules and record resource impact in task
   packets when applicable.
2. **Observe:** collect only approved operational measurements and identify
   repeatable waste.
3. **Optimize:** introduce a project-specific tool or filter only after a
   dry-run or audit period, documented evidence, and rollback instructions.

## External Tool Evaluation

Evaluate an external efficiency tool for platform compatibility, data sources,
privacy and retention, dry-run support, evidence preservation, reproducible
configuration, and an easy disable path. The Claude Code project
[`token-diet`](https://github.com/KasperChenGH/token-diet) is a useful source
of ideas such as reducing unnecessary delegation and filtering noisy tool
output, but it is not a required dependency and does not measure every agent
platform used by this system.
