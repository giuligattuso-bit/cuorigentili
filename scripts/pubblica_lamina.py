#!/usr/bin/env python3
"""Pubblica sul sito le lámine programmate la cui ora di uscita è passata.

Legge laminas/manifest.json e i file in laminas/files/<data>/ (copiati dal ramo
`programmati` dal workflow), copia i file al loro posto nel sito e aggiunge la
scheda in cima alle pagine di download in ES, EN e IT.

Uso: python3 scripts/pubblica_lamina.py <cartella_programmati> [--now 2026-11-28T09:31]
"""
import datetime as dt
import json
import os
import re
import shutil
import sys
from html import escape
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")
RELEASE_TIME = dt.time(9, 30)  # ora di Madrid: poco prima del post delle 10:30

PAGES = {
    "es": dict(page="descargas/index.html", base="descargas/",
               weekly="Lámina de la semana", meta="PDF gratuito · 1 página · A4",
               btn="Descargar PDF", alt="Vista previa: "),
    "en": dict(page="en/downloads/index.html", base="en/downloads/",
               weekly="Colouring page of the week", meta="Free PDF · 1 page · A4",
               btn="Download PDF", alt="Preview: "),
    "it": dict(page="it/download/index.html", base="it/download/",
               weekly="Disegno della settimana", meta="PDF gratuito · 1 pagina · A4",
               btn="Scarica il PDF", alt="Anteprima: "),
}
SVG = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '
       'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="vertical-align:-4px;margin-right:8px">'
       '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/></svg>')


def card(date, lang, info):
    p = PAGES[lang]
    rel = lambda path: path[len(p["base"]):] if path.startswith(p["base"]) else "/" + path
    title = escape(info["title"])
    return (
        f'<article class="cg-dl-card" id="lamina-semana" data-lamina="{date}">\n'
        f'<div class="cg-dl-thumb"><img src="{rel(info["img"])}" alt="{p["alt"]}{title}" width="828" height="1171" loading="lazy"></div>\n'
        f'<div class="cg-dl-body">\n'
        f'<p class="cg-dl-meta">{p["weekly"]} · {p["meta"]}</p>\n'
        f'<h2>{title}</h2>\n'
        f'<p class="cg-p">{escape(info["desc"])}</p>\n'
        f'<div class="cg-btns"><a class="cg-btn" href="{rel(info["pdf"])}" download>{SVG}{p["btn"]}</a></div>\n'
        f'</div>\n</article>\n'
    )


def add_card(lang, date, info):
    p = PAGES[lang]
    html = open(p["page"], encoding="utf-8").read()
    if f'data-lamina="{date}"' in html:
        return False
    # la lámina precedente perde l'etichetta "della settimana" e l'ancora #lamina-semana
    html = re.sub(r'id="lamina-semana" data-lamina="([\d-]+)"', r'id="lamina-\1" data-lamina="\1"', html)
    html = html.replace(f'{p["weekly"]} · {p["meta"]}', p["meta"])
    marker = '<div class="cg-dl-grid">\n'
    assert html.count(marker) == 1, f"griglia non trovata in {p['page']}"
    html = html.replace(marker, marker + card(date, lang, info), 1)
    open(p["page"], "w", encoding="utf-8").write(html)
    return True


def main():
    src = sys.argv[1]
    now = dt.datetime.now(MADRID)
    if "--now" in sys.argv:
        now = dt.datetime.fromisoformat(sys.argv[sys.argv.index("--now") + 1]).replace(tzinfo=MADRID)
    manifest = json.load(open(os.path.join(src, "manifest.json"), encoding="utf-8"))
    published = []
    for entry in sorted(manifest, key=lambda e: e["date"]):
        release = dt.datetime.combine(dt.date.fromisoformat(entry["date"]), RELEASE_TIME, MADRID)
        if release > now:
            continue
        files = os.path.join(src, "files", entry["date"])
        if not os.path.isdir(files):
            continue
        changed = False
        for lang, info in entry["langs"].items():
            for key in ("pdf", "img"):
                dst = info[key]
                if not os.path.exists(dst):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(os.path.join(files, dst), dst)
                    changed = True
            changed |= add_card(lang, entry["date"], info)
        if changed:
            published.append(entry["date"])
    print("Pubblicate:", ", ".join(published) if published else "nessuna")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
            fh.write(f"published={' '.join(published)}\n")


if __name__ == "__main__":
    main()
