#!/bin/sh
# Applies a candidate host configuration only if NGINX accepts it, otherwise keeps the last working one.
# Usage: apply_generated.sh <generated folder> <nginx test command> <nginx reload command>
GENERATED="$1"
TEST_COMMAND="$2"
RELOAD_COMMAND="$3"

[ -f "$GENERATED/live/sites.conf" ] || { mkdir -p "$GENERATED/live/certs"; : > "$GENERATED/live/sites.conf"; }
[ -d "$GENERATED/candidate" ] || exit 0

rm -rf "$GENERATED/previous"
mv "$GENERATED/live" "$GENERATED/previous"
mv "$GENERATED/candidate" "$GENERATED/live"

if OUTPUT=$($TEST_COMMAND 2>&1); then
  rm -f "$GENERATED/last_error" "$GENERATED/rejected_version"
  rm -rf "$GENERATED/previous"
  $RELOAD_COMMAND
else
  # Recorded so core-service does not write the same rejected candidate again.
  cp "$GENERATED/live/version" "$GENERATED/rejected_version" 2>/dev/null
  rm -rf "$GENERATED/live"
  mv "$GENERATED/previous" "$GENERATED/live"
  printf '%s\n' "$OUTPUT" | tail -5 > "$GENERATED/last_error"
  exit 1
fi
