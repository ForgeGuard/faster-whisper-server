# Security policy

## Reporting a vulnerability

Please do **not** report suspected vulnerabilities through public GitHub issues,
pull requests, or discussions.

Report privately through GitHub's built-in private vulnerability reporting:

1. Open the repository's **Security** tab.
2. Select **Report a vulnerability** (GitHub Security Advisories).
3. Describe the issue, the affected version or image tag, and reproduction steps.

If private reporting is not enabled for your account view, open a minimal public
issue that says only "requesting a private security contact" — with no exploit
details — and a maintainer will open a private advisory.

We aim to acknowledge a report within a few business days and to coordinate a
fix and disclosure timeline with the reporter.

## Supported versions

Security fixes target the latest released minor series. Container images and the
Helm chart are versioned together with the repository (see
[`CHANGELOG.md`](./CHANGELOG.md) and [Releases](https://github.com/forgeguard-ai/faster-whisper-server/releases)).

| Version | Supported |
|---|---|
| 1.1.x | ✅ |
| < 1.1 | ❌ (upgrade to the latest release) |

Pin an immutable release tag (for example `:1.1.0`) for production deployments;
`:latest` tracks the newest stable release and can change without notice.

## Scope

This policy covers the ForgeGuard-authored server, container images, Helm chart,
and web console in this repository. Vulnerabilities in upstream dependencies
(faster-whisper, CTranslate2, Whisper model weights, FastAPI, uvicorn) should be
reported to their respective projects; if a dependency issue affects this
distribution, we will track and ship the remediation here.

## Handling sensitive data

Speech audio and transcripts are frequently sensitive personal data. Operator
guidance for running this server safely — authentication, TLS, upload limits,
transcript logging, temporary-file handling, and container hardening — lives in
[Security hardening](./docs/site/operations/security-hardening.md) and
[Privacy and responsible use](./docs/site/concepts/privacy-and-responsible-use.md).
Do not include real credentials, keys, or captured transcripts in a report.
