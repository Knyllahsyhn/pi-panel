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


def test_rtsp_braucht_keine_frigate_passwortdatei(konfigdatei, tmp_path):
    inhalt = konfigdatei.read_text().replace("modus: mjpeg", "modus: rtsp")
    fehlt = tmp_path / "gibtsnicht.pass"
    inhalt = inhalt.replace(
        "password_file: %s" % (tmp_path / "geheim.pass"),
        "password_file: %s" % fehlt,
        1,
    )
    konfigdatei.write_text(inhalt)
    k = lade(konfigdatei)
    assert k.frigate.passwort == ""
    assert k.mqtt.passwort == "s3cr3t"


def test_mjpeg_braucht_die_frigate_passwortdatei(konfigdatei, tmp_path):
    inhalt = konfigdatei.read_text().replace(
        "password_file: %s" % (tmp_path / "geheim.pass"),
        "password_file: %s" % (tmp_path / "gibtsnicht.pass"),
        1,
    )
    konfigdatei.write_text(inhalt)
    with pytest.raises(KonfigFehler, match="gibtsnicht.pass"):
        lade(konfigdatei)


def test_knoepfe_pro_seite_fehlt_ergibt_eine_seite(konfigdatei):
    # Bestandsschutz: das Panel im Feld hat den Schluessel nicht.
    k = lade(konfigdatei)
    assert k.knoepfe_pro_seite == len(k.kameras)


def test_knoepfe_pro_seite_wird_uebernommen(tmp_path):
    k = lade(_mit_pro_seite(tmp_path, "  knoepfe_pro_seite: 1"))
    assert k.knoepfe_pro_seite == 1


@pytest.mark.parametrize("wert", ["0", "-1", "zwei", "true", "2.5"])
def test_knoepfe_pro_seite_ungueltig(tmp_path, wert):
    with pytest.raises(KonfigFehler):
        lade(_mit_pro_seite(tmp_path, "  knoepfe_pro_seite: %s" % wert))


def _mit_pro_seite(tmp_path, zeile):
    pw = tmp_path / "geheim.pass"
    pw.write_text("s3cr3t\n")
    text = BASIS.format(pw=pw).replace(
        "  sperrzeit_auto_s: 120",
        "  sperrzeit_auto_s: 120\n" + zeile,
    )
    datei = tmp_path / "panel.yaml"
    datei.write_text(text)
    return datei
