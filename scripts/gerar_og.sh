#!/bin/sh
# Gera site/og.png (1200x630) a partir de scripts/og.html usando o Chrome em modo headless.
cd "$(dirname "$0")/.." || exit 1
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --window-size=1200,630 --virtual-time-budget=5000 \
  --screenshot="$PWD/site/og.png" "file://$PWD/scripts/og.html"
