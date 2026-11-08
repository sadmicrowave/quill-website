#!/bin/zsh
# Record one clip of the live Quill app (and Numbers, where the clip needs it) as window captures.
#
#   promo/record_clip.sh <dictate|helper|learns|mini> [seconds]
#
# Starts a fresh demo Quill (its own throw-away settings, so nothing you taught your real Quill is touched), opens the sample
# workbook in Numbers when the clip needs it, starts the window recorders, and lets the demo scenario run by itself
# (QUILL_DEMO_SCENARIO). The frames land in promo/takes/<clip>/<window>/ with a times.txt each (the host clock, to sync them).
# Needs: the built app (../quill-dictation-app/dist/Quill.app), promo/tools/build.sh run once, and the Screen Recording permission
# for the terminal.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
CLIP="$1"
APP="${QUILL_APP:-$HERE/../../quill-dictation-app/dist/Quill.app}"
DEMO="$HERE/takes/_demo"
OUT="$HERE/takes/$CLIP"
REC="$HERE/tools/skgrab"
[ -x "$REC" ] || { echo "build the recorder first: promo/tools/build.sh"; exit 1; }

case "$CLIP" in
  dictate) NUMBERS=1; SCENARIO=clip_dictate; SECS=${2:-58}; TARGETS=("numbers" "main") ;;
  helper)  NUMBERS=1; SCENARIO=clip_helper;  SECS=${2:-62}; TARGETS=("main" "helper") ;;
  learns)  NUMBERS=1; SCENARIO=clip_learns;  SECS=${2:-84}; TARGETS=("main" "helper" "settings") ;;
  mini)    NUMBERS=1; SCENARIO=clip_mini;    SECS=${2:-56}; TARGETS=("numbers" "main") ;;
  *) echo "unknown clip: $CLIP"; exit 1 ;;
esac

pkill -x Quill 2>/dev/null || true; sleep 1
osascript -l JavaScript -e 'const n=Application("Numbers"); for (const d of n.documents()) { if (d.name().indexOf("Demo Inventory")===0) d.close({saving:"no"}); }' 2>/dev/null || true
rm -rf "$DEMO"; mkdir -p "$DEMO"; rm -rf "$OUT"; mkdir -p "$OUT"
open -n --env QUILL_DEMO_DIR="$DEMO" --env QUILL_DEMO_AUTORUN=${AUTORUN:-28} --env QUILL_DEMO_SCENARIO="$SCENARIO" "$APP" --args --demo
sleep 7
if [ "$NUMBERS" = "1" ]; then
  osascript -l JavaScript -e 'const n=Application("Numbers"); n.open(Path("'"$DEMO"'/Demo Inventory.xlsx")); delay(4); n.windows()[0].bounds={x:40,y:60,width:1180,height:760};' >/dev/null
  # the sample's drop-down lists show as small blue arrows in every cell in Numbers: plain cells for a recording (this document only)
  osascript -l JavaScript -e 'const n=Application("Numbers"); for (const d of n.documents()) { if (d.name().indexOf("Demo Inventory")===0) d.sheets[0].tables[0].cellRange.format="text"; }' >/dev/null
fi
osascript -e 'tell application "Quill" to activate' >/dev/null

ARGS=()
for t in $TARGETS; do
  case "$t" in
    numbers)  ARGS+=("com.apple.Numbers:Demo Inventory|$OUT/numbers|0|$SECS") ;;
    main)     ARGS+=("com.quill.app:=Quill|$OUT/main|0|$SECS") ;;
    helper)   ARGS+=("com.quill.app:Term Helper|$OUT/helper|0|$SECS") ;;
    settings) ARGS+=("com.quill.app:Quill Settings|$OUT/settings|0|$SECS") ;;
  esac
done
"$REC" 24 "${ARGS[@]}"
pkill -x Quill 2>/dev/null || true
echo "recorded $CLIP into $OUT"
