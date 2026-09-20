"""Aufteilung der Kameraliste auf blaetterbare Seiten. Ohne I/O, damit ohne Display testbar."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Aufteilung:
    seiten: tuple
    pro_seite: int


def teile(kameras, pro_seite):
    if pro_seite < 1:
        raise ValueError("pro_seite muss mindestens 1 sein")
    kameras = tuple(kameras)
    seiten = tuple(
        kameras[anfang : anfang + pro_seite]
        for anfang in range(0, len(kameras), pro_seite)
    )
    # Eine leere Kameraliste ergibt null Seiten, und der Stack haette dann kein
    # Kind zum Anzeigen. config.lade() laesst das nicht zu, hier trotzdem
    # abgefangen, damit das Modul allein tragfaehig bleibt.
    return Aufteilung(seiten=seiten or ((),), pro_seite=pro_seite)


def seite_mit(aufteilung, kamera_name):
    """Index der Seite mit dieser Kamera, oder None.

    Bewusst None statt 0: ein unbekannter Name soll die sichtbare Seite stehen
    lassen und nicht auf die erste zurueckspringen.
    """
    for index, seite in enumerate(aufteilung.seiten):
        if any(kamera.name == kamera_name for kamera in seite):
            return index
    return None


def begrenzen(aufteilung, seite):
    return max(0, min(seite, len(aufteilung.seiten) - 1))
