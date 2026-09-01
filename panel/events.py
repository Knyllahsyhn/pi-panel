"""Abonniert Frigates Personenzaehler und meldet nur die steigende Flanke."""

import logging

import paho.mqtt.client as mqtt

log = logging.getLogger(__name__)


class Entprellung:
    def __init__(self, rueckruf):
        self._rueckruf = rueckruf
        self._letzter = {}

    def nachricht(self, topic, nutzlast):
        teile = topic.split("/")
        if len(teile) != 3 or teile[2] != "person":
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
    client.on_connect = lambda c, *_: c.subscribe(
        "%s/+/person" % konfig.mqtt.topic_prefix
    )
    client.on_message = lambda c, u, m: entprellung.nachricht(m.topic, m.payload)
    # Reconnect selbst regeln, damit ein Brokerausfall das Panel nicht anhaelt.
    client.reconnect_delay_set(min_delay=1, max_delay=60)
    client.connect_async(konfig.mqtt.host_oder_url, konfig.mqtt.port, keepalive=60)
    client.loop_start()
    return client
