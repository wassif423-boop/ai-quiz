# AI Quiz Generator (Gemini version)

This version uses the Gemini Developer API instead of OpenAI.

## Run locally
1. Install Python 3.10 or newer.
2. Run `pip install -r requirements.txt`.
3. Create `.streamlit/secrets.toml` with:

```toml
GEMINI_API_KEY = "your_gemini_api_key_here"
```

4. Run `streamlit run app.py`.

## Deploy on Streamlit Community Cloud
1. Replace the old `app.py` and `requirements.txt` in your existing GitHub repository with these versions.
2. In Streamlit Community Cloud, open your app → Settings → Secrets.
3. Replace the old OpenAI secret with:

```toml
GEMINI_API_KEY = "your_gemini_api_key_here"
```

4. Save and reboot/redeploy the app.

## Important
- Get a Gemini API key from Google AI Studio with help from a parent/guardian.
- Check current model availability and free-tier limits in Google AI Studio.
- Free-tier prompts may be used by Google to improve products; do not send private or sensitive information.
- Never put API keys in GitHub or share them in chat.
