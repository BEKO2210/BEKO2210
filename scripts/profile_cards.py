#!/usr/bin/env python3
"""Erzeugt Profil-Karten (SVG) und aktualisiert die Projekt-Abschnitte im README.

Läuft in der GitHub Action ohne fremde Dienste: nur GitHub-API + Standardbibliothek.
Aufruf: python3 scripts/profile_cards.py <ausgabeordner>
"""
import json
import os
import re
import sys
import urllib.request
from collections import Counter
from datetime import date, timedelta
from html import escape

USER = os.environ.get("PROFILE_USER", "BEKO2210")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = sys.argv[1] if len(sys.argv) > 1 else "dist"
RAW = f"https://raw.githubusercontent.com/{USER}/{USER}/output"
FEATURED_COUNT = 6
BUILDING_COUNT = 4
SKIP = {USER, f"{USER.lower()}.github.io"}

BG, BORDER, TITLE, TEXT, MUTED = "#0d1117", "#30363d", "#58a6ff", "#c9d1d9", "#8b949e"
LANG_COLORS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572A5", "HTML": "#e34c26",
    "CSS": "#563d7c", "Astro": "#ff5a03", "Kotlin": "#A97BFF", "C++": "#f34b7d", "Shell": "#89e051",
    "Dart": "#00B4AB", "GDScript": "#355570", "Rust": "#dea584", "Go": "#00ADD8", "Java": "#b07219",
    "Vue": "#41b883", "Svelte": "#ff3e00", "MDX": "#fcb32c", "Jupyter Notebook": "#DA5B0B",
}
FONT = "font-family=\"-apple-system,'Segoe UI',Helvetica,Arial,sans-serif\""


def api(path, body=None):
    url = "https://api.github.com/" + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers={
        "Accept": "application/vnd.github+json",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def public_repos():
    repos, page = [], 1
    while True:
        batch = api(f"users/{USER}/repos?type=owner&per_page=100&page={page}")
        repos += batch
        if len(batch) < 100:
            return [r for r in repos if not r["fork"]]
        page += 1


def contributions():
    """Beiträge im letzten Jahr + aktuelle und längste Serie (braucht Token)."""
    if not TOKEN:
        return None
    q = """query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{
           totalContributions weeks{contributionDays{date contributionCount}}}}}}"""
    cal = api("graphql", {"query": q, "variables": {"u": USER}})["data"]["user"][
        "contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        longest = max(longest, run)
    current = 0
    for d in reversed(days):
        # Heute ohne Beitrag bricht die Serie noch nicht ab.
        if d["contributionCount"]:
            current += 1
        elif d["date"] != date.today().isoformat():
            break
    return cal["totalContributions"], current, longest


def wrap(text, width, lines):
    words, out, line = text.split(), [], ""
    for w in words:
        if len(line) + len(w) + 1 > width and line:
            out.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    out.append(line)
    if len(out) > lines:
        out = out[:lines]
        out[-1] = out[-1][: width - 1].rstrip() + "…"
    return out


def describe(r):
    if r.get("description"):
        return r["description"]
    if r.get("homepage"):
        return "Live: " + re.sub(r"^https?://|/$", "", r["homepage"])
    return "Open-Source-Projekt von " + USER


def star_icon(x, y):
    return (f'<path transform="translate({x},{y})" fill="{MUTED}" d="M8 .25a.75.75 0 0 1 .673.418l1.882 '
            '3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.75.75 0 0 1-1.088.791L8 '
            '12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21'
            '-.611L7.327.668A.75.75 0 0 1 8 .25Z"/>')


def repo_card(r):
    name = escape(r["name"])
    desc = [escape(l) for l in wrap(describe(r), 52, 2)]
    lang = r.get("language") or ""
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="120" viewBox="0 0 400 120" {FONT}>',
             f'<title>{name}</title>',
             f'<rect x="0.5" y="0.5" width="399" height="119" rx="8" fill="{BG}" stroke="{BORDER}"/>',
             f'<path transform="translate(20,18)" fill="{MUTED}" d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 '
             '.75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 '
             '1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 '
             '0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.25.25 0 0 0-.3 0L5.4 15.7a.25.25 '
             '0 0 1-.4-.2Z"/>',
             f'<text x="44" y="31" fill="{TITLE}" font-size="16" font-weight="600">{name}</text>']
    for i, line in enumerate(desc):
        parts.append(f'<text x="20" y="{58 + i * 18}" fill="{TEXT}" font-size="13">{line}</text>')
    x = 20
    if lang:
        parts.append(f'<circle cx="{x + 6}" cy="99" r="6" fill="{LANG_COLORS.get(lang, MUTED)}"/>')
        parts.append(f'<text x="{x + 18}" y="104" fill="{MUTED}" font-size="12">{escape(lang)}</text>')
        x += 30 + len(lang) * 7
    parts.append(star_icon(x, 91))
    parts.append(f'<text x="{x + 21}" y="104" fill="{MUTED}" font-size="12">{r["stargazers_count"]}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def stats_card(repos, user, contrib):
    stars = sum(r["stargazers_count"] for r in repos)
    rows = [("Sterne gesamt", stars), ("Öffentliche Repos", user["public_repos"]), ("Follower", user["followers"])]
    if contrib:
        rows += [("Beiträge (12 Monate)", contrib[0]), ("Aktuelle Serie", f"{contrib[1]} Tage"),
                 ("Längste Serie", f"{contrib[2]} Tage")]
    langs = Counter(r["language"] for r in repos if r.get("language")).most_common(6)
    total = sum(n for _, n in langs) or 1
    h = 72 + max(len(rows), len(langs)) * 26
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="{h}" viewBox="0 0 800 {h}" {FONT}>',
         f'<title>GitHub-Statistik {USER}</title>',
         f'<rect x="0.5" y="0.5" width="799" height="{h - 1}" rx="8" fill="{BG}" stroke="{BORDER}"/>',
         f'<text x="28" y="38" fill="{TITLE}" font-size="18" font-weight="600">GitHub-Statistik</text>',
         f'<text x="430" y="38" fill="{TITLE}" font-size="18" font-weight="600">Sprachen (nach Repos)</text>']
    for i, (label, val) in enumerate(rows):
        y = 74 + i * 26
        p.append(f'<text x="28" y="{y}" fill="{TEXT}" font-size="14">{label}</text>')
        p.append(f'<text x="370" y="{y}" fill="{TEXT}" font-size="14" font-weight="600" text-anchor="end">{val}</text>')
    x = 430
    for lang, n in langs:
        w = 340 * n / total
        p.append(f'<rect x="{x:.1f}" y="52" width="{w:.1f}" height="8" fill="{LANG_COLORS.get(lang, MUTED)}"/>')
        x += w
    for i, (lang, n) in enumerate(langs):
        y = 88 + i * 24
        p.append(f'<circle cx="436" cy="{y - 4}" r="5" fill="{LANG_COLORS.get(lang, MUTED)}"/>')
        p.append(f'<text x="450" y="{y}" fill="{TEXT}" font-size="13">{escape(lang)}</text>')
        p.append(f'<text x="770" y="{y}" fill="{MUTED}" font-size="13" text-anchor="end">{100 * n / total:.0f} %</text>')
    p.append("</svg>")
    return "\n".join(p)


def grid(repos):
    # Feste Breite statt Tabelle: Desktop zeigt zwei nebeneinander, Handy eine pro Zeile.
    return "\n".join(f'<a href="{r["html_url"]}"><img src="{RAW}/repo-{r["name"]}.svg" width="400" '
                     f'alt="{escape(r["name"])}"/></a>' for r in repos)


def replace_block(readme, key, content):
    pattern = re.compile(rf"(<!-- {key}:START -->).*?(<!-- {key}:END -->)", re.S)
    return pattern.sub(lambda m: f"{m.group(1)}\n{content}\n{m.group(2)}", readme)


def main():
    os.makedirs(OUT, exist_ok=True)
    repos = public_repos()
    showcase = [r for r in repos if not r["archived"] and r["name"] not in SKIP
                and (r.get("description") or r.get("homepage"))]
    user = api(f"users/{USER}")
    featured = sorted(showcase, key=lambda r: (-r["stargazers_count"], r["name"].lower()))[:FEATURED_COUNT]
    recent_cut = (date.today() - timedelta(days=60)).isoformat()
    building = [r for r in sorted(showcase, key=lambda r: r["pushed_at"], reverse=True)
                if r not in featured and r.get("description") and r["pushed_at"] >= recent_cut][:BUILDING_COUNT]
    for r in featured + building:
        with open(os.path.join(OUT, f"repo-{r['name']}.svg"), "w") as f:
            f.write(repo_card(r))
    with open(os.path.join(OUT, "stats.svg"), "w") as f:
        f.write(stats_card(repos, user, contributions()))
    with open("README.md") as f:
        readme = f.read()
    readme = replace_block(readme, "FEATURED", grid(featured))
    readme = replace_block(readme, "BUILDING", grid(building))
    with open("README.md", "w") as f:
        f.write(readme)
    print("Featured:", [r["name"] for r in featured])
    print("Building:", [r["name"] for r in building])


if __name__ == "__main__":
    main()
