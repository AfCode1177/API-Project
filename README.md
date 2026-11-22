Skincare Bot (Routine Auditor)

A web-based AI agent that checks a user's skincare routine for ingredient conflicts, finds missing steps, and orders an AM/PM routine. It uses the Gemini API with function calling: the model decides which tools to call, and the server runs them against a local ingredient and conflict-rules table.

Cosmetic guidance only. Not medical advice.

Repository contents
app.py - Flask backend, Gemini agent loop, and security controls (rate limiting, input caps, output scanning, security headers)
rules.py - ingredient table, conflict rules, and the three agent tools (lookup_ingredient, check_conflicts, build_routine)
static/index.html, static/style.css, static/app.js - browser chat interface
test_app.py - automated tests (no API calls needed)
requirements.txt - Python dependencies
.env.example - template for the environment file (contains no secrets)
.gitignore - keeps .env, .venv/ and caches out of the repository
Dependencies

Python 3.10 or newer, plus the packages in requirements.txt: Flask, Flask-Limiter, python-dotenv, google-genai, cryptography (for the local HTTPS certificate), gunicorn, and pytest.

Setup
Get a Gemini API key from Google AI Studio.
Clone the repository and open a terminal in the project folder.
Create and activate a virtual environment, then install the dependencies.

Windows (cmd):

py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

Never commit .env. It is listed in .gitignore.

Run
python app.py
With USE_HTTPS=1, the app serves HTTPS using a self-signed certificate generated at startup. Browsers show a certificate warning, which you can click through for testing.
Open https://127.0.0.1:5000 on the same machine.
To let other machines on the network connect, the server must listen on all interfaces. Change the host argument in the last line of app.py from 127.0.0.1 to 0.0.0.0, and allow TCP port 5000 through the host firewall. Then browse to https://<server-ip>:5000.
Tests
pytest -v

The tests cover the tools, input limits, rate limiting, security headers, output leak scanning, and the tool allow-list. They run without calling Gemini.

Security notes
The API key is read from the environment on the server and is never sent to the browser.
User text is treated as data, and replies are rendered as plain text, never HTML.
Limits: 2,000 characters per message, 16 KB request bodies, 15 requests per minute and 200 per day per IP, and at most 6 model and tool round trips per request.
Only three allow-listed tools can run.
Known limitations
The ingredient table is small, and many rule sources are still placeholders to be completed.
Budget suggestions come from the model's general knowledge, not from the tools.
Chat history is kept in server memory and resets on restart.
There is no user login.
Prompt injection cannot be fully prevented.
