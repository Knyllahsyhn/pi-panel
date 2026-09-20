# Blaetterbare Knopfleiste

Stand 2026-09-20. Anlass: die Anlage waechst von sechs auf neun Kameras. Bei
neun Knoepfen auf 480 px Hoehe bleiben 53 px pro Knopf, zu wenig um sie auf
einem Touchdisplay zuverlaessig zu treffen.

## Entscheidungen

Vorab festgelegt, damit die Umsetzung nicht neu abwaegt:

- **Pfeile sitzen am Fuss der Knopfleiste**, nicht in einem Balken ueber die
  volle Breite. Die Leiste bleibt 160 px breit, das Video damit exakt
  640x480 und unskaliert. Ein Balken ueber die volle Breite haette das Video
  auf 800x410 gestaucht und Skalierung erzwungen, genau die Last, die
  `KNOPFBREITE = 160` bisher vermeidet.
- **Die Seite folgt der laufenden Kamera.** Wechselt die Anzeige von selbst,
  per Personenerkennung oder per Rueckfall auf die Basiskamera, blaettert die
  Leiste auf die Seite mit diesem Knopf. Die Aktiv-Markierung ist dadurch
  immer sichtbar.
- **Der Pfeil am Rand wird ausgegraut**, kein Rundlauf. Auf Seite 1 ist der
  Linkspfeil unempfindlich, auf der letzten der Rechtspfeil. Damit braucht es
  keine zusaetzliche Seitenanzeige.
- **Kein Wischen.** Ausdruecklich nicht gewuenscht, nur Knoepfe.
- **Ein Pfeildruck zaehlt als Bedienung** und verlaengert die Anzeigedauer,
  ohne die Kamera zu wechseln.
- **Glyphen `◀` und `▶`** aus DejaVu Sans. Wird am Geraet geprueft; rendern
  sie nicht, werden es `<` und `>`. Die Zeichen stehen deshalb an genau einer
  Stelle im Code.

## Aufteilung: `panel/seiten.py`

Die Blaetterarithmetik ist reine Logik und kommt in ein eigenes Modul, nach
dem Muster von `state.py`: frozen dataclass plus freie Funktionen, kein I/O,
ohne Display testbar.

```python
@dataclass(frozen=True)
class Aufteilung:
    seiten: tuple      # Tupel von Tupeln aus Kamera
    pro_seite: int

def teile(kameras, pro_seite) -> Aufteilung
def seite_mit(aufteilung, kamera_name) -> int | None
def begrenzen(aufteilung, seite) -> int
```

- `teile` schneidet die Kameraliste in Bloecke von `pro_seite`. Der letzte
  Block darf kuerzer sein. `pro_seite` groesser als die Liste ergibt eine
  einzige Seite.
- `seite_mit` gibt den Index der Seite zurueck, auf der die Kamera steht, oder
  `None` wenn sie unbekannt ist. Bewusst `None` und nicht `0`, damit ein
  unerwarteter Name die Seite stehen laesst statt auf Seite 1 zu springen.
- `begrenzen` klemmt einen Seitenindex auf `[0, letzte]`.

Bei neun Kameras und `pro_seite = 5`:

- Seite 1: `klingel`, `haustuer`, `einfahrt1`, `einfahrt2`, `pergola`
- Seite 2: `garten` plus die drei neuen

## Oberflaeche: `panel/ui.py`

`Fenster.__init__` bekommt zwei Parameter dazu:

```python
Fenster(kameras, knoepfe_pro_seite, bei_knopfdruck, bei_bedienung)
```

### Widgets

`Gtk.Stack` mit `set_transition_type(Gtk.StackTransitionType.NONE)`, je Seite
eine vertikale `Gtk.Box` als Stack-Kind. Alle Kameraknoepfe existieren
dauerhaft und bleiben in `self._knoepfe`, `markiere()` findet damit jeden
Knopf unabhaengig von der sichtbaren Seite. Umschalten ist ein
`set_visible_child`.

Verworfen: eine einzige Box, deren Kinder beim Blaettern neu aufgebaut
werden. Spart Widgets, kostet aber Remove/Add-Gefummel und flackert auf
schwacher Hardware. Ebenfalls verworfen: `Gtk.Notebook`, dessen Tab-Leiste
erst wieder unterdrueckt werden muesste.

### Gleiche Knopfhoehe auf jeder Seite

Jede Seitenbox bekommt genau `pro_seite` Plaetze. Wo auf der letzten Seite
Kameras fehlen, stehen leere `Gtk.Box` mit Stilklasse `panel-luecke` in
Leistenfarbe. Alle Plaetze werden mit `expand=True, fill=True` gepackt.

Dadurch entfaellt jede Pixelrechnung: jede Seite teilt dieselbe Resthoehe
durch dieselbe Zahl. Kein Knopf springt beim Blaettern in der Groesse, und es
bleibt richtig, wenn die Statuszeile aufklappt und Hoehe wegnimmt.

### Pfeilzeile

Horizontale `Gtk.Box` am Fuss der Leiste, unterhalb des Stacks, mit
`expand=False`. Zwei Knoepfe, je `expand=True`, also 80 px breit. Hoehe ueber
`set_size_request(-1, PFEILHOEHE)` mit `PFEILHOEHE = 70` als Modulkonstante
neben `KNOPFBREITE`. Bleiben 410 px fuer fuenf Plaetze, also 82 px pro Knopf,
praktisch die heutigen 80.

`set_can_focus(False)` wie bei den Kameraknoepfen.

Gibt es nur eine Seite, wird die Pfeilzeile gar nicht erst gepackt, damit
keine toten Bedienelemente herumstehen.

### Neue und geaenderte Methoden

- `_seite_zeigen(index)`: setzt das sichtbare Stack-Kind und die
  Empfindlichkeit beider Pfeile (`set_sensitive`). Index wird ueber
  `seiten.begrenzen` geklemmt.
- `_bei_pfeil(richtung)`: `_seite_zeigen(self._seite + richtung)` und danach
  der Rueckruf `bei_bedienung()`.
- `_markieren(kamera)`: wie heute die Aktiv-Klasse, zusaetzlich
  `seite = seiten.seite_mit(...)` und bei `seite is not None` ein
  `_seite_zeigen(seite)`.

Alles was mit Seiten zu tun hat, bleibt in `Fenster`. `main.py` erfaehrt von
Seiten nichts.

## Konfiguration: `panel/config.py`

Neues Feld `Konfig.knoepfe_pro_seite`, gelesen aus
`anzeige.knoepfe_pro_seite`.

**Optionaler Schluessel.** Fehlt er, ist der Wert die Anzahl der Kameras,
also alle auf einer Seite und damit genau das heutige Verhalten. Kein
Pflichtfeld, weil das erste Panel im Feld laeuft und beim naechsten Deploy
sonst mit `KonfigFehler` nicht mehr startet.

Ein Wert kleiner als 1 oder keine Ganzzahl ist ein `KonfigFehler`.

## Zustandsmaschine: `panel/state.py`

Neuer Eingang, damit ein Pfeildruck die Anzeige verlaengert ohne die Kamera
zu wechseln:

```python
def bei_bedienung(zustand, regeln, jetzt):
    """Verlaengert die laufende Anzeige, ohne die Kamera zu wechseln."""
```

- `BASIS`: unveraendert zurueck. Die Basiskamera laeuft ohnehin unbefristet,
  es gibt nichts zu verlaengern.
- `MANUELL` und `AUTO`: `replace(zustand, seit=jetzt)`.

Der Modus bleibt in beiden Faellen stehen. Bewusst kein Wechsel von `AUTO`
nach `MANUELL`: der Modus `MANUELL` bedeutet "hat eine Kamera gewaehlt", und
Blaettern ist keine Kamerawahl. `letzter_autosprung` und `kamera` bleiben
ebenfalls unberuehrt.

Ohne diesen Eingang gilt: laeuft `manuell` mit 60 s Rueckfall und es wird in
Sekunde 55 geblaettert, reisst es die Kamera fuenf Sekunden spaeter auf die
Basiskamera und die Seite mit.

## Verdrahtung: `panel/main.py`

```python
self._fenster = Fenster(
    konfig.kameras,
    konfig.knoepfe_pro_seite,
    self._bei_knopfdruck,
    self._bei_bedienung,
)

def _bei_bedienung(self):
    self._zustand = state.bei_bedienung(
        self._zustand, self._konfig.regeln, time.monotonic()
    )
```

Kein `_anwenden()` in `_bei_bedienung`. Sichtbar aendert sich nichts, und
`_anwenden` wuerde den Stream unnoetig neu laden. Das unterscheidet diesen
Pfad von `_bei_knopfdruck`, der absichtlich immer neu laedt, damit ein
eingefrorenes Bild sich durch Antippen wiederbeleben laesst.

Weil `_bei_bedienung` nicht `_anwenden` ruft, laeuft auch kein `markiere`, und
die Seite bleibt beim Blaettern stehen statt zur laufenden Kamera
zurueckzuspringen.

Der Weg "Seite folgt der Kamera" haengt an der bestehenden Stelle:
`_anwenden` ruft bei jedem Kamerawechsel `markiere`, und `markiere` schaltet
kuenftig auch die Seite. Personenerkennung, Rueckfall und Knopfdruck sind
damit in einem Griff abgedeckt.

## Aussehen: `panel/stil.css`

- `.panel-pfeil`: wie `.panel-knopf`, groessere Schrift fuer die Glyphe,
  `border-top` als Trennung zur Knopfliste, `border-right` zwischen den
  beiden Pfeilen.
- `.panel-pfeil:disabled`: Schriftfarbe auf Leistenniveau abgesenkt, gleicher
  Hintergrund, damit der Pfeil sichtbar tot ist. GTK3 nutzt `:disabled` fuer
  unempfindliche Widgets.
- `.panel-luecke`: Hintergrund wie `.panel-knopf`, ohne Rahmen, damit die
  Fuellplaetze der letzten Seite nicht als Loch auffallen.

## Fehlerfaelle

- Kamera nicht in der Aufteilung: `seite_mit` gibt `None`, die aktuelle Seite
  bleibt stehen. Kann bei gueltiger Konfiguration nicht auftreten, weil
  `lade()` die Basiskamera gegen die Kameraliste prueft.
- `knoepfe_pro_seite` groesser als die Kameraanzahl: eine Seite, keine
  Pfeilzeile.
- Reconnect: `_erneut_laden` ruft `_anwenden` und damit `markiere`. Blaettert
  jemand gerade und der Stream kommt wieder, springt die Seite zur laufenden
  Kamera. Selten und konsistent mit der Regel "Seite folgt der Kamera",
  deshalb nicht gesondert behandelt.

## Tests

Neu `tests/test_seiten.py`:

- `teile` bei glatter Teilung, bei ungerader Teilung mit kuerzerer letzter
  Seite, bei `pro_seite` groesser als die Liste
- `seite_mit` fuer eine Kamera auf der ersten Seite, eine auf der letzten,
  einen unbekannten Namen
- `begrenzen` unterhalb 0, oberhalb der letzten Seite, innerhalb

Ergaenzt `tests/test_state.py`:

- `bei_bedienung` in `BASIS` gibt den Zustand unveraendert zurueck
- `bei_bedienung` in `MANUELL` setzt `seit`, sodass ein `bei_tick` nach dem
  urspruenglichen Ablauf noch nicht zurueckfaellt
- `bei_bedienung` in `AUTO` setzt `seit` und laesst `modus`, `kamera` und
  `letzter_autosprung` stehen

Ergaenzt `tests/test_config.py`:

- Schluessel fehlt, `knoepfe_pro_seite` entspricht der Kameraanzahl
- Schluessel gesetzt, Wert wird uebernommen
- Wert `0` und Wert `-1` ergeben `KonfigFehler`

`ui.py` bleibt untestet wie bisher, GTK braucht ein Display. Die Pruefung
dort laeuft am Geraet.

## Nachzuziehen

- `panel.yaml.example`: `knoepfe_pro_seite: 5` unter `anzeige`, plus die drei
  neuen Kameras
- `README.md`: der neue Schluessel und was sein Fehlen bedeutet

## Offen

Die Frigate-Kameranamen und Beschriftungen der drei neuen Kameras stehen noch
nicht fest. In `panel.yaml.example` kommen Platzhalter `neu1`, `neu2`, `neu3`
mit `springt: false`, nachgetragen wird direkt in `/etc/panel/panel.yaml` auf
den Pis. `springt: false` als Platzhalter, weil automatisches Aufspringen
eine bewusste Entscheidung pro Kamera ist.
