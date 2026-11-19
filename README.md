# Mwalimu

**Understand. Teach. Improve.**

Mwalimu ("teacher" in Kiswahili) is an AI-powered learning recovery platform that helps teachers identify learner misconceptions, provide personalised feedback, and measure learning progress. It includes misconception-mapped assessments, AI explanations, an Africa's Talking USSD/SMS-style workflow, and baseline and follow-up learning recovery analytics.

## Windows quick start

Backend (PowerShell):
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

Frontend (second PowerShell):
```powershell
cd frontend
npm install
Copy-Item .env.local.example .env.local
npm run dev
```
Open http://localhost:3000. API docs: http://localhost:8000/docs

Demo login: `teacher@demo.com` / `RadarDemo123!`

SQLite is used by default, so PostgreSQL is not required for the demo. The backend seeds a clearly-labelled illustrative class dataset on first startup.

## OpenRouter AI explanations (optional)
Set `OPENROUTER_API_KEY` in `backend/.env`; the default model is `openai/gpt-4o-mini` and can be changed with `OPENROUTER_MODEL`. The key stays on the backend. The app uses the AI to explain a misconception that has already been identified by the teacher-authored answer mapping; AI does not classify the learner.

You can test the AI without Africa's Talking by signing in, opening `http://localhost:8000/docs`, and trying `POST /api/ai/explanation`. Use the bearer token `radar-demo-token` and provide a question, correct answer, selected answer, misconception, and optional teacher feedback. If no OpenRouter key is configured or the provider request fails, the API safely falls back to the teacher-authored explanation.

## Africa's Talking Sandbox
Set `AT_USERNAME=sandbox`, `AT_API_KEY=...`, and `AT_ENABLED=true` in `backend/.env`. Run `ngrok http 8000` and configure the USSD callback URL as `https://YOUR-NGROK-DOMAIN/api/ussd/callback`. Test in the Africa's Talking Sandbox simulator. Provider acceptance is not proof of handset delivery.

USSD flow: dial service code → 1 Start quiz → enter learner ID (001–030) → answer options. Wrong answers trigger mapped SMS feedback when Sandbox is enabled.

## Notes
- Wrong options are explicitly mapped to teacher-authored misconceptions; AI is not required for live classification.
- A selected option is an indicator of a possible misconception, not proof of a learner's belief.
- Recovery counts only learners who demonstrated a misconception at baseline and no longer select an option mapped to it in follow-up.
- Demo authentication is intentionally minimal. Replace it before production.
- Never commit `.env` or API credentials.
