import pytest
from panel.config import Kamera
from panel.seiten import begrenzen, seite_mit, teile


def kams(*namen):
    return [Kamera(name=n, label=n.title(), springt=False) for n in namen]


NEUN = kams(
    "klingel",
    "haustuer",
    "einfahrt1",
    "einfahrt2",
    "pergola",
    "garten",
    "neu1",
    "neu2",
    "neu3",
)


def test_glatte_teilung():
    a = teile(kams("a", "b", "c", "d"), 2)
    assert [[k.name for k in s] for s in a.seiten] == [["a", "b"], ["c", "d"]]


def test_ungerade_teilung_macht_letzte_seite_kuerzer():
    a = teile(NEUN, 5)
    assert [len(s) for s in a.seiten] == [5, 4]
    assert a.seiten[1][0].name == "garten"


def test_pro_seite_gleich_anzahl_ergibt_eine_seite():
    # Der Fall, den ein fehlender Konfigschluessel erzeugt. Eine leere zweite
    # Seite waere hier der klassische Off-by-one.
    a = teile(NEUN, len(NEUN))
    assert len(a.seiten) == 1
    assert len(a.seiten[0]) == 9


def test_pro_seite_groesser_als_liste_ergibt_eine_seite():
    a = teile(kams("a", "b", "c"), 5)
    assert len(a.seiten) == 1
    assert len(a.seiten[0]) == 3


def test_leere_liste_ergibt_eine_leere_seite():
    # Der Stack braucht immer ein Kind zum Anzeigen.
    a = teile([], 5)
    assert a.seiten == ((),)


def test_pro_seite_unter_eins_ist_fehler():
    with pytest.raises(ValueError):
        teile(NEUN, 0)


def test_seite_mit_findet_erste_seite():
    assert seite_mit(teile(NEUN, 5), "klingel") == 0


def test_seite_mit_findet_letzte_seite():
    assert seite_mit(teile(NEUN, 5), "neu3") == 1


def test_seite_mit_unbekannter_kamera_ist_none():
    assert seite_mit(teile(NEUN, 5), "keller") is None


def test_begrenzen_klemmt_nach_unten():
    assert begrenzen(teile(NEUN, 5), -1) == 0


def test_begrenzen_klemmt_nach_oben():
    assert begrenzen(teile(NEUN, 5), 7) == 1


def test_begrenzen_laesst_gueltige_seite_stehen():
    assert begrenzen(teile(NEUN, 5), 1) == 1
