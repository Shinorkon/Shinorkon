#!/data/data/com.termux/files/usr/bin/bash
# Usage: zimyo.sh in|out
# Logs in, checks current status, punches only if the state needs to change.
set -u
ACTION="${1:-}"
[ "$ACTION" = in ] || [ "$ACTION" = out ] || { echo "usage: $0 in|out"; exit 1; }

CONF="$HOME/.zimyo.conf"   # contains: ZIMYO_USER='you@example.com'  ZIMYO_PASS='...'
. "$CONF" || exit 1

BASE="https://www.zimyo.work/apiv2"
say() { echo "$*"; command -v termux-toast >/dev/null && termux-toast "Zimyo: $*"; }

login=$(curl -sS -X POST "$BASE/login_api" \
  -H 'Content-Type: application/json' -H 'Accept: application/json' \
  -H 'app_name: account' -H 'app_lang: en' \
  -d "$(jq -n --arg u "$ZIMYO_USER" --arg p "$ZIMYO_PASS" '{username:$u,password:$p}')") \
  || { say "network error"; exit 1; }

TOKEN=$(jq -r '.data.token // empty' <<<"$login")
EMP=$(jq -r '.data.auth_user_detail.user_emp_id // .data.auth.user_emp_id // empty' <<<"$login")
if [ -z "$TOKEN" ] || [ -z "$EMP" ]; then
  if [ "$(jq -r '.data.show_otp_input // false' <<<"$login")" = true ]; then
    say "login needs OTP - not supported"
  else
    say "login failed: $(jq -r '.message // "unknown"' <<<"$login")"
  fi
  exit 1
fi

post() { curl -sS -X POST "$BASE/auth/hrms/$1" -H "token: $TOKEN" \
  -H 'Content-Type: application/json' -H 'Accept: application/json' -d "$2"; }

st=$(post check-clock-in-out-status "$(jq -n --arg e "$EMP" '{EMP_ID:$e}')")
STATE=$(jq -r '.data.attendance.IN_OUT_STATUS // "none"' <<<"$st")
DATE=$(jq -r '.data.attendance.DATE // empty' <<<"$st")

if [ "$ACTION" = in ] && [ "$STATE" = In ]; then say "already clocked in"; exit 0; fi
if [ "$ACTION" = out ] && [ "$STATE" != In ]; then say "not clocked in, nothing to do"; exit 0; fi

res=$(post clock-in-out "$(jq -n --arg e "$EMP" --arg d "$DATE" \
  '{EMP_ID:$e,SOURCE:"Web",DATE:$d,PLACE:""}')")
if [ "$(jq -r '.error' <<<"$res")" = false ]; then
  say "clocked $ACTION - $(jq -r '.data.showmessage // .message' <<<"$res")"
else
  say "failed: $(jq -r '.message' <<<"$res")"; exit 1
fi
