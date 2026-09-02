"""Verbindet Konfiguration, Zustandsmaschine, Player, Ereignisse und Oberflaeche."""

import logging
import sys
import threading
import time

from gi.repository import GLib

from panel import events, state
from panel.auth import Anmeldung
from panel.config import KonfigFehler, lade, stream_url
from panel.player import Player, mpv_starten
from panel.ui import Fenster

KONFIGPFAD = "/etc/panel/panel.yaml"
TICK_MS = 1000
NEUVERSUCH_MS = 3000
HEADER_INTERVALL_S = 600
HEADER_NEUVERSUCH_S = 30

log = logging.getLogger("panel")


class Panel:
    def __init__(self, konfig):
        self._konfig = konfig
        self._zustand = state.start(konfig.regeln, time.monotonic())
        self._player = None
        self._neuversuch_id = None
        self._header = None
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
            lambda: mpv_starten(
                wid,
                tls_verify=self._konfig.frigate.tls_verify,
                hwdec=self._konfig.quelle.get("hwdec", "auto-safe"),
            ),
            bei_streamende=self._bei_streamende,
        )
        threading.Thread(target=self._player.beobachten, daemon=True).start()
        if self._anmeldung is not None:
            threading.Thread(target=self._anmeldeschleife, daemon=True).start()
        self._anwenden()
        GLib.timeout_add(TICK_MS, self._tick)
        events.verbinde(self._konfig, self._bei_person)
        return False

    def _anmeldeschleife(self):
        """Holt das Token abseits des GTK-Threads, damit die Oberflaeche nie einfriert."""
        while True:
            try:
                neu = self._anmeldung.header()
            except Exception:
                # Breit gefangen: stirbt dieser Thread, bekommt das Panel nie
                # wieder ein Token und zeigt bis zum Neustart nichts an.
                log.exception("Anmeldung an Frigate fehlgeschlagen")
                time.sleep(HEADER_NEUVERSUCH_S)
                continue
            erstmalig = self._header is None
            self._header = neu
            if erstmalig:
                GLib.idle_add(self._erneut_laden)
            time.sleep(HEADER_INTERVALL_S)

    def _bei_knopfdruck(self, kamera):
        # Bewusst ohne Kameravergleich: ein Knopfdruck laedt immer neu, damit ein
        # eingefrorenes Bild sich durch Antippen wiederbeleben laesst.
        self._zustand = state.bei_touch(
            self._zustand, self._konfig.regeln, kamera, time.monotonic()
        )
        self._anwenden()

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
        self._neuversuch_planen()
        return False

    def _neuversuch_planen(self):
        # Ohne diese Sperre legt jedes end-file einen weiteren Timer an, und ein
        # flatternder Stream schaukelt sich in immer mehr parallele Neuversuche.
        if self._neuversuch_id is None:
            self._neuversuch_id = GLib.timeout_add(NEUVERSUCH_MS, self._erneut_laden)

    def _erneut_laden(self):
        self._neuversuch_id = None
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
        # Zwischen show_all() und dem Idle-Rueckruf gibt es noch keinen Player,
        # ein Touch in diesem Fenster darf nicht abstuerzen.
        if self._player is None:
            return
        kamera = self._zustand.kamera
        if self._anmeldung is not None:
            if self._header is None:
                self._fenster.zeige_status("Anmeldung laeuft")
                self._neuversuch_planen()
                return
            self._player.setze_header([self._header])
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
