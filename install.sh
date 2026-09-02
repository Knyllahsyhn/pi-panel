#!/usr/bin/env bash
# Installiert das Panel auf einem Raspberry Pi mit Raspberry Pi OS.
# Das Repo bleibt an Ort und Stelle, ein Update ist ein git pull plus Neustart.
set -euo pipefail

ZIEL="$(cd "$(dirname "$0")" && pwd)"
KONFIG=/etc/panel

if [ "$(id -u)" -ne 0 ]; then
  echo "Bitte als root ausfuehren." >&2
  exit 1
fi

if [ "$(. /etc/os-release 2>/dev/null && echo "${ID:-}")" != "raspbian" ] \
   && [ ! -e /proc/device-tree/model ]; then
  echo "Warnung: sieht nicht nach einem Raspberry Pi aus, mache trotzdem weiter." >&2
fi

echo "== Pakete =="
apt-get update
apt-get install -y --no-install-recommends \
  mpv python3 python3-gi python3-yaml python3-paho-mqtt python3-requests \
  gir1.2-gtk-3.0 xserver-xorg xserver-xorg-legacy xinit x11-xserver-utils

echo "== Benutzer =="
id -u panel >/dev/null 2>&1 \
  || useradd --system --create-home --shell /usr/sbin/nologin panel
usermod -aG video,input,tty panel

echo "== Konfiguration =="
mkdir -p "$KONFIG"
if [ ! -f "$KONFIG/panel.yaml" ]; then
  cp "$ZIEL/panel.yaml.example" "$KONFIG/panel.yaml"
  echo "   $KONFIG/panel.yaml aus der Vorlage angelegt, bitte anpassen."
fi
# Der Dienst laeuft als panel, deshalb Gruppenleserecht statt 600.
chown root:panel "$KONFIG/panel.yaml"
chmod 640 "$KONFIG/panel.yaml"
for datei in "$KONFIG"/*.pass; do
  [ -e "$datei" ] || continue
  chown root:panel "$datei"
  chmod 640 "$datei"
done

echo "== X-Sitzung =="
# Ohne das darf nur die Konsolensitzung einen X-Server starten, der
# systemd-Dienst also nicht.
if [ -f /etc/X11/Xwrapper.config ]; then
  sed -i 's/^allowed_users=.*/allowed_users=anybody/' /etc/X11/Xwrapper.config
  grep -q '^allowed_users=' /etc/X11/Xwrapper.config \
    || echo "allowed_users=anybody" >> /etc/X11/Xwrapper.config
else
  echo "allowed_users=anybody" > /etc/X11/Xwrapper.config
fi
chmod +x "$ZIEL/systemd/panel-session.sh"

echo "== Dienst =="
# Desktop-Sitzung nicht mehr automatisch starten. Per SSH bleibt alles erreichbar.
systemctl set-default multi-user.target
sed "s|__ZIEL__|$ZIEL|g" "$ZIEL/systemd/panel.service" > /etc/systemd/system/panel.service
chmod 644 /etc/systemd/system/panel.service
systemctl daemon-reload
systemctl enable panel

echo
echo "Fertig. Naechste Schritte:"
echo "  1. $KONFIG/panel.yaml anpassen"
echo "  2. Passwortdatei anlegen:"
echo "       printf '%s' 'MQTT_PASSWORT' > $KONFIG/mqtt.pass"
echo "       chown root:panel $KONFIG/mqtt.pass && chmod 640 $KONFIG/mqtt.pass"
echo "  3. systemctl start panel"
