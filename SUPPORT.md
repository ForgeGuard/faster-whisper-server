# Support

Thanks for using ForgeGuard Faster Whisper Server. This page explains where to
get help and what is in scope.

## Where to go

| Need | Channel |
|---|---|
| Bug report or regression | [GitHub Issues](https://github.com/forgeguard-ai/faster-whisper-server/issues) |
| Feature request | [GitHub Issues](https://github.com/forgeguard-ai/faster-whisper-server/issues) |
| Configuration / deployment question | [GitHub Issues](https://github.com/forgeguard-ai/faster-whisper-server/issues) (search first) |
| Security vulnerability | [SECURITY.md](./SECURITY.md) — private reporting, **not** a public issue |
| Documentation | [Documentation](./docs/site/index.md) |

Before opening an issue, please:

- Read the relevant [documentation](./docs/site/index.md), especially
  [Troubleshooting](./docs/site/troubleshooting/common-errors.md),
  [Model provisioning](./docs/site/troubleshooting/model-provisioning.md), and
  [Jetson](./docs/site/troubleshooting/jetson.md).
- Search existing issues for a duplicate.
- Include the image tag or chart version, hardware/GPU and driver, the relevant
  environment variables (redact secrets), and the exact error or log lines
  (with transcript text removed).

## Scope: ForgeGuard vs. upstream dependencies

This project is an original ForgeGuard server built on
[faster-whisper](https://github.com/SYSTRAN/faster-whisper),
[CTranslate2](https://github.com/OpenNMT/CTranslate2), and OpenAI Whisper model
weights. We support the ForgeGuard-authored parts: the FastAPI service, health
and readiness behavior, authentication, the container images and Helm chart, and
the web console.

Transcription quality, language support, and model-weight behavior come from the
underlying Whisper models and inference libraries. If an issue reproduces purely
in `faster-whisper`/`CTranslate2` independently of this server, it is best raised
with those projects; we will still track anything that affects this distribution.

## Service expectations

This is open-source software provided under the [MIT License](./LICENSE) with no
guaranteed response time or private support commitment. Maintainers respond on a
best-effort basis.
