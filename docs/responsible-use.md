# Responsible use & data handling

This server transcribes speech to text. Speech recordings and their transcripts
are frequently **sensitive personal data** — private conversations, health and
financial details, identifiable voices — and in many places recording or
transcribing people is legally regulated. This document records the landscape,
what the software does today to minimize risk, and ideas to harden it further.

> This is engineering documentation, not legal advice. Laws vary by jurisdiction
> and change quickly; consult a qualified attorney for your situation.

## Why this matters

- **Wiretap / recording-consent laws.** Many jurisdictions require the consent
  of one or all parties to record a conversation (e.g. "two-party consent"
  states in the US, and comparable rules elsewhere). Transcribing a recording
  made without the required consent can compound the exposure.
- **Data-protection law.** Under the GDPR/UK GDPR, CCPA, and similar regimes, a
  voice recording and its transcript are personal data; a voiceprint can be a
  biometric identifier attracting stricter rules. Operators have obligations
  around lawful basis, minimization, retention, and subject rights.
- **Confidentiality.** Transcripts of meetings, medical, legal, or HR
  conversations can carry contractual or statutory confidentiality duties.

The takeaway for our defaults and wording: treat transcript text and audio as
sensitive by default, keep as little as possible, and make it easy for an
operator to keep it out of logs and off disk.

## What the software does today

- **Text stays out of logs by default.** `LOG_INPUT_TEXT=false` (default) means
  transcript prompts and outputs are never written to the logs — only lengths
  and timings.
- **Audio is not persisted.** Uploads are streamed to a temp file only for the
  duration of the transcription and deleted immediately afterward, including on
  cancellation. `PERSIST_AUDIO=false` is the default; `RETENTION_DAYS=0` keeps
  nothing.
- **No third-party calls.** Transcription runs fully local on the loaded model;
  nothing about a request is sent to an external service. TLS cert generation is
  local and offline too.
- **Auth & transport.** Optional `API_KEY` bearer auth protects the API and the
  model-switch endpoint; built-in HTTPS (`TLS_ENABLED`) protects data in transit
  with zero extra infrastructure.

See [security.md](security.md) for the concrete controls (auth, upload limits,
container hardening, TLS).

## Ideas to harden further (roadmap / open to feedback)

Ordered roughly by leverage-to-effort. None is a silver bullet; layered, they
reduce how much sensitive data exists and who can reach it.

1. **Per-key access + audit.** Owner-scoped API keys, rate limits, and an audit
   trail (keyed by a key fingerprint, never the raw key) of who transcribed what
   and when.
2. **PII redaction option.** An optional post-processing pass that masks obvious
   identifiers (emails, phone numbers, card/account numbers) in the returned
   transcript for logging/telemetry surfaces.
3. **Configurable retention with hard delete.** If a deployment ever stores
   transcripts/audio, honor `RETENTION_DAYS` with a background sweeper that hard-
   deletes both the row and the artifact.
4. **Consent affordance in the console.** A visible reminder that the operator is
   responsible for having consent to record/transcribe the speaker, shown near
   the record control.
5. **Acceptable-Use Policy + abuse contact.** A short AUP and a documented
   process for takedown/abuse if a deployment is exposed beyond a single trusted
   operator.
6. **At-rest encryption guidance.** Document encrypting the data volume when any
   persistence is enabled.

A reasonable **minimum bar** before exposing a deployment beyond a trusted
operator: keep text out of logs and audio off disk (already the defaults),
require an `API_KEY`, serve over TLS, and publish an AUP/abuse process.
