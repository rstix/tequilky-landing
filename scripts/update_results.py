#!/usr/bin/env python3
"""Pull Tequilky's results and the league table from 2lz.futsalliga.cz (the
2nd women's league's own site: public, no bot wall) and write them into
index.html. Run on a schedule by the deploy workflow; safe to run any time.
With --if-due it asks the league site only while one of our results is due.

It rewrites only three marked spots (the fixtures list, the table body and
its note), always from data/season.json, so a run with nothing new changes
nothing. If the source looks wrong it writes nothing and exits non-zero.
"""
import html
import json
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA, PAGE = ROOT / "data" / "season.json", ROOT / "index.html"
# 2. futsalová liga žen, 2026/27: the season is "2027", group 11 is Východ
# (group 8 is Západ). The 1st league lives at lz.futsalliga.cz, without a group.
BASE, SEASON, GROUP = "https://2lz.futsalliga.cz", "2027", "11"
US = "Tequilky Slavia Malé Hoštice"
TZ = ZoneInfo("Europe/Prague")
NAMES = {                                                    # league-site spelling -> ours
    "Tělovýchovná jednota Slavia Malé Hoštice, z.s.": US,
    "Rakovec Kotvrdovice": "TJ Rakovec Kotvrdovice",
}
GRACE_DAYS = 14   # an empty schedule is fine until this long after our first match
DAYS = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]
UA = "futsal-tequilky.cz results (+https://futsal-tequilky.cz; after matches)"
ROW = '<div class="row align-items-center pt-3 pb-3 border-bottom border-bcolor">'


def fetch(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def name(raw):
    return NAMES.get(raw, raw)


def parse_matches(page):
    """Every match on the schedule page: date, time, teams, score, venue."""
    heads = [(m.start(), date(int(m[3]), int(m[2]), int(m[1])))
             for m in re.finditer(r"<h2[^>]*>(?:(?!</h2>).)*?(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\s*</h2>", page, re.S)]
    starts = [m.start() for m in re.finditer(re.escape(ROW), page)] + [len(page)]
    out = []
    for a, b in zip(starts, starts[1:]):
        chunk = page[a:b]
        day = next((d for p, d in reversed(heads) if p < a), None)
        when = re.search(r'href="/match/(\d+)"[^>]*>\s*<div[^>]*>\s*(\d{1,2}):(\d{2})', chunk)
        teams = [name(text(t)) for t in re.findall(r'<div class="match-team">(.*?)</div>', chunk, re.S)]
        if not (day and when and len(teams) == 2):
            continue
        score = re.search(r'match-results">\s*(\d+)\s*:\s*(\d+)\s*<', chunk)
        venue = re.search(r'<div class="match-place">(.*?)</div>', chunk, re.S)
        out.append({"lz": int(when[1]), "home": teams[0], "away": teams[1],
                    "kickoff": datetime(day.year, day.month, day.day, int(when[2]), int(when[3]), tzinfo=TZ),
                    "score": [int(score[1]), int(score[2])] if score else None,
                    "venue": text(venue[1]) if venue else None})
    return out


def parse_table(page):
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", page, re.S):
        cells = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) == 8 and cells[0].isdigit():
            rows.append([int(cells[0]), name(cells[1]), *cells[2:]])
    return rows


# ── rendering: must reproduce the page's own markup exactly ──────────────────

def render_fixture(f):
    k = datetime.fromisoformat(f["kickoff"])
    home = f["home"] == US
    result = None
    if f["score"]:
        ours, theirs = f["score"] if home else f["score"][::-1]
        result = "win" if ours > theirs else "draw" if ours == theirs else "loss"
    cls = "fixture" + (f" has-result is-{result}" if result else "")
    side = lambda t: "<b>Tequilky</b>" if t == US else html.escape(t)
    mid = f' <span class="fixture__score">{f["score"][0]}:{f["score"][1]}</span> ' if result else " – "
    meta = [f'{f["round"]}.&nbsp;kolo', "doma" if home else "venku"]
    if f.get("venue"):
        meta.append(html.escape(f["venue"]))
    if result:
        meta.append({"win": "výhra", "draw": "remíza", "loss": "prohra"}[result])
    if f.get("postponed"):
        meta.append("odloženo")
    off = k.strftime("%z"); off = off[:3] + ":" + off[3:]
    return f'''          <li class="{cls}" data-kickoff="{k.strftime('%Y-%m-%dT%H:%M:00')}{off}">
            <time class="fixture__when" datetime="{k.strftime('%Y-%m-%dT%H:%M')}{off}"><span class="fixture__day">{DAYS[k.weekday()]} {k.day}.&nbsp;{k.month}.&nbsp;{k.year}</span><span class="fixture__time">{k.strftime('%H:%M')}</span></time>
            <span class="fixture__match">
              <span class="fixture__teams">{side(f["home"])}{mid}{side(f["away"])}</span>
              <span class="fixture__meta">{" · ".join(meta)}</span>
            </span>
            <a class="fixture__link" href="{f.get("fotbal") or f"{BASE}/match/{f['lz']}"}" target="_blank" rel="noopener" aria-label="Detail zápasu {html.escape(f["home"])} – {html.escape(f["away"])} na {"fotbal.cz" if f.get("fotbal") else "futsalliga.cz"}">Detail</a>
          </li>'''


def render_table(rows):
    out = []
    for pos, team, z, v, r, p, score, pts in rows:
        us = ' class="is-us"' if team == US else ""
        out.append(f'            <tr{us}><td class="num">{pos}</td><th scope="row">{html.escape(team)}</th>'
                   f'<td class="num">{z}</td><td class="num opt">{v}</td><td class="num opt">{r}</td>'
                   f'<td class="num opt">{p}</td><td class="num">{score}</td><td class="num"><b>{pts}</b></td></tr>')
    return "\n".join(out)


def swap(page, pattern, new, what):
    page, n = re.subn(pattern, lambda m: m[1] + new + m[2], page, count=1, flags=re.S)
    if n != 1:
        sys.exit(f"index.html: could not find the {what}")
    return page


def due(fixtures, now):
    """A match of ours has ended and its score isn't in yet. Kickoff + 75 min
    is about the final whistle; after a day the weekly runs take over."""
    return [f for f in fixtures if not f["score"] and timedelta(minutes=75)
            <= now - datetime.fromisoformat(f["kickoff"]) <= timedelta(hours=24)]


def main():
    season = json.loads(DATA.read_text(encoding="utf-8"))
    fixtures = season["fixtures"]
    if "--if-due" in sys.argv[1:]:
        # The frequent schedule: ask the league site only while a result is due.
        waiting = due(fixtures, datetime.now(TZ))
        if not waiting:
            print("no result due, nothing to do")
            return
        print("waiting for: " + ", ".join(f'{f["home"]} – {f["away"]}' for f in waiting))
    try:
        listed = parse_matches(fetch(f"/matches/{SEASON}/{GROUP}"))
        table = parse_table(fetch(f"/standings/{SEASON}/{GROUP}"))
    except Exception as e:                                   # network, HTTP, decoding
        sys.exit(f"{BASE} unreachable: {e}")
    out = set(season.get("withdrawn", []))                  # teams that left: their matches don't count
    matches = [m for m in listed if US in (m["home"], m["away"]) and not out & {m["home"], m["away"]}]
    if not listed:
        # The league fills its site in its own time; an empty page is only
        # alarming once the season has been running for a while.
        first = min(datetime.fromisoformat(f["kickoff"]) for f in fixtures)
        if (datetime.now(TZ) - first).days < GRACE_DAYS:
            print("schedule not on the league site yet, nothing to do")
            return
        sys.exit("the league site still lists no matches: check it, nothing written")
    if not matches:
        sys.exit("no Tequilky matches on the schedule page: a team name or its layout changed, nothing written")
    teams = {f["home"] for f in fixtures} | {f["away"] for f in fixtures} | out
    if table:
        # The league lists a team only once it has played: add the rest at the
        # bottom with zeros, so the table always shows the whole group.
        unknown = [t[1] for t in table if t[1] not in teams]
        if unknown or len({t[1] for t in table}) != len(table) or sum(t[1] == US for t in table) != 1:
            sys.exit(f"standings look wrong (unknown or repeated teams: {unknown or 'repeats'}), nothing written")
        for team in sorted(teams - out - {t[1] for t in table}):
            table.append([len(table) + 1, team, "0", "0", "0", "0", "0:0", "0"])

    # Each fixture carries the league's match id ("lz"); a pair can meet more
    # than once, so a new fixture without an id is matched by pair only.
    by_id = {f["lz"]: f for f in fixtures if f.get("lz")}
    for m in matches:
        f = by_id.get(m["lz"])
        if f is None:
            free = [f for f in fixtures if not f.get("lz") and (f["home"], f["away"]) == (m["home"], m["away"])]
            if len(free) != 1:
                sys.exit(f"unknown fixture on lz: {m['home']} – {m['away']} (match {m['lz']}), "
                         "add it to data/season.json, nothing written")
            f = free[0]
            f["lz"] = m["lz"]
        f["kickoff"] = m["kickoff"].isoformat()             # lz is the league's own schedule
        f["venue"] = m["venue"] or f["venue"]
        f["score"] = m["score"] or f["score"]               # keep a hand-entered score until lz has one
    fixtures.sort(key=lambda f: f["kickoff"])

    original = PAGE.read_text(encoding="utf-8")
    page = swap(original, r'(<ol class="fixtures" id="fixtures">\n).*?(\n      </ol>)',
                "\n".join(render_fixture(f) for f in fixtures), "fixtures list")
    if table:
        before = page
        page = swap(page, r'(<table class="standings">.*?<tbody>\n).*?(\n        </tbody>)',
                    render_table(table), "table body")
        if page != before:                                   # date the note only when the table moved
            today = datetime.now(TZ)
            page = swap(page, r'(<p class="standings__note">).*?(</p>)',
                        f'Aktualizováno {today.day}.&nbsp;{today.month}.&nbsp;{today.year} podle '
                        f'<a class="link" href="{BASE}/standings/{SEASON}/{GROUP}" target="_blank" rel="noopener">futsalliga.cz</a>.',
                        "table note")
    if any(f["score"] for f in fixtures):
        page = page.replace("Sezona\n          začíná 14.&nbsp;listopadu 2026.", "Sezona\n          začala 14.&nbsp;listopadu 2026.")

    played = sum(bool(f["score"]) for f in fixtures)
    if page != original:
        PAGE.write_text(page, encoding="utf-8")
        DATA.write_text(json.dumps(season, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"updated: {played}/{len(fixtures)} results, table {'live' if table else 'not out yet'}")
    else:
        print(f"nothing new: {played}/{len(fixtures)} results, table {'live' if table else 'not out yet'}")


if __name__ == "__main__":
    main()
