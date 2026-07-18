---
title: Privacy and responsible use
description: How audio and transcripts are handled, and an operator's obligations around consent, minimization, and retention.
order: 22
status: stable
---

# Privacy and responsible use

Speech recordings and their transcripts are frequently **sensitive personal
data** — private conversations, health and financial details, identifiable
voices. This page describes what the software does to minimize risk and what
remains your responsibility as an operator.

> This is engineering documentation, not legal advice. Laws governing recording,
> consent, and personal data vary by jurisdiction and change over time. Consult a
> qualified professional for your situation.

## What the software does today

- **Transcript text stays out of the logs by default.** `LOG_INPUT_TEXT=false`
  (the default) means prompt and output text are never written to the logs — only
  lengths and timings are recorded. Enable it only for local debugging.
- **Uploaded audio is not durably persisted.** Each upload is streamed to a
  per-request temporary file for the duration of the transcription and removed
  immediately afterward — on success, on error, on an oversized-upload rejection,
  on queue shedding, and on client cancellation or disconnect. There is no code
  path that keeps audio after a request completes.
- **No third-party calls.** Transcription runs entirely on the locally loaded
  model; nothing about a request is sent to an external service. Self-signed TLS
  certificate generation is local and offline as well.
- **Optional authentication and transport security.** An `API_KEY` bearer key
  protects the inference and model-admin routes; built-in HTTPS
  (`TLS_ENABLED`) encrypts traffic without extra infrastructure.

### A note on `PERSIST_AUDIO` and `RETENTION_DAYS`

`PERSIST_AUDIO` and `RETENTION_DAYS` are **reserved configuration flags**. They
are read into configuration but are **not currently enforced by any code path** —
the server always uses the per-request temporary file described above regardless
of their values, and no retention sweeper exists. Treat them as placeholders for
future stored-artifact behavior, not as controls that change today's handling. The
accurate statement is: *audio transits a temporary file and is always deleted when
the request ends*, not that it is "never written to disk."

## Why this matters

- **Recording-consent laws.** Many jurisdictions require the consent of one or all
  parties to record a conversation. Transcribing a recording made without the
  required consent can compound the exposure.
- **Data-protection law.** Under regimes such as the GDPR/UK GDPR and comparable
  laws, a voice recording and its transcript are personal data, and a voiceprint
  can be a biometric identifier attracting stricter obligations. Operators
  generally have duties around lawful basis, minimization, retention limits,
  access, and deletion.
- **Confidentiality.** Transcripts of meetings and of medical, legal, or HR
  conversations can carry contractual or statutory confidentiality duties.

## Operator obligations

You are responsible for how a deployment records and processes people's speech.
At minimum, before exposing a deployment beyond a single trusted operator:

- Have a lawful basis and any required consent to record and transcribe.
- Keep transcript text out of the logs (`LOG_INPUT_TEXT=false`, the default) and
  audio off durable storage (the default behavior).
- Require an `API_KEY` and serve over TLS (or terminate TLS at an ingress).
- Minimize what you collect and how long you keep any downstream copies you make
  of transcripts, and honor access and deletion requests for that data.
- Publish an acceptable-use and abuse-contact process if the deployment is reachable
  by untrusted users.

## Related

- [Security hardening](../operations/security-hardening.md) — the concrete
  controls (auth, upload caps, TLS, container hardening).
- [Request lifecycle](../architecture/request-lifecycle.md) — exactly when the
  temporary audio file is created and removed.
