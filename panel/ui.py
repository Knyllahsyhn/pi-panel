"""GTK-Fenster mit Videoflaeche links und blaetterbarer Knopfleiste rechts."""

import os

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from panel import seiten  # noqa: E402

# 800 minus 160 ergibt 640, die Breite des Substreams. Das Video laeuft dadurch
# unskaliert, was auf schwacher Hardware spuerbar ist.
KNOPFBREITE = 160
# Hoehe der Pfeilzeile am Fuss der Leiste. Bei 480 px Bildschirmhoehe bleiben
# 410 px fuer die Kameraknoepfe, bei fuenf je Seite also 82 px.
PFEILHOEHE = 70
# Beide Zeichen stehen nur hier. Fehlt der Zeichensatz auf dem Geraet und es
# erscheinen Kaestchen, werden daraus "<" und ">".
PFEIL_ZURUECK = "◀"
PFEIL_VOR = "▶"
ERSATZGROESSE = (800, 480)
STILDATEI = os.path.join(os.path.dirname(__file__), "stil.css")


def bildschirmgroesse():
    """Groesse des primaeren Monitors, mit Rueckfall auf die Panelgroesse."""
    anzeige = Gdk.Display.get_default()
    if anzeige is None:
        return ERSATZGROESSE
    monitor = anzeige.get_primary_monitor() or anzeige.get_monitor(0)
    if monitor is None:
        return ERSATZGROESSE
    geometrie = monitor.get_geometry()
    return geometrie.width, geometrie.height


def stil_laden():
    if not os.path.exists(STILDATEI):
        return
    anbieter = Gtk.CssProvider()
    anbieter.load_from_path(STILDATEI)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        anbieter,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


class Fenster:
    def __init__(self, kameras, knoepfe_pro_seite, bei_knopfdruck, bei_bedienung):
        stil_laden()
        self._knoepfe = {}
        self._aufteilung = seiten.teile(kameras, knoepfe_pro_seite)
        self._blaettert = len(self._aufteilung.seiten) > 1
        self._seite = 0
        self._pfeile = None
        self._bei_bedienung = bei_bedienung

        self._fenster = Gtk.Window()
        self._fenster.set_decorated(False)
        # fullscreen() ist eine Bitte an den Fenstermanager. Unter xinit laeuft
        # keiner, deshalb die Groesse zusaetzlich explizit setzen, sonst bekommt
        # das Fenster nur seine natuerliche Groesse.
        breite, hoehe = bildschirmgroesse()
        self._fenster.set_default_size(breite, hoehe)
        self._fenster.move(0, 0)
        self._fenster.fullscreen()
        self._fenster.get_style_context().add_class("panel-hintergrund")
        self._fenster.connect("destroy", Gtk.main_quit)

        aussen = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        innen = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        self.video = Gtk.DrawingArea()
        self.video.set_hexpand(True)
        self.video.set_vexpand(True)
        self.video.get_style_context().add_class("panel-video")
        innen.pack_start(self.video, True, True, 0)

        leiste = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        leiste.set_size_request(KNOPFBREITE, -1)
        leiste.pack_start(self._stapel_bauen(bei_knopfdruck), True, True, 0)
        # Bei einer einzigen Seite gaebe es nichts zu blaettern, und zwei tote
        # Knoepfe wuerden nur Platz und Aufmerksamkeit kosten.
        if self._blaettert:
            leiste.pack_start(self._pfeilzeile_bauen(), False, False, 0)
        innen.pack_start(leiste, False, False, 0)

        aussen.pack_start(innen, True, True, 0)

        self._status = Gtk.Label(label="")
        self._status.get_style_context().add_class("panel-status")
        # Nur einblenden, wenn es etwas zu melden gibt. Sonst staucht die Zeile
        # das Video und es muesste skaliert werden.
        self._status.set_no_show_all(True)
        aussen.pack_start(self._status, False, False, 0)

        self._fenster.add(aussen)
        self._seite_zeigen(0)

    def _stapel_bauen(self, bei_knopfdruck):
        self._stapel = Gtk.Stack()
        # Ohne NONE animiert GTK jeden Seitenwechsel. Das kostet auf dem Pi
        # Rechenzeit, die das Dekodieren braucht.
        self._stapel.set_transition_type(Gtk.StackTransitionType.NONE)
        for nummer, seite in enumerate(self._aufteilung.seiten):
            self._stapel.add_named(self._seite_bauen(seite, bei_knopfdruck), str(nummer))
        return self._stapel

    def _seite_bauen(self, seite, bei_knopfdruck):
        kasten = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for kamera in seite:
            knopf = Gtk.Button(label=kamera.label)
            knopf.get_style_context().add_class("panel-knopf")
            knopf.set_can_focus(False)
            knopf.connect("clicked", lambda _, n=kamera.name: bei_knopfdruck(n))
            kasten.pack_start(knopf, True, True, 0)
            self._knoepfe[kamera.name] = knopf
        # Jede Seite bekommt gleich viele Plaetze. Ohne die Fuellplaetze waeren
        # die Knoepfe auf der kuerzeren letzten Seite hoeher als auf den
        # vorigen und wuerden beim Blaettern springen. Ueber expand teilen alle
        # Seiten dieselbe Resthoehe durch dieselbe Zahl, das bleibt auch
        # richtig, wenn die Statuszeile aufklappt.
        for _ in range(self._aufteilung.pro_seite - len(seite)):
            # EventBox und nicht Box: nur ein Widget mit eigenem Fenster
            # zeichnet in GTK3 zuverlaessig seinen CSS-Hintergrund.
            luecke = Gtk.EventBox()
            luecke.get_style_context().add_class("panel-luecke")
            kasten.pack_start(luecke, True, True, 0)
        # set_visible_child_name greift nur auf ein Kind, das selbst schon
        # visible ist. Ohne dieses show_all waere die Seitenwahl vor dem
        # show_all() des Fensters stillschweigend wirkungslos. Sichtbar wird
        # dadurch nichts, der Stack zeigt weiterhin nur ein Kind.
        kasten.show_all()
        return kasten

    def _pfeilzeile_bauen(self):
        zeile = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        zeile.set_size_request(-1, PFEILHOEHE)
        zurueck = self._pfeil_bauen(PFEIL_ZURUECK, -1)
        vor = self._pfeil_bauen(PFEIL_VOR, 1)
        zeile.pack_start(zurueck, True, True, 0)
        zeile.pack_start(vor, True, True, 0)
        self._pfeile = (zurueck, vor)
        return zeile

    def _pfeil_bauen(self, zeichen, richtung):
        knopf = Gtk.Button(label=zeichen)
        knopf.get_style_context().add_class("panel-pfeil")
        knopf.set_can_focus(False)
        knopf.connect("clicked", lambda _: self._bei_pfeil(richtung))
        return knopf

    def _bei_pfeil(self, richtung):
        self._seite_zeigen(self._seite + richtung)
        # Blaettern zaehlt als Bedienung, sonst reisst der Rueckfall die Kamera
        # mitten im Suchen weg und nimmt die Seite mit.
        self._bei_bedienung()

    def _seite_zeigen(self, nummer):
        self._seite = seiten.begrenzen(self._aufteilung, nummer)
        self._stapel.set_visible_child_name(str(self._seite))
        if self._pfeile is None:
            return
        zurueck, vor = self._pfeile
        zurueck.set_sensitive(self._seite > 0)
        vor.set_sensitive(self._seite < len(self._aufteilung.seiten) - 1)

    def zeige_status(self, text):
        GLib.idle_add(self._status_setzen, text)

    def _status_setzen(self, text):
        self._status.set_text(text)
        self._status.set_visible(bool(text))
        return False

    def markiere(self, kamera):
        GLib.idle_add(self._markieren, kamera)

    def _markieren(self, kamera):
        for name, knopf in self._knoepfe.items():
            kontext = knopf.get_style_context()
            if name == kamera:
                kontext.add_class("panel-knopf-aktiv")
            else:
                kontext.remove_class("panel-knopf-aktiv")
        # Die Seite folgt der laufenden Kamera, damit die Markierung nie auf
        # einer unsichtbaren Seite leuchtet.
        seite = seiten.seite_mit(self._aufteilung, kamera)
        if seite is not None:
            self._seite_zeigen(seite)
        return False

    def fenster_id(self):
        return self.video.get_window().get_xid()

    def starten(self, nach_dem_anzeigen):
        self._fenster.show_all()
        # Erst nach dem Realisieren existiert die XID, die mpv als --wid braucht.
        GLib.idle_add(nach_dem_anzeigen)
        Gtk.main()
