# Zimyo clock in/out home-screen widget (Android)

1. Install **Termux**, **Termux:Widget** and **Termux:API** from F-Droid (not Play Store).
2. In Termux: `pkg install curl jq termux-api`
3. Create credentials (keep private):
   ```
   cat > ~/.zimyo.conf <<'X'
   ZIMYO_USER='you@example.com'
   ZIMYO_PASS='your-password'
   X
   chmod 600 ~/.zimyo.conf
   ```
4. Install the buttons:
   ```
   mkdir -p ~/.shortcuts
   cp zimyo.sh ~/.zimyo.sh && chmod +x ~/.zimyo.sh
   printf '#!/data/data/com.termux/files/usr/bin/bash\n~/.zimyo.sh in\n'  > ~/.shortcuts/"Clock In"
   printf '#!/data/data/com.termux/files/usr/bin/bash\n~/.zimyo.sh out\n' > ~/.shortcuts/"Clock Out"
   chmod +x ~/.shortcuts/*
   ```
5. Long-press home screen -> Widgets -> Termux:Widget -> place it. Tap a button to punch.

Notes: no OTP/SSO support. Endpoints were found from the ESS web app, not an official
API, so they may change. The script skips the punch if you're already in the requested state.
