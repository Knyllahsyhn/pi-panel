"""GTK-Fenster mit Videoflaeche links und Knopfleiste rechts."""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

KNOPFBREITE = 160


class Fenster:
    def __init__(self, kameras, bei_knopfdruck):
        self._fenster = Gtk.Window()
        self._fenster.set_decorated(False)
        self._fenster.fullscreen()
        self._fenster.connect("destroy", Gtk.main_quit)

        aussen = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        innen = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        self.video = Gtk.DrawingArea()
        self.video.set_hexpand(True)
        self.video.set_vexpand(True)
        innen.pack_start(self.video, True, True, 0)

        leiste = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        leiste.set_size_request(KNOPFBREITE, -1)
        for kamera in kameras:
            knopf = Gtk.Button(label=kamera.label)
            knopf.connect("clicked", lambda _, n=kamera.name: bei_knopfdruck(n))
            leiste.pack_start(knopf, True, True, 0)
        innen.pack_start(leiste, False, False, 0)

        aussen.pack_start(innen, True, True, 0)
        self._status = Gtk.Label(label="")
        aussen.pack_start(self._status, False, False, 0)
        self._fenster.add(aussen)

    def zeige_status(self, text):
        GLib.idle_add(self._status.set_text, text)

    def fenster_id(self):
        return self.video.get_window().get_xid()

    def starten(self, nach_dem_anzeigen):
        self._fenster.show_all()
        # Erst nach dem Realisieren existiert die XID, die mpv als --wid braucht.
        GLib.idle_add(nach_dem_anzeigen)
        Gtk.main()
