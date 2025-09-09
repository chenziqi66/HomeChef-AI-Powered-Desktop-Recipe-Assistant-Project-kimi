# HomeChef — AI-Powered Desktop Recipe Assistant (PyQt5)

## Overview
HomeChef is a beginner-friendly PyQt5 desktop application that helps you:
- Manage and browse recipes (local SQLite database).
- Find recipes using ingredients you have.
- Maintain a pantry and auto-generate a grocery list.
- Ask an AI cooking assistant (OpenAI GPT) for suggestions, steps, and tips.
- Run a step-by-step cooking guide with contextual tips.

This package contains a working baseline implementation you can extend.

---

## What's included (files)
- `main.py` — The PyQt5 application (entry point).
- `db.py` — SQLite helper: initialization and simple CRUD.
- `gpt_client.py` — Simple wrapper for calling the OpenAI GPT API (graceful fallback if API key not present).
- `seed_recipes.json` — A few seeded recipes used to populate the database on first run.
- `requirements.txt` — Python packages to install.
- `README.md` — (this file).
- `HomeChef.zip` — this archive (the project folder compressed).

---

## Quick setup (Windows / macOS / Linux)
1. Install Python 3.8+ (https://www.python.org/downloads/).
2. Open VS Code and **Open Folder** → select the `HomeChef` folder from this archive.
3. Create and activate a virtual environment.

On Windows (PowerShell):
```powershell
python -m venv venv
.env\Scripts\Activate.ps1
pip install -r requirements.txt
```

On macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. **OpenAI API key** (optional but required for AI features):
- Obtain an API key from OpenAI and set it as an environment variable:
  - Windows (PowerShell): `$env:OPENAI_API_KEY = "sk-..."` (or permanently via System Settings)
  - macOS / Linux: `export OPENAI_API_KEY="sk-..."`
- Alternatively create a `.env` file with `OPENAI_API_KEY=sk-...` (the app loads it automatically if python-dotenv is installed).

5. Run the app:
```bash
python main.py
```

---

## Using in VS Code
- Open the folder in VS Code.
- Make sure the Python interpreter is the virtual environment you created (`Ctrl+Shift+P` → Python: Select Interpreter).
- Use the integrated terminal to run `python main.py`.
- You can also set up a debug configuration to run `main.py`.

---

## How the OpenAI features work
- If `OPENAI_API_KEY` is set, the app uses the OpenAI Chat API to:
  - Suggest recipe ideas when no exact match is found.
  - Answer cooking/chatbot questions.
  - Provide contextual tips during step-by-step cooking.
- If no API key is present, the app uses simple programmed fallbacks so you can still use core features locally.

---

## Next steps / Extending the app
- Add more recipes to `seed_recipes.json` or add a UI to create recipes.
- Improve the ingredient-matching algorithm.
- Add images and richer media.
- Add authentication / user profiles.
- Package into an executable with PyInstaller:
  `pyinstaller --onefile main.py`

---

If you get any errors running the app, paste the full traceback here and I'll help debug it.
