# pi-panel

Kamera-Panel fuer Raspberry Pi. Zeigt die Streams eines Frigate-NVR auf einem
7-Zoll-Touchscreen. Grundbild ist die Klingelkamera, Umschalten per Touch,
automatischer Sprung bei Personenerkennung.

Entwurf und Netzkontext liegen ausserhalb dieses Repos.

## Voraussetzungen

Raspberry Pi OS mit X11. Pakete siehe `install.sh`.

## Installation

Siehe `install.sh`.

## Konfiguration

`panel.yaml.example` nach `/etc/panel/panel.yaml` kopieren und anpassen.
Passwoerter stehen in eigenen Dateien, nicht in der YAML.

## Betrieb

    systemctl status panel
    journalctl -u panel -f

## Fehlersuche

Folgt.
