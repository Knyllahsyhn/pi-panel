import base64
import json

import pytest

from panel.auth import Anmeldung, AuthFehler, jwt_ablauf


def jwt(exp, sub="pi", role="viewer"):
    kopf = base64.urlsafe_b64encode(b'{"typ":"JWT"}').decode().rstrip("=")
    nutz = json.dumps({"sub": sub, "role": role, "iat": 0, "exp": exp}).encode()
    return "%s.%s.unterschrift" % (kopf, base64.urlsafe_b64encode(nutz).decode().rstrip("="))


class FakeAntwort:
    def __init__(self, status, cookies=None):
        self.status_code = status
        self.cookies = cookies or {}


class FakeSession:
    def __init__(self, antworten):
        self.antworten = list(antworten)
        self.aufrufe = 0

    def post(self, *args, **kwargs):
        self.aufrufe += 1
        return self.antworten.pop(0)


def anmeldung(session, uhr):
    return Anmeldung(
        base_url="https://host:8971",
        user="pi",
        passwort="geheim",
        tls_verify=False,
        session=session,
        uhr=uhr,
    )


def test_jwt_ablauf_liest_exp():
    assert jwt_ablauf(jwt(exp=1788389266)) == 1788389266


def test_jwt_ablauf_bei_muell():
    assert jwt_ablauf("kein.jwt") is None
    assert jwt_ablauf("") is None


def test_erste_anmeldung_liest_cookie():
    t = jwt(exp=90000)
    s = FakeSession([FakeAntwort(200, {"frigate_token": t})])
    assert anmeldung(s, lambda: 1000.0).token() == t
    assert s.aufrufe == 1


def test_token_wird_zwischengespeichert():
    s = FakeSession([FakeAntwort(200, {"frigate_token": jwt(exp=90000)})])
    a = anmeldung(s, lambda: 1000.0)
    a.token()
    a.token()
    assert s.aufrufe == 1


def test_abgelaufenes_token_wird_erneuert():
    jetzt = [1000.0]
    erst, dann = jwt(exp=2000), jwt(exp=90000)
    s = FakeSession([
        FakeAntwort(200, {"frigate_token": erst}),
        FakeAntwort(200, {"frigate_token": dann}),
    ])
    a = anmeldung(s, lambda: jetzt[0])
    assert a.token() == erst
    jetzt[0] = 1900.0
    assert a.token() == dann
    assert s.aufrufe == 2


def test_fehlgeschlagene_anmeldung():
    s = FakeSession([FakeAntwort(401)])
    with pytest.raises(AuthFehler, match="401"):
        anmeldung(s, lambda: 1000.0).token()


def test_fehlendes_cookie():
    s = FakeSession([FakeAntwort(200, {})])
    with pytest.raises(AuthFehler, match="frigate_token"):
        anmeldung(s, lambda: 1000.0).token()


def test_header_hat_cookie_form():
    t = jwt(exp=90000)
    s = FakeSession([FakeAntwort(200, {"frigate_token": t})])
    assert anmeldung(s, lambda: 1000.0).header() == "Cookie: frigate_token=%s" % t


def test_passwort_nicht_in_repr():
    s = FakeSession([FakeAntwort(200, {"frigate_token": jwt(exp=90000)})])
    assert "geheim" not in repr(anmeldung(s, lambda: 1000.0))
