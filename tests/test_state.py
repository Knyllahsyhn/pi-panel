import pytest
from panel.state import Modus, Regeln, start, bei_touch, bei_person, bei_tick

REGELN = Regeln(
    basis_kamera="klingel",
    rueckfall_manuell_s=60.0,
    rueckfall_auto_s=30.0,
    sperrzeit_auto_s=120.0,
    sprungliste=frozenset({"klingel", "haustuer"}),
)


def test_start_zeigt_basiskamera():
    z = start(REGELN, jetzt=1000.0)
    assert z.modus is Modus.BASIS
    assert z.kamera == "klingel"


def test_touch_wechselt_nach_manuell():
    z = bei_touch(start(REGELN, 1000.0), REGELN, "pergola", jetzt=1005.0)
    assert z.modus is Modus.MANUELL
    assert z.kamera == "pergola"


def test_touch_auf_andere_kamera_setzt_timer_zurueck():
    z = bei_touch(start(REGELN, 1000.0), REGELN, "pergola", 1005.0)
    z = bei_touch(z, REGELN, "garten", jetzt=1050.0)
    assert z.kamera == "garten"
    assert z.seit == 1050.0


def test_manuell_faellt_nach_timeout_zurueck():
    z = bei_touch(start(REGELN, 1000.0), REGELN, "pergola", 1005.0)
    assert bei_tick(z, REGELN, jetzt=1064.0).modus is Modus.MANUELL
    z = bei_tick(z, REGELN, jetzt=1065.0)
    assert z.modus is Modus.BASIS
    assert z.kamera == "klingel"


def test_person_springt_aus_basis():
    z = bei_person(start(REGELN, 1000.0), REGELN, "haustuer", jetzt=1010.0)
    assert z.modus is Modus.AUTO
    assert z.kamera == "haustuer"


def test_person_ausserhalb_sprungliste_wird_ignoriert():
    a = start(REGELN, 1000.0)
    assert bei_person(a, REGELN, "pergola", jetzt=1010.0) == a


def test_person_innerhalb_sperrzeit_wird_ignoriert():
    z = bei_person(start(REGELN, 1000.0), REGELN, "haustuer", 1010.0)
    z = bei_tick(z, REGELN, jetzt=1041.0)
    assert z.modus is Modus.BASIS
    unveraendert = bei_person(z, REGELN, "haustuer", jetzt=1100.0)
    assert unveraendert == z


def test_person_nach_sperrzeit_springt_wieder():
    z = bei_person(start(REGELN, 1000.0), REGELN, "haustuer", 1010.0)
    z = bei_tick(z, REGELN, 1041.0)
    z = bei_person(z, REGELN, "haustuer", jetzt=1131.0)
    assert z.modus is Modus.AUTO


def test_person_in_manuell_wird_ignoriert():
    z = bei_touch(start(REGELN, 1000.0), REGELN, "pergola", 1005.0)
    assert bei_person(z, REGELN, "haustuer", jetzt=1010.0) == z


def test_person_auf_gleicher_kamera_in_auto_verlaengert():
    z = bei_person(start(REGELN, 1000.0), REGELN, "haustuer", 1010.0)
    z = bei_person(z, REGELN, "haustuer", jetzt=1030.0)
    assert z.modus is Modus.AUTO
    assert z.seit == 1030.0


def test_auto_faellt_nach_timeout_zurueck():
    z = bei_person(start(REGELN, 1000.0), REGELN, "haustuer", 1010.0)
    z = bei_tick(z, REGELN, jetzt=1041.0)
    assert z.modus is Modus.BASIS


def test_touch_gewinnt_gegen_auto():
    z = bei_person(start(REGELN, 1000.0), REGELN, "haustuer", 1010.0)
    z = bei_touch(z, REGELN, "garten", jetzt=1015.0)
    assert z.modus is Modus.MANUELL
    assert z.kamera == "garten"


def test_tick_in_basis_aendert_nichts():
    a = start(REGELN, 1000.0)
    assert bei_tick(a, REGELN, jetzt=99999.0) == a
