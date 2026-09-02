#!/bin/sh
# Wird von xinit als X-Sitzung gestartet.
set -e

# Selbst lokalisieren, damit das Skript nicht vom Arbeitsverzeichnis der Unit
# abhaengt. Sonst scheitert python3 -m panel.main mit "No module named panel".
ZIEL="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ZIEL"

# Bildschirmschoner und Energieverwaltung aus, das Panel soll dauerhaft an sein.
xset s off || true
xset s noblank || true
xset -dpms || true

echo "panel-session: starte aus $ZIEL"
exec python3 -m panel.main
