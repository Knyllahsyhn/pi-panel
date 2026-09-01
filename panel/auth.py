"""Holt und erneuert das Frigate-Token fuer Variante B."""

import base64
import json
import time

import requests

LOGIN_PFAD = "/api/login"
COOKIE_NAME = "frigate_token"
SICHERHEITSABSTAND_S = 300.0
ERSATZLAUFZEIT_S = 3600.0


class AuthFehler(Exception):
    pass


def jwt_ablauf(token):
    """Liest exp aus der JWT-Nutzlast. Ohne Signaturpruefung, die macht Frigate."""
    try:
        nutzlast = token.split(".")[1]
        roh = base64.urlsafe_b64decode(nutzlast + "=" * (-len(nutzlast) % 4))
        return float(json.loads(roh)["exp"])
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return None


class Anmeldung:
    def __init__(self, base_url, user, passwort, tls_verify,
                 session=None, uhr=time.time):
        self._base_url = base_url.rstrip("/")
        self._user = user
        self._passwort = passwort
        self._tls_verify = tls_verify
        self._session = session or requests.Session()
        self._uhr = uhr
        self._token = None
        self._gueltig_bis = 0.0

    def __repr__(self):
        return "Anmeldung(base_url=%r, user=%r)" % (self._base_url, self._user)

    def token(self):
        if self._token and self._uhr() < self._gueltig_bis:
            return self._token
        antwort = self._session.post(
            self._base_url + LOGIN_PFAD,
            json={"user": self._user, "password": self._passwort},
            verify=self._tls_verify,
            timeout=10,
        )
        if not 200 <= antwort.status_code < 300:
            raise AuthFehler("Anmeldung fehlgeschlagen, Status %d" % antwort.status_code)
        token = antwort.cookies.get(COOKIE_NAME)
        if not token:
            raise AuthFehler("Cookie %s fehlt in der Antwort" % COOKIE_NAME)
        ablauf = jwt_ablauf(token)
        # Die expires-Angabe des Cookies steht auf 2083 und ist unbrauchbar.
        self._gueltig_bis = (
            ablauf - SICHERHEITSABSTAND_S
            if ablauf is not None
            else self._uhr() + ERSATZLAUFZEIT_S
        )
        self._token = token
        return token

    def header(self):
        return "Cookie: %s=%s" % (COOKIE_NAME, self.token())
