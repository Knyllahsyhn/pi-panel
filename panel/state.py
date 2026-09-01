"""Verhaltenslogik der Panels. Ohne I/O, damit ohne Hardware testbar."""

from dataclasses import dataclass, replace
from enum import Enum


class Modus(Enum):
    BASIS = "basis"
    MANUELL = "manuell"
    AUTO = "auto"


@dataclass(frozen=True)
class Regeln:
    basis_kamera: str
    rueckfall_manuell_s: float
    rueckfall_auto_s: float
    sperrzeit_auto_s: float
    sprungliste: frozenset


@dataclass(frozen=True)
class Zustand:
    modus: Modus
    kamera: str
    seit: float
    letzter_autosprung: float


def start(regeln, jetzt):
    return Zustand(
        modus=Modus.BASIS,
        kamera=regeln.basis_kamera,
        seit=jetzt,
        letzter_autosprung=float("-inf"),
    )


def bei_touch(zustand, regeln, kamera, jetzt):
    return replace(zustand, modus=Modus.MANUELL, kamera=kamera, seit=jetzt)


def bei_person(zustand, regeln, kamera, jetzt):
    if kamera not in regeln.sprungliste:
        return zustand
    if zustand.modus is Modus.MANUELL:
        return zustand
    # Laeuft die Person weiter vor derselben Kamera, Anzeige verlaengern
    # statt die Sperrzeit zu bemuehen.
    if zustand.modus is Modus.AUTO:
        if kamera == zustand.kamera:
            return replace(zustand, seit=jetzt)
        return zustand
    if jetzt - zustand.letzter_autosprung < regeln.sperrzeit_auto_s:
        return zustand
    return replace(
        zustand, modus=Modus.AUTO, kamera=kamera, seit=jetzt, letzter_autosprung=jetzt
    )


def bei_tick(zustand, regeln, jetzt):
    if zustand.modus is Modus.BASIS:
        return zustand
    grenze = (
        regeln.rueckfall_manuell_s
        if zustand.modus is Modus.MANUELL
        else regeln.rueckfall_auto_s
    )
    if jetzt - zustand.seit < grenze:
        return zustand
    return replace(zustand, modus=Modus.BASIS, kamera=regeln.basis_kamera, seit=jetzt)
