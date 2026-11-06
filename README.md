# DEMIO AI — deployment package

## Files
- `app.py`: Flask backend and AI API connection.
- `index.html`: responsive DEMIO interface.
- `app.js`: chat, voice, variables, mentor, exercises and games.
- `requirements.txt`: Python dependencies.

## Render setup
Create/use a Render **Web Service** connected to the GitHub repository containing these files at its root.

- Root Directory: leave blank if these files are at repository root.
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`

In Render → Environment, add:
- `OPENAI_API_KEY` = your API key
- `OPENAI_MODEL` = `gpt-4o-mini` (or another model available to your API account)

Then deploy the latest commit.

## Test
- `/` should show the DEMIO interface.
- `/health` should return JSON with `status: online`.
- `ai_configured` should be `true` after adding the API key.

## Important limitations
- DEMIO does not have unrestricted access to your computer or everything you do.
- Microphone access starts only when you press Start Listening and approve the browser permission.
- Image access is limited to images you explicitly attach.
- Voice recognition depends on browser support.
- Variables are stored in this browser's local storage, not in a secure cloud database.
- The text adventure and mentor use the configured AI API. The trivia quiz is local.
- AI API usage may incur charges. A ChatGPT subscription does not automatically include API credits.
- This is a starter personal AI web app, not a complete replacement for every ChatGPT capability.
