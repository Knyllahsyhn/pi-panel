"""Verbindet Konfiguration, Zustandsmaschine, Player, Ereignisse und Oberflaeche."""

import logging
import sys
import threading
import time

from gi.repository import GLib

from panel import events, state
from panel.auth import Anmeldung, AuthFehler
from panel.config import KonfigFehler, lade, stream_url
from panel.player import Player, mpv_starten
from panel.ui import Fenster

KONFIGPFAD = "/etc/panel/panel.yaml"
TICK_MS = 1000
NEUVERSUCH_MS = 3000

log = logging.getLogger("panel")


class Panel:
    def __init__(self, konfig):
        self._konfig = konfig
        self._zustand = state.start(konfig.regeln, time.monotonic())
        self._player = None
        self._anmeldung = self._anmeldung_bauen()
        self._fenster = Fenster(konfig.kameras, self._bei_knopfdruck)

    def _anmeldung_bauen(self):
        # Variante A holt RTSP direkt von go2rtc, dort gibt es nichts anzumelden.
        if self._konfig.quelle["modus"] != "mjpeg":
            return None
        return Anmeldung(
            base_url=self._konfig.frigate.host_oder_url,
            user=self._konfig.frigate.user,
            passwort=self._konfig.frigate.passwort,
            tls_verify=self._konfig.frigate.tls_verify,
        )

    def starten(self):
        self._fenster.starten(self._nach_dem_anzeigen)

    def _nach_dem_anzeigen(self):
        wid = self._fenster.fenster_id()
        self._player = Player(
            lambda: mpv_starten(wid, tls_verify=self._konfig.frigate.tls_verify),
            bei_streamende=self._bei_streamende,
        )
        threading.Thread(target=self._player.beobachten, daemon=True).start()
        self._anwenden()
        GLib.timeout_add(TICK_MS, self._tick)
        events.verbinde(self._konfig, self._bei_person)
        return False

    def _bei_knopfdruck(self, kamera):
        self._uebernehmen(
            state.bei_touch(self._zustand, self._konfig.regeln, kamera, time.monotonic())
        )

    def _bei_person(self, kamera):
        # Kommt aus dem MQTT-Thread, deshalb in den GTK-Thread zurueckreichen.
        GLib.idle_add(self._person_im_hauptthread, kamera)

    def _person_im_hauptthread(self, kamera):
        self._uebernehmen(
            state.bei_person(self._zustand, self._konfig.regeln, kamera, time.monotonic())
        )
        return False

    def _bei_streamende(self):
        # Kommt aus dem Beobachter-Thread.
        GLib.idle_add(self._streamende_im_hauptthread)

    def _streamende_im_hauptthread(self):
        self._fenster.zeige_status("Verbindung unterbrochen, neuer Versuch")
        GLib.timeout_add(NEUVERSUCH_MS, self._erneut_laden)
        return False

    def _erneut_laden(self):
        self._anwenden()
        return False

    def _tick(self):
        self._uebernehmen(
            state.bei_tick(self._zustand, self._konfig.regeln, time.monotonic())
        )
        return True

    def _uebernehmen(self, neu):
        vorher = self._zustand.kamera
        self._zustand = neu
        if neu.kamera != vorher:
            self._anwenden()

    def _anwenden(self):
        kamera = self._zustand.kamera
        if self._anmeldung is not None:
            try:
                self._player.setze_header([self._anmeldung.header()])
            except AuthFehler as fehler:
                log.error("Anmeldung an Frigate fehlgeschlagen: %s", fehler)
                self._fenster.zeige_status("Anmeldung fehlgeschlagen")
                GLib.timeout_add(NEUVERSUCH_MS, self._erneut_laden)
                return
        self._player.zeige(stream_url(self._konfig, kamera))
        self._fenster.zeige_status("")
        log.info("zeige %s (%s)", kamera, self._zustand.modus.value)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        konfig = lade(KONFIGPFAD)
    except KonfigFehler as fehler:
        log.error("Konfiguration fehlerhaft: %s", fehler)
        return 1
    Panel(konfig).starten()
    return 0


if __name__ == "__main__":
    sys.exit(main())
