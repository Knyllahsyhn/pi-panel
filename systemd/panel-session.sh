#!/bin/sh
# Wird von xinit als X-Sitzung gestartet.
# Bildschirmschoner und Energieverwaltung aus, das Panel soll dauerhaft an sein.
xset s off
xset s noblank
xset -dpms
exec python3 -m panel.main
