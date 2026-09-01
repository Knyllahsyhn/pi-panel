import pytest
from panel.config import KonfigFehler, lade, stream_url

BASIS = """
frigate:
  base_url: https://192.168.30.2:8971
  user: panel
  password_file: {pw}
  tls_verify: false
mqtt:
  host: 192.168.30.2
  port: 1883
  user: panel-kueche
  password_file: {pw}
  topic_prefix: frigate
anzeige:
  basis_kamera: klingel
  rueckfall_manuell_s: 60
  rueckfall_auto_s: 30
  sperrzeit_auto_s: 120
quelle:
  modus: mjpeg
  mjpeg:
    pfad: "/api/{{cam}}?fps=5&h=480&bbox=0"
  rtsp:
    basis: "rtsp://192.168.30.2:8554"
    suffix: "_sub"
kameras:
  - {{name: klingel, label: "Klingel", springt: true}}
  - {{name: pergola, label: "Pergola", springt: false}}
"""


@pytest.fixture
def konfigdatei(tmp_path):
    pw = tmp_path / "geheim.pass"
    pw.write_text("s3cr3t\n")
    datei = tmp_path / "panel.yaml"
    datei.write_text(BASIS.format(pw=pw))
    return datei


def test_laedt_kameras(konfigdatei):
    k = lade(konfigdatei)
    assert [c.name for c in k.kameras] == ["klingel", "pergola"]


def test_regeln_enthalten_sprungliste(konfigdatei):
    k = lade(konfigdatei)
    assert k.regeln.sprungliste == frozenset({"klingel"})
    assert k.regeln.basis_kamera == "klingel"


def test_passwort_wird_gelesen(konfigdatei):
    k = lade(konfigdatei)
    assert k.frigate.passwort == "s3cr3t"


def test_passwort_nicht_in_repr(konfigdatei):
    k = lade(konfigdatei)
    assert "s3cr3t" not in repr(k.frigate)


def test_fehlendes_pflichtfeld(konfigdatei):
    inhalt = konfigdatei.read_text().replace("basis_kamera: klingel", "")
    konfigdatei.write_text(inhalt)
    with pytest.raises(KonfigFehler, match="basis_kamera"):
        lade(konfigdatei)


def test_basiskamera_muss_existieren(konfigdatei):
    inhalt = konfigdatei.read_text().replace("basis_kamera: klingel", "basis_kamera: keller")
    konfigdatei.write_text(inhalt)
    with pytest.raises(KonfigFehler, match="keller"):
        lade(konfigdatei)


def test_stream_url_mjpeg(konfigdatei):
    k = lade(konfigdatei)
    assert stream_url(k, "pergola") == (
        "https://192.168.30.2:8971/api/pergola?fps=5&h=480&bbox=0"
    )


def test_stream_url_rtsp(konfigdatei):
    inhalt = konfigdatei.read_text().replace("modus: mjpeg", "modus: rtsp")
    konfigdatei.write_text(inhalt)
    k = lade(konfigdatei)
    assert stream_url(k, "pergola") == "rtsp://192.168.30.2:8554/pergola_sub"
