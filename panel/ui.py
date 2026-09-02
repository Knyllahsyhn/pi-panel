"""GTK-Fenster mit Videoflaeche links und Knopfleiste rechts."""

import os

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

# 800 minus 160 ergibt 640, die Breite des Substreams. Das Video laeuft dadurch
# unskaliert, was auf schwacher Hardware spuerbar ist.
KNOPFBREITE = 160
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
    def __init__(self, kameras, bei_knopfdruck):
        stil_laden()
        self._knoepfe = {}

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
        for kamera in kameras:
            knopf = Gtk.Button(label=kamera.label)
            knopf.get_style_context().add_class("panel-knopf")
            knopf.set_can_focus(False)
            knopf.connect("clicked", lambda _, n=kamera.name: bei_knopfdruck(n))
            leiste.pack_start(knopf, True, True, 0)
            self._knoepfe[kamera.name] = knopf
        innen.pack_start(leiste, False, False, 0)

        aussen.pack_start(innen, True, True, 0)

        self._status = Gtk.Label(label="")
        self._status.get_style_context().add_class("panel-status")
        # Nur einblenden, wenn es etwas zu melden gibt. Sonst staucht die Zeile
        # das Video und es muesste skaliert werden.
        self._status.set_no_show_all(True)
        aussen.pack_start(self._status, False, False, 0)

        self._fenster.add(aussen)

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
        return False

    def fenster_id(self):
        return self.video.get_window().get_xid()

    def starten(self, nach_dem_anzeigen):
        self._fenster.show_all()
        # Erst nach dem Realisieren existiert die XID, die mpv als --wid braucht.
        GLib.idle_add(nach_dem_anzeigen)
        Gtk.main()
