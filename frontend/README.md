# FinAlly frontend

Next.js static export, served by FastAPI from the same origin. Every request is
a relative `/api/*` path, so there is no CORS config and no API base URL.

```bash
npm ci
npm run build      # static export -> out/
npm test           # component tests (vitest + React Testing Library)
npm run lint
```

`npm run dev` needs the backend on the same origin. `npm run dev:mock` runs the
terminal against in-memory fixtures that speak the shapes in
`planning/API_CONTRACT.md`, including a simulated price stream, so the UI can be
worked on with no backend running. The mock is compiled out of a normal build.

Live prices arrive over one shared `EventSource` (`src/lib/priceStore.ts`).
Components subscribe per ticker, and the price flash is applied straight to the
DOM node, so a tick does not re-render the page.
