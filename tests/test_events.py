from panel.events import Entprellung


def test_null_auf_eins_loest_aus():
    gesehen = []
    e = Entprellung(gesehen.append)
    e.nachricht("frigate/klingel/person", b"0")
    e.nachricht("frigate/klingel/person", b"1")
    assert gesehen == ["klingel"]


def test_eins_auf_zwei_loest_nicht_aus():
    gesehen = []
    e = Entprellung(gesehen.append)
    e.nachricht("frigate/klingel/person", b"1")
    e.nachricht("frigate/klingel/person", b"2")
    assert gesehen == ["klingel"]


def test_erneutes_auftauchen_loest_wieder_aus():
    gesehen = []
    e = Entprellung(gesehen.append)
    e.nachricht("frigate/klingel/person", b"1")
    e.nachricht("frigate/klingel/person", b"0")
    e.nachricht("frigate/klingel/person", b"1")
    assert gesehen == ["klingel", "klingel"]


def test_kameras_werden_getrennt_gezaehlt():
    gesehen = []
    e = Entprellung(gesehen.append)
    e.nachricht("frigate/klingel/person", b"1")
    e.nachricht("frigate/garten/person", b"1")
    assert gesehen == ["klingel", "garten"]


def test_unlesbare_nutzlast_wird_verworfen():
    gesehen = []
    e = Entprellung(gesehen.append)
    e.nachricht("frigate/klingel/person", b"online")
    assert gesehen == []


def test_fremdes_topic_wird_ignoriert():
    gesehen = []
    e = Entprellung(gesehen.append)
    e.nachricht("frigate/klingel/car", b"1")
    assert gesehen == []


def test_state_suffix_loest_auch_aus():
    gesehen = []
    e = Entprellung(gesehen.append)
    e.nachricht("frigate/klingel/person/state", b"1")
    assert gesehen == ["klingel"]


def test_fremdes_viertes_segment_wird_ignoriert():
    gesehen = []
    e = Entprellung(gesehen.append)
    e.nachricht("frigate/klingel/person/threshold", b"1")
    assert gesehen == []


def test_konfigtopics_werden_ignoriert():
    gesehen = []
    e = Entprellung(gesehen.append)
    for topic in (
        "frigate/klingel/detect/state",
        "frigate/klingel/motion_threshold/state",
        "frigate/klingel/status/detect",
        "frigate/available",
    ):
        e.nachricht(topic, b"1")
    assert gesehen == []
