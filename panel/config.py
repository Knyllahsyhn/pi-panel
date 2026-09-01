"""Laedt panel.yaml, validiert und stellt fertige Objekte bereit."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from panel.state import Regeln


class KonfigFehler(Exception):
    pass


@dataclass
class Zugang:
    host_oder_url: str
    user: str
    passwort: str = field(repr=False)
    port: int = 0
    tls_verify: bool = True
    topic_prefix: str = "frigate"


@dataclass(frozen=True)
class Kamera:
    name: str
    label: str
    springt: bool


@dataclass
class Konfig:
    frigate: Zugang
    mqtt: Zugang
    regeln: Regeln
    kameras: list
    quelle: dict


def _pflicht(daten, pfad):
    wert = daten
    for teil in pfad.split("."):
        if not isinstance(wert, dict) or teil not in wert or wert[teil] is None:
            raise KonfigFehler("Pflichtfeld fehlt oder ist leer: %s" % pfad)
        wert = wert[teil]
    return wert


def _passwort(pfad):
    try:
        return Path(pfad).read_text().strip()
    except OSError as fehler:
        raise KonfigFehler("Passwortdatei nicht lesbar: %s" % pfad) from fehler


def lade(pfad):
    try:
        roh = yaml.safe_load(Path(pfad).read_text())
    except (OSError, yaml.YAMLError) as fehler:
        raise KonfigFehler("panel.yaml nicht lesbar: %s" % fehler) from fehler
    if not isinstance(roh, dict):
        raise KonfigFehler("panel.yaml ist leer oder kein Mapping")

    kameras = [
        Kamera(
            name=_pflicht(eintrag, "name"),
            label=_pflicht(eintrag, "label"),
            springt=bool(eintrag.get("springt", False)),
        )
        for eintrag in _pflicht(roh, "kameras")
    ]
    if not kameras:
        raise KonfigFehler("kameras ist leer")

    basis = _pflicht(roh, "anzeige.basis_kamera")
    namen = {k.name for k in kameras}
    if basis not in namen:
        raise KonfigFehler("basis_kamera %s steht nicht in kameras" % basis)

    regeln = Regeln(
        basis_kamera=basis,
        rueckfall_manuell_s=float(_pflicht(roh, "anzeige.rueckfall_manuell_s")),
        rueckfall_auto_s=float(_pflicht(roh, "anzeige.rueckfall_auto_s")),
        sperrzeit_auto_s=float(_pflicht(roh, "anzeige.sperrzeit_auto_s")),
        sprungliste=frozenset(k.name for k in kameras if k.springt),
    )

    quelle = _pflicht(roh, "quelle")
    if quelle.get("modus") not in ("mjpeg", "rtsp"):
        raise KonfigFehler("quelle.modus muss mjpeg oder rtsp sein")

    return Konfig(
        frigate=Zugang(
            host_oder_url=_pflicht(roh, "frigate.base_url").rstrip("/"),
            user=_pflicht(roh, "frigate.user"),
            passwort=_passwort(_pflicht(roh, "frigate.password_file")),
            tls_verify=bool(roh["frigate"].get("tls_verify", True)),
        ),
        mqtt=Zugang(
            host_oder_url=_pflicht(roh, "mqtt.host"),
            port=int(_pflicht(roh, "mqtt.port")),
            user=_pflicht(roh, "mqtt.user"),
            passwort=_passwort(_pflicht(roh, "mqtt.password_file")),
            topic_prefix=roh["mqtt"].get("topic_prefix", "frigate"),
        ),
        regeln=regeln,
        kameras=kameras,
        quelle=quelle,
    )


def stream_url(konfig, kamera):
    if konfig.quelle["modus"] == "mjpeg":
        pfad = konfig.quelle["mjpeg"]["pfad"].format(cam=kamera)
        return konfig.frigate.host_oder_url + pfad
    rtsp = konfig.quelle["rtsp"]
    return "%s/%s%s" % (rtsp["basis"].rstrip("/"), kamera, rtsp.get("suffix", ""))
