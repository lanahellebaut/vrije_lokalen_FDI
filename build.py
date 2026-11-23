#!/usr/bin/env python3
"""Bouwt docs/index.html: een overzicht van vrije en bezette uren per lokaal,
op basis van TimeEdit-abonnementslinks (iCal).

Gebruik:
  ICS_URLS="https://...ics
  https://...ics" python3 build.py        # haalt de links op (zo draait het op GitHub)
  python3 build.py testdata/*.ics         # lokale bestanden, om te testen
"""
import html
import json
import os
import sys
import urllib.request
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
TZ = ZoneInfo(CONFIG.get("tijdzone", "Europe/Brussels"))

DAGEN = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]
MAANDEN = ["januari", "februari", "maart", "april", "mei", "juni", "juli",
           "augustus", "september", "oktober", "november", "december"]


# ---------------------------------------------------------------- iCal inlezen
def unfold(text):
    lines = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def unescape(value):
    return (value.replace("\\n", "\n").replace("\\N", "\n")
            .replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\"))


def parse_dt(value):
    if value.endswith("Z"):
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone(TZ)
    if "T" in value:
        return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=TZ)
    return datetime.strptime(value, "%Y%m%d").replace(tzinfo=TZ)


def parse_ics(text):
    events, cur = [], None
    for line in unfold(text):
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT":
            if cur and "DTSTART" in cur and "DTEND" in cur:
                events.append(cur)
            cur = None
        elif cur is not None and ":" in line:
            key, value = line.split(":", 1)
            key = key.split(";", 1)[0]
            if key in ("DTSTART", "DTEND"):
                cur[key] = parse_dt(value)
            elif key in ("SUMMARY", "LOCATION"):
                cur[key] = unescape(value).strip()
    return events


def room_name(location):
    """'Auditorium 1. D1. Campus Merelbeke. Ingang 24 ...' -> 'Auditorium 1 (D1)'"""
    first = location.split("\n")[0].strip()
    for full, short in CONFIG.get("lokaalnamen", {}).items():
        if first.startswith(full):
            return short
    parts = [p.strip() for p in first.split(". ")]
    return f"{parts[0]} ({parts[1]})" if len(parts) > 1 else parts[0]


# ---------------------------------------------------------------- vrij/bezet
def is_closed(summary):
    return any(s.lower() in summary.lower() for s in CONFIG.get("sluiting_activiteiten", []))


def day_slots(events, day):
    """Geeft (vrij, bezet) als lijsten (start, einde, titel) binnen het venster van die dag."""
    hs, ms = map(int, CONFIG["dag_start"].split(":"))
    he, me = map(int, CONFIG["dag_einde"].split(":"))
    w0 = datetime.combine(day, time(hs, ms), TZ)
    w1 = datetime.combine(day, time(he, me), TZ)

    busy = []
    for e in events:
        s, t = max(e["DTSTART"], w0), min(e["DTEND"], w1)
        if s < t:
            title = "Gebouw gesloten" if is_closed(e.get("SUMMARY", "")) else e.get("SUMMARY", "Bezet")
            busy.append((s, t, title))
    busy.sort()

    free, cursor = [], w0
    min_free = timedelta(minutes=CONFIG.get("min_vrij_minuten", 30))
    for s, t, _ in busy:
        if s - cursor >= min_free:
            free.append((cursor, s, ""))
        cursor = max(cursor, t)
    if w1 - cursor >= min_free:
        free.append((cursor, w1, ""))
    return free, busy, w0, w1


# ---------------------------------------------------------------- HTML
def hm(dt):
    return dt.strftime("%H:%M").replace(":", "u") if dt.minute else f"{dt.hour}u"


def dag_label(day):
    return f"{DAGEN[day.weekday()]} {day.day} {MAANDEN[day.month - 1]}"


def bar(free, busy, w0, w1):
    span = (w1 - w0).total_seconds()
    out = []
    for kind, items in (("vrij", free), ("bezet", busy)):
        for s, t, title in items:
            left = (s - w0).total_seconds() / span * 100
            width = (t - s).total_seconds() / span * 100
            label = f"{hm(s)}–{hm(t)}" + (f" · {title}" if title else " · vrij")
            tekst = f"<span>{hm(s)}–{hm(t)}</span>" if width >= 9 else ""
            out.append(f'<div class="blok {kind}" style="left:{left:.2f}%;width:{width:.2f}%" '
                       f'title="{html.escape(label)}">{tekst}</div>')
    return "".join(out)


def ticks(w0, w1):
    out, h = [], w0.replace(minute=0) + (timedelta(hours=1) if w0.minute else timedelta())
    span = (w1 - w0).total_seconds()
    while h <= w1:
        out.append(f'<span style="left:{(h - w0).total_seconds() / span * 100:.2f}%">{h.hour}u</span>')
        h += timedelta(hours=1)
    return "".join(out)


def render(rooms, now):
    today = now.date()
    werkdagen = CONFIG.get("enkel_weekdagen", True)
    days, d = [], today
    while len(days) < CONFIG.get("aantal_dagen", 10):
        if not werkdagen or d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)

    vandaag = []
    first_day = days[0]
    titel_dag = "Vandaag" if first_day == today else f"Eerstvolgende werkdag ({dag_label(first_day)})"
    for name, events in rooms.items():
        free, _, _, _ = day_slots(events, first_day)
        items = "".join(f"<li>{hm(s)} – {hm(t)}</li>" for s, t, _ in free) or '<li class="geen">geen vrije uren</li>'
        vandaag.append(f'<div class="kaart"><h3>{html.escape(name)}</h3><ul>{items}</ul></div>')

    weken = []
    for name, events in rooms.items():
        rows = []
        for day in days:
            free, busy, w0, w1 = day_slots(events, day)
            kort = f"{DAGEN[day.weekday()][:2]} {day.day} {MAANDEN[day.month - 1][:3]}"
            rows.append(f'<div class="rij"><div class="dag">{kort}</div>'
                        f'<div class="balk">{bar(free, busy, w0, w1)}</div></div>')
        _, _, w0, w1 = day_slots([], days[0])
        weken.append(f'<section><h3>{html.escape(name)}</h3>'
                     f'<div class="rij as"><div class="dag"></div><div class="schaal">{ticks(w0, w1)}</div></div>'
                     f'{"".join(rows)}</section>')

    tpl = (ROOT / "template.html").read_text(encoding="utf-8")
    return (tpl.replace("{{TITEL}}", html.escape(CONFIG.get("titel", "Vrije lokalen")))
               .replace("{{UITLEG}}", html.escape(CONFIG.get("uitleg", "")))
               .replace("{{BIJGEWERKT}}", f"{dag_label(today)} om {hm(now)}")
               .replace("{{TITEL_DAG}}", titel_dag)
               .replace("{{VANDAAG}}", "".join(vandaag))
               .replace("{{WEKEN}}", "".join(weken)))


# ---------------------------------------------------------------- main
def load_sources(args):
    if args:
        return [Path(a).read_text(encoding="utf-8") for a in args]
    urls = [u.strip() for u in os.environ.get("ICS_URLS", "").split() if u.strip()]
    if not urls:
        sys.exit("Geen ICS_URLS ingesteld en geen bestanden meegegeven.")
    texts = []
    for u in urls:
        req = urllib.request.Request(u, headers={"User-Agent": "vrije-lokalen/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            texts.append(r.read().decode("utf-8"))
    return texts


def main():
    rooms = {}
    for text in load_sources(sys.argv[1:]):
        for e in parse_ics(text):
            rooms.setdefault(room_name(e.get("LOCATION", "Onbekend lokaal")), []).append(e)
    if not rooms:
        sys.exit("Geen activiteiten gevonden; pagina niet overschreven.")
    now = datetime.now(TZ)
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "index.html").write_text(render(dict(sorted(rooms.items())), now), encoding="utf-8")
    print(f"OK: {len(rooms)} lokaal/lokalen, {sum(len(v) for v in rooms.values())} activiteiten")


if __name__ == "__main__":
    main()
