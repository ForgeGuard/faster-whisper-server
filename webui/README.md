# ForgeGuard Faster Whisper Web Console

A Vite + React 18 + TypeScript + Tailwind CSS v3 console for the ForgeGuard
Faster Whisper STT server. Built to static assets and served by FastAPI at
`/web/`.

## Develop

```bash
npm install
npm run dev      # local dev server
npm run build    # emits dist/ (index.html + hashed assets)
npm run preview  # preview the production build
```

The Docker image runs `npm ci && npm run build` and copies `webui/dist` to
`/app/webui_dist`. Vite is configured with `base: './'` so relative asset URLs
work behind a reverse-proxy prefix.

## Shared design system — keep in sync

The following are **byte-for-byte identical** to the Kokoro TTS console at
`kokoro-server/web/`:

- `src/ui/**` — design tokens + primitives (Button, Card, Select, TextArea,
  Slider, Dialog, Toast, Spinner, IconButton, Badge, Field, Input, icons,
  ThemeProvider/ThemeToggle).
- `src/lib/apiClient.ts` — API key handling (localStorage `apiKey`), Bearer
  auth injection, root-path bootstrap from `GET /web/config`, and 401 handling.
- `src/index.css` and `tailwind.config.ts` — shared theme tokens.

When changing any shared file here, copy it to the other repo (and vice versa):

```bash
cp -r src/ui ../../kokoro-server/web/src/
cp src/lib/apiClient.ts ../../kokoro-server/web/src/lib/
cp src/index.css tailwind.config.ts ../../kokoro-server/web/
```

App-specific code (may diverge from the Kokoro console) lives in `src/App.tsx`,
`src/components/stt/**`, `src/lib/sttApi.ts`, and `src/lib/health.ts` (warmup
polling that drives the "model warming" banner).
