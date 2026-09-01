"""Startet mpv im Leerlauf und schaltet Streams ueber den JSON-IPC-Socket um."""

import json
import os
import socket
import subprocess
import time

SOCKET_PFAD = "/run/panel/mpv.sock"
MAX_BACKOFF_S = 30.0


def mpv_argumente(wid, socket_pfad, tls_verify):
    return [
        "mpv",
        "--idle=yes",
        "--input-ipc-server=%s" % socket_pfad,
        "--wid=%d" % wid,
        "--profile=low-latency",
        "--no-audio",
        "--no-osc",
        "--no-input-default-bindings",
        "--hwdec=auto-safe",
        "--tls-verify=%s" % ("yes" if tls_verify else "no"),
    ]


def mpv_starten(wid, socket_pfad=SOCKET_PFAD, tls_verify=False):
    os.makedirs(os.path.dirname(socket_pfad), exist_ok=True)
    if os.path.exists(socket_pfad):
        os.unlink(socket_pfad)
    subprocess.Popen(mpv_argumente(wid, socket_pfad, tls_verify))
    for _ in range(50):
        if os.path.exists(socket_pfad):
            break
        time.sleep(0.1)
    verbindung = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    verbindung.connect(socket_pfad)
    return verbindung


class Player:
    def __init__(self, starter, warte=time.sleep, bei_streamende=None):
        self._starter = starter
        self._warte = warte
        self._bei_streamende = bei_streamende or (lambda: None)
        self._backoff_s = 0.5
        self._socket = self._starter()

    def zeige(self, url):
        self._sende(["loadfile", url, "replace"])

    def setze_header(self, zeilen):
        self._sende(["set_property", "http-header-fields", list(zeilen)])

    def verarbeite_ereignis(self, zeile):
        try:
            daten = json.loads(zeile.decode())
        except (ValueError, UnicodeDecodeError):
            return
        if daten.get("event") == "end-file":
            self._bei_streamende()

    def beobachten(self):
        """Liest mpv-Ereignisse. Als Daemon-Thread aus main.py gestartet."""
        puffer = b""
        while True:
            try:
                daten = self._socket.recv(4096)
            except OSError:
                self._warte(1.0)
                continue
            if not daten:
                self._warte(1.0)
                continue
            puffer += daten
            while b"\n" in puffer:
                zeile, puffer = puffer.split(b"\n", 1)
                self.verarbeite_ereignis(zeile)

    def _sende(self, befehl):
        zeile = json.dumps({"command": befehl}) + "\n"
        try:
            self._socket.sendall(zeile.encode())
            self._backoff_s = 0.5
        except OSError:
            self._fehler()

    def _fehler(self):
        self._warte(self._backoff_s)
        self._backoff_s = min(self._backoff_s * 2, MAX_BACKOFF_S)
        try:
            self._socket.close()
        except OSError:
            pass
        self._socket = self._starter()
