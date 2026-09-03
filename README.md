# pi-panel

Kamera-Panel für Raspberry Pi. Zeigt die Streams eines Frigate-NVR auf einem
7-Zoll-Touchscreen.

Grundbild ist die Klingelkamera. Ein Druck auf einen Knopf schaltet um, nach
einer Minute ohne Bedienung faellt die Anzeige zurueck. Erkennt Frigate eine
Person auf einer dafuer freigegebenen Kamera, springt das Panel selbsttaetig
dorthin und kehrt danach zurueck.

Der Broker ist ein Komfortmerkmal. Faellt er aus, laeuft das Panel normal
weiter, nur ohne den automatischen Sprung.

## Voraussetzungen

- Raspberry Pi mit Raspberry Pi OS, **X11** (nicht Wayland). Pruefen mit
  `echo $XDG_SESSION_TYPE`, umstellen ueber `raspi-config`.
- Erreichbar im Netz: go2rtc-RTSP auf `<nvr>:8554` und MQTT auf `<nvr>:1883`.
- Ein MQTT-Benutzer mit ausschliesslich lesendem Zugriff auf `frigate/#`.

Getestet auf einem Raspberry Pi 2B rev 1.1.

## Installation

```bash
cd /opt
sudo git clone <repo-url> pi-panel
cd pi-panel
sudo ./install.sh
```

Das Repo bleibt liegen, wo es geklont wurde. Ein Update ist `git pull` plus
`systemctl restart panel`.

Danach die Konfiguration hinterlegen:

```bash
sudo nano /etc/panel/panel.yaml
printf '%s' 'MQTT_PASSWORT' | sudo tee /etc/panel/mqtt.pass >/dev/null
sudo chown root:panel /etc/panel/mqtt.pass
sudo chmod 640 /etc/panel/mqtt.pass
sudo systemctl start panel
```

`printf` statt `echo`, damit kein Zeilenumbruch im Passwort landet.

**Zweite Passwortdatei nur im Modus `mjpeg`.** Dann meldet sich das Panel bei
Frigate an und braucht zusaetzlich `/etc/panel/frigate.pass`, mit denselben
Rechten. Im Modus `rtsp` wird sie nicht gelesen und darf fehlen.

## Konfiguration

`/etc/panel/panel.yaml`, Vorlage siehe `panel.yaml.example`.

| Feld | Bedeutung |
|---|---|
| `anzeige.basis_kamera` | Grundbild, muss in `kameras` vorkommen |
| `anzeige.rueckfall_manuell_s` | Sekunden bis zur Rueckkehr nach einem Knopfdruck |
| `anzeige.rueckfall_auto_s` | Sekunden bis zur Rueckkehr nach einem Auto-Sprung |
| `anzeige.sperrzeit_auto_s` | Ruhephase zwischen zwei Auto-Spruengen |
| `quelle.modus` | `rtsp` (Regelfall) oder `mjpeg` |
| `kameras[].name` | Name der Kamera in Frigate |
| `kameras[].label` | Beschriftung auf dem Knopf |
| `kameras[].springt` | ob eine Personenerkennung hier einen Sprung ausloest |

Passwoerter stehen nie in dieser Datei, sondern in eigenen Dateien, auf die sie
zeigt. Sie gehoeren `root:panel` mit Rechten `640`.

| Datei | Wird gebraucht |
|---|---|
| `/etc/panel/mqtt.pass` | immer |
| `/etc/panel/frigate.pass` | nur bei `quelle.modus: mjpeg` |

**`springt` sparsam setzen.** Jede Kamera an einer Strasse laesst das Panel bei
jedem Passanten umschalten. Im Zweifel nur die Kamera an der Tuer.

## Betrieb

```bash
systemctl status panel
systemctl restart panel
journalctl -u panel -f
```

Im Log steht bei jedem Wechsel, welche Kamera gezeigt wird und warum
(`basis`, `manuell`, `auto`).

## Fehlersuche

**Schwarzes Bild, sonst laeuft alles.**
Stream-URL von Hand pruefen. Der Name in `panel.yaml` ist der Frigate-Name, im
RTSP-Modus haengt das Suffix aus `quelle.rtsp.suffix` an:

```bash
mpv "rtsp://<nvr>:8554/klingel_sub"
```

Kommt hier nichts, liegt es nicht am Panel. Dann pruefen, ob `8554:8554` in der
Portmap des Frigate-Containers veroeffentlicht ist und die Firewall den Pi
durchlaesst.

**Kein automatischer Sprung, Bild aber da.**
Der Broker ist nicht erreichbar oder die Kamera steht nicht in der Sprungliste.

```bash
mosquitto_sub -h <nvr> -u <benutzer> -P <passwort> -v \
  -t 'frigate/+/person' -t 'frigate/+/person/state'
```

Kommt beim Vorbeilaufen nichts, publiziert Frigate die Zaehler unter einem
anderen Namen. Das Panel akzeptiert `frigate/<kamera>/person` mit und ohne
angehaengtes `/state`.

**Panel startet nicht, `journalctl` zeigt einen Konfigurationsfehler.**
Absicht: eine unvollstaendige `panel.yaml` laesst den Dienst gar nicht erst
starten, statt halb konfiguriert zu laufen. Die Meldung nennt das Feld.

**`Permission denied` auf `panel.yaml` oder eine `.pass`-Datei.**
Der Dienst laeuft als Benutzer `panel`, nicht als root. `chown root:panel` und
`chmod 640`.

**`Server is already active for display 0`.**
Der Displaymanager haelt noch `:0`. `systemctl set-default multi-user.target`
aendert nur das Boot-Ziel und stoppt die laufende Sitzung nicht.

```bash
sudo systemctl stop panel
sudo systemctl disable --now display-manager
sudo rm -f /tmp/.X0-lock
sudo systemctl start panel
```

**`parse_vt_settings: Cannot open /dev/tty0 (Permission denied)`.**
Xorg bekommt kein virtuelles Terminal. Die Unit braucht dafuer `PAMName=login`
zusammen mit `TTYPath=/dev/tty7`, und das `vt7` in der `ExecStart`-Zeile muss
dazu passen. Nur mit einer logind-Sitzung erhaelt Xorg Terminal, Eingabegeraete
und DRM-Zugriff.

Hilft das nicht, laesst sich Xorg mit root-Rechten starten:

```bash
echo "needs_root_rights=yes" | sudo tee -a /etc/X11/Xwrapper.config
```

Ausfuehrlichere Meldungen als im Journal stehen in
`/home/panel/.local/share/xorg/Xorg.0.log`.

**Wayland statt X11.**
Das Panel braucht X11, weil mpv per `--wid` in das GTK-Fenster eingebettet wird.
Auf Raspberry Pi OS mit Wayland belegt Xwayland bereits `:0`, `xinit` scheitert
dann mit `Server is already active for display 0`. Umstellen ueber `raspi-config`,
Advanced Options, Wayland, X11. Achtung: **wayvnc funktioniert danach nicht
mehr**, als Ersatz `x11vnc -display :0 -localhost` verwenden.

**Dienst beendet sich sofort, Neustart alle 5 Sekunden.**
`RestartSec` ist 5, das Programm steigt also unmittelbar aus. Erst die Schleife
anhalten (`systemctl stop panel`), dann den Log ohne Xorg-Rauschen ansehen:

```bash
journalctl -u panel --since "-1 min" --no-pager \
  | grep -viE 'X\.Org|LoadModule|Option "|\(II\)|\(\*\*\)'
```

Haeufigste Ursache: `python3 -m panel.main` findet das Paket nicht. Pruefen mit
`systemctl cat panel | grep -E 'WorkingDirectory|ExecStart'` -- steht dort noch
`__ZIEL__` statt eines echten Pfades, wurde die Unit von Hand kopiert, ohne den
Platzhalter zu ersetzen. `install.sh` erledigt das sonst.

**Kein X-Server, `xinit` bricht ab.**
`/etc/X11/Xwrapper.config` muss `allowed_users=anybody` enthalten, sonst darf
nur die Konsolensitzung X starten. `install.sh` setzt das.

**Bildschirm wird nach einigen Minuten dunkel.**
`systemd/panel-session.sh` schaltet Bildschirmschoner und DPMS ab. Laeuft das
Panel ohne dieses Skript, fehlt das.

## Aufbau

| Modul | Aufgabe |
|---|---|
| `panel/state.py` | Zustandsmaschine, reine Funktionen, ohne I/O |
| `panel/config.py` | `panel.yaml` laden und validieren |
| `panel/player.py` | mpv-Prozess und JSON-IPC |
| `panel/events.py` | MQTT-Abonnement und Flankenerkennung |
| `panel/auth.py` | Frigate-Token, nur im Modus `mjpeg` benutzt |
| `panel/ui.py` | GTK-Fenster, Knopfleiste, Statuszeile |
| `panel/main.py` | verbindet die Module |

mpv laeuft dauerhaft im Leerlauf und wird ueber einen Unix-Socket umgeschaltet,
statt fuer jede Kamera neu zu starten. Das vermeidet schwarze Zwischenbilder.

`state.py` kennt weder mpv noch MQTT noch GTK. Die gesamte Verhaltenslogik ist
dadurch ohne Pi, ohne Broker und ohne Bildschirm testbar.

## Tests

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/pip install pytest PyYAML paho-mqtt requests
.venv/bin/python -m pytest -q
```

Nur fuer die Entwicklung. Auf dem Pi kommen alle Abhaengigkeiten als
Debian-Pakete ueber `install.sh`.
