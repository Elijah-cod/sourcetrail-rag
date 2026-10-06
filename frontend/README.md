# SourceTrail frontend

Next.js (App Router) + React + TypeScript + Tailwind CSS, exported as static files.

```bash
npm install
npm run dev        # http://localhost:3000 — forwards /api/* to the backend on :8000
npm run build      # writes the static site to out/, which FastAPI serves at /
npm run lint
```

The backend must be running for the app to work (see the repository README).
Set `BACKEND_URL` if your backend isn't on `http://localhost:8000`.
