import json

from panel.player import Player


class FakeSocket:
    def __init__(self, scheitert_bei=()):
        self.gesendet = []
        self.scheitert_bei = set(scheitert_bei)
        self.geschlossen = False

    def sendall(self, daten):
        if len(self.gesendet) in self.scheitert_bei:
            raise BrokenPipeError("kaputt")
        self.gesendet.append(daten)

    def close(self):
        self.geschlossen = True


class FakeStarter:
    def __init__(self, scheitert_bei=()):
        self.starts = 0
        self.scheitert_bei = scheitert_bei
        self.letzter = None

    def __call__(self):
        self.starts += 1
        self.letzter = FakeSocket(scheitert_bei=self.scheitert_bei)
        return self.letzter


def befehle(starter):
    return [json.loads(z.decode())["command"] for z in starter.letzter.gesendet]


def test_zeige_sendet_loadfile():
    starter = FakeStarter()
    Player(starter, warte=lambda _: None).zeige("rtsp://host/cam")
    assert befehle(starter) == [["loadfile", "rtsp://host/cam", "replace"]]


def test_setze_header_setzt_property():
    starter = FakeStarter()
    p = Player(starter, warte=lambda _: None)
    p.setze_header(["Authorization: Bearer T1"])
    assert befehle(starter) == [
        ["set_property", "http-header-fields", ["Authorization: Bearer T1"]]
    ]


def test_schreibfehler_loest_neustart_aus():
    starter = FakeStarter(scheitert_bei=(0,))
    Player(starter, warte=lambda _: None).zeige("rtsp://host/cam")
    assert starter.starts == 2


def test_wartezeit_waechst_bei_wiederholtem_fehlschlag():
    gesammelt = []
    p = Player(FakeStarter(), warte=gesammelt.append)
    p._backoff_s = 1.0
    p._fehler()
    p._fehler()
    assert gesammelt[1] > gesammelt[0]


def test_endfile_ruft_rueckruf():
    gesehen = []
    p = Player(FakeStarter(), warte=lambda _: None, bei_streamende=lambda: gesehen.append(1))
    p.verarbeite_ereignis(b'{"event":"end-file","reason":"eof"}')
    assert gesehen == [1]


def test_anderes_ereignis_ruft_nicht():
    gesehen = []
    p = Player(FakeStarter(), warte=lambda _: None, bei_streamende=lambda: gesehen.append(1))
    p.verarbeite_ereignis(b'{"event":"property-change","name":"pause"}')
    assert gesehen == []


def test_unlesbare_zeile_ruft_nicht():
    gesehen = []
    p = Player(FakeStarter(), warte=lambda _: None, bei_streamende=lambda: gesehen.append(1))
    p.verarbeite_ereignis(b"nicht json")
    assert gesehen == []
