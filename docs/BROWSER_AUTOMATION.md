# Browser Automation (Playwright)

This module adds end-to-end registration automation:
- Launches a Chromium browser via Playwright (headless or headed)
- Fills sign-up forms (email/username/password)
- Waits and polls Microsoft Graph for verification email
- Completes verification via link or OTP code
- Persists cookies and storage state to the database
- Always captures debug screenshots with red outlines on interacted elements

Quick start
1) Install dependencies:
   pip install -r requirements.txt
   python -m playwright install

2) Run the CLI register command:
   python -m servbot register SERVICE --url SIGNUP_URL --provision outlook --headed \
     --email-selector "input[name=email]" \
     --password-selector "input[name=password]" \
     --submit-selector "button[type=submit]" \
     --otp-selector "input[name=otp]" \
     --success-selector ".account-home"

Notes
- Screenshots are saved under servbot/data/screenshots/run-<timestamp>-<id>/
- Interacted elements are outlined in red to aid debugging.
- Registrations are saved in the registrations table with cookies_json and storage_state_json.
- For provisioning, ensure FLASHMAIL_CARD is configured (see existing docs/).
