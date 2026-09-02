"""Abonniert Frigates Personenzaehler und meldet nur die steigende Flanke."""

import logging

import paho.mqtt.client as mqtt

log = logging.getLogger(__name__)


class Entprellung:
    def __init__(self, rueckruf):
        self._rueckruf = rueckruf
        self._letzter = {}

    def nachricht(self, topic, nutzlast):
        # Frigate benennt die Objektzaehler je nach Version mit oder ohne
        # angehaengtes /state. Beide Formen werden akzeptiert, alles andere
        # verworfen, sonst schluckt der Filter still die Ereignisse.
        teile = topic.split("/")
        if len(teile) not in (3, 4) or teile[2] != "person":
            return
        if len(teile) == 4 and teile[3] != "state":
            return
        kamera = teile[1]
        try:
            anzahl = int(nutzlast.decode().strip())
        except (ValueError, UnicodeDecodeError):
            log.warning("unlesbare Nutzlast auf %s", topic)
            return
        vorher = self._letzter.get(kamera, 0)
        self._letzter[kamera] = anzahl
        if vorher == 0 and anzahl > 0:
            self._rueckruf(kamera)


def verbinde(konfig, rueckruf):
    entprellung = Entprellung(rueckruf)
    client = mqtt.Client()
    client.username_pw_set(konfig.mqtt.user, konfig.mqtt.passwort)
    def bei_verbindung(client_, *_):
        client_.subscribe("%s/+/person" % konfig.mqtt.topic_prefix)
        client_.subscribe("%s/+/person/state" % konfig.mqtt.topic_prefix)

    client.on_connect = bei_verbindung
    client.on_message = lambda c, u, m: entprellung.nachricht(m.topic, m.payload)
    # Reconnect selbst regeln, damit ein Brokerausfall das Panel nicht anhaelt.
    client.reconnect_delay_set(min_delay=1, max_delay=60)
    client.connect_async(konfig.mqtt.host_oder_url, konfig.mqtt.port, keepalive=60)
    client.loop_start()
    return client
