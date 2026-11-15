# PROJECT_RULES.md – CreateX AI Development Standards

## 1. Core Principles

1. **Working > Complete** – A feature that works partially is better than a broken feature that is "done."
2. **Test before claiming done** – Never mark a feature complete without actually running it.
3. **No fake responses** – Never return placeholder data, hardcoded image URLs, or mocked AI output in production paths.
4. **No unnecessary dependencies** – If the standard library or an already-installed package can do it, don't add a new one.
5. **MVP scope** – Implement what is specified. Do not add features not in the spec.

---

## 2. Code Standards

### Python (Backend)
- Use **Python 3.12+** features.
- Use **Pydantic v2** (`model_dump()`, `model_validate()`, not `.dict()`).
- Keep route handlers thin — 10–20 lines max. Business logic goes in services.
- All services are `async def`.
- Use `logging` not `print` for debug output.
- Never hardcode API keys or credentials.
- Use `get_settings()` from `app.core.config` for all configuration.

### TypeScript/JavaScript (Frontend)
- Use functional components and React Hooks only.
- No class components.
- Centralise all API calls in `src/services/api.js`.
- Use Tailwind utility classes; never write inline `style={{}}` for layout.
- All interactive elements must have unique `id` attributes.
- Always handle loading and error states explicitly.

---

## 3. Environment Variables

| Rule | Detail |
|------|--------|
| Never hardcode keys | All secrets go in `.env` |
| Never commit `.env` | `.gitignore` covers this |
| Use `.env.example` | Template for all required vars |
| Backend key: service role | `SUPABASE_SERVICE_ROLE_KEY` — backend only |
| Frontend key: anon only | `SUPABASE_ANON_KEY` — only if strictly necessary |

---

## 4. API Contract Rules

- All responses follow: `{ "success": true/false, "data": ... }` or use Pydantic response models.
- All errors return appropriate HTTP status codes:
  - `422` – Validation failure
  - `503` – External service unavailable (Supabase/Gemini not configured)
  - `500` – Unexpected server error
- All endpoints must have a Pydantic request and response model.
- No endpoint returns `200` with an error body.

---

## 5. AI Generation Rules

- **Never fabricate** image URLs, campaign names, or any AI output.
- If `GEMINI_API_KEY` is missing, return a `503` with a clear message: `"GEMINI_API_KEY is not configured."`
- All Gemini calls must include error handling with retry guidance in the error message.
- JSON responses from Gemini must be validated through Pydantic before returning to the client.
- Prompts are defined in `backend/app/core/prompts.py` — not inline in services.

---

## 6. Supabase Rules

- Only the backend uses `SUPABASE_SERVICE_ROLE_KEY`.
- If Supabase is not configured, the app degrades gracefully (session storage fallback for MVP).
- All DB operations are in `supabase_service.py`.
- Do not write raw SQL in route handlers or service files.

---

## 7. Git Rules

- Branch naming: `feature/<name>`, `fix/<name>`, `docs/<name>`
- Commit messages: imperative, present tense: `Add poster generation endpoint`
- Never commit to `main` directly.
- Run `npm run build` and check the backend starts before merging.

---

## 8. UI/UX Rules

- Dark theme is non-negotiable. Background: `#0A0A14`.
- All interactive elements have hover and focus states.
- All loading states show a spinner or skeleton.
- All error states show a clear message with a retry option.
- Mobile responsive layout required.
- No decorative features that don't serve the workflow.
