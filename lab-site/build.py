#!/usr/bin/env python3
"""
Build the lab website.

    python build.py            # build into _site/
    python build.py --serve    # build, then serve at http://localhost:8000

Everything the site shows comes from the files in content/.
You should rarely need to edit this script.
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

import markdown as md
import yaml
from jinja2 import Environment, FileSystemLoader

try:
    import bibtexparser
    from bibtexparser.bparser import BibTexParser
    from bibtexparser.customization import convert_to_unicode
except ImportError:
    bibtexparser = None

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
OUT = ROOT / "_site"

MD = md.Markdown(extensions=["extra", "smarty"])


# --------------------------------------------------------------------------
# content loading
# --------------------------------------------------------------------------

def load_yaml(name, default=None):
    path = CONTENT / name
    if not path.exists():
        return default if default is not None else {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or (default if default is not None else {})


def render_md(text):
    """Markdown -> HTML. Safe on None."""
    if not text:
        return ""
    MD.reset()
    return MD.convert(str(text))


def load_pages():
    """Markdown files in content/pages/ become standalone pages.

    Optional YAML front matter at the top sets `title` and `slug`.
    """
    pages = []
    for path in sorted((CONTENT / "pages").glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = {}, raw
        if raw.startswith("---"):
            _, fm, body = raw.split("---", 2)
            meta = yaml.safe_load(fm) or {}
        pages.append({
            "slug": meta.get("slug", path.stem),
            "title": meta.get("title", path.stem.replace("-", " ").title()),
            "nav": meta.get("nav", True),
            "body": render_md(body),
        })
    return pages


# --------------------------------------------------------------------------
# publications
# --------------------------------------------------------------------------

LATEX = {r"\&": "&", r"\%": "%", r"\_": "_", r"\#": "#", r"\$": "$",
         "{": "", "}": "", "~": " ", r"\\": ""}


def clean(text):
    if not text:
        return ""
    text = re.sub(r"\s+", " ", str(text)).strip()
    for a, b in LATEX.items():
        text = text.replace(a, b)
    return text.strip()


def split_authors(field):
    """'Curie, Marie and Pierre Curie' -> ['Marie Curie', 'Pierre Curie']"""
    out = []
    for raw in re.split(r"\s+and\s+", clean(field)):
        raw = raw.strip().rstrip(",")
        if not raw:
            continue
        if "," in raw:
            last, first = [p.strip() for p in raw.split(",", 1)]
            raw = f"{first} {last}".strip()
        out.append(raw)
    return out


def name_key(name):
    """Loose match key: last name + first initial. Handles 'M. Curie' vs 'Marie Curie'."""
    parts = [p for p in re.split(r"\s+", name.strip()) if p]
    if not parts:
        return ""
    last = parts[-1].lower()
    initial = parts[0][0].lower() if len(parts) > 1 else ""
    return f"{last}|{initial}"


VENUE_FIELDS = ["journal", "booktitle", "school", "institution", "publisher", "howpublished"]

TYPE_LABELS = {
    "article": "Journal",
    "inproceedings": "Conference",
    "conference": "Conference",
    "incollection": "Chapter",
    "book": "Book",
    "phdthesis": "Thesis",
    "mastersthesis": "Thesis",
    "misc": "Preprint",
    "unpublished": "Preprint",
    "techreport": "Report",
}


def load_publications(lab_names):
    """Parse content/publications.bib into template-friendly dicts."""
    path = CONTENT / "publications.bib"
    if not path.exists() or bibtexparser is None:
        return []

    parser = BibTexParser(common_strings=True)
    parser.customization = convert_to_unicode
    parser.ignore_nonstandard_types = False
    with open(path, encoding="utf-8") as f:
        db = bibtexparser.load(f, parser)

    lab_keys = {name_key(n) for n in lab_names}
    pubs = []

    for e in db.entries:
        authors = split_authors(e.get("author") or e.get("editor", ""))
        venue = next((clean(e[f]) for f in VENUE_FIELDS if e.get(f)), "")
        if not venue and e.get("eprint"):
            venue = f"arXiv:{clean(e['eprint'])}"

        links = []
        for label, field in [("DOI", "doi"), ("PDF", "pdf"), ("Code", "code"),
                             ("Data", "data"), ("Link", "url")]:
            val = clean(e.get(field, ""))
            if not val:
                continue
            if field == "doi":
                val = val if val.startswith("http") else f"https://doi.org/{val}"
            links.append({"label": label, "url": val})

        try:
            year = int(re.sub(r"\D", "", e.get("year", "0")) or 0)
        except ValueError:
            year = 0

        pubs.append({
            "key": e.get("ID", ""),
            "title": clean(e.get("title", "Untitled")).rstrip("."),
            "authors": [{"name": a, "is_lab": name_key(a) in lab_keys} for a in authors],
            "venue": venue,
            "year": year,
            "type": TYPE_LABELS.get(e.get("ENTRYTYPE", "").lower(), "Other"),
            "note": clean(e.get("note", "")),
            "award": clean(e.get("award", "")),
            "selected": str(e.get("selected", "")).lower() in ("true", "yes", "1"),
            "links": links,
        })

    pubs.sort(key=lambda p: (-p["year"], p["title"].lower()))
    return pubs


def group_by_year(pubs):
    years = []
    for p in pubs:
        if not years or years[-1]["year"] != p["year"]:
            years.append({"year": p["year"], "entries": []})
        years[-1]["entries"].append(p)
    return years


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------

def initials(name):
    parts = [p for p in re.split(r"\s+", name.strip()) if p and p[0].isalpha()]
    if not parts:
        return "?"
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


def build():
    site = load_yaml("site.yml")
    team = load_yaml("team.yml", {"groups": []})
    projects = load_yaml("projects.yml", {"projects": []})
    news = load_yaml("news.yml", {"news": []})
    pages = load_pages()

    site["footer_note_html"] = render_md(site.get("footer_note"))
    site["intro_html"] = render_md(site.get("intro"))

    lab_names = site.get("lab_authors", [])
    for group in team.get("groups", []):
        for person in group.get("people", []):
            lab_names.append(person["name"])
            person["initials"] = initials(person["name"])
            person["bio_html"] = render_md(person.get("bio"))
    for alum in team.get("alumni", []) or []:
        lab_names.append(alum["name"])

    pubs = load_publications(lab_names)

    for p in projects.get("projects", []):
        p["body_html"] = render_md(p.get("body"))
    for n in news.get("news", []):
        n["html"] = render_md(n.get("text")).replace("<p>", "").replace("</p>", "")

    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    groups = [g for g in team.get("groups", []) if g.get("people")]
    project_list = projects.get("projects", []) or []
    news_list = news.get("news", []) or []

    shared = {
        "site": site,
        "groups": groups,
        "alumni": team.get("alumni") or [],
        "featured_projects": [p for p in project_list if p.get("featured")],
        "selected_pubs": [p for p in pubs if p["selected"]],
        "team": team,
        "projects": project_list,
        "news": news_list,
        "pubs": pubs,
        "pub_years": group_by_year(pubs),
        "pub_types": sorted({p["type"] for p in pubs}),
        "pages": pages,
    }

    # (output path, template, extra context)
    targets = [
        ("index.html", "index.html", {"page_id": "home"}),
        ("team/index.html", "team.html", {"page_id": "team", "title": "Team"}),
        ("projects/index.html", "projects.html", {"page_id": "projects", "title": "Research"}),
        ("publications/index.html", "publications.html",
         {"page_id": "publications", "title": "Publications"}),
        ("404.html", "404.html", {"page_id": None, "title": "Page not found"}),
    ]
    for page in pages:
        targets.append((f"{page['slug']}/index.html", "page.html",
                        {"page_id": page["slug"], "title": page["title"], "page": page}))

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    for out_path, template, ctx in targets:
        depth = out_path.count("/")
        html = env.get_template(template).render(
            root="../" * depth, **shared, **ctx
        )
        dest = OUT / out_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf-8")
        print(f"  {out_path}")

    missing = []
    for group in team.get("groups", []):
        for person in group.get("people", []):
            if person.get("photo") and not (ROOT / "static" / "img" / person["photo"]).exists():
                missing.append(f"{person['name']}: static/img/{person['photo']}")
    for item in missing:
        print(f"  ! missing image — {item}", file=sys.stderr)

    shutil.copytree(ROOT / "static", OUT / "static")
    (OUT / ".nojekyll").touch()
    if (ROOT / "CNAME").exists():
        shutil.copy(ROOT / "CNAME", OUT / "CNAME")

    print(f"\nBuilt {len(targets)} pages and {len(pubs)} publications into {OUT}/")


def serve():
    import functools
    import http.server
    import socketserver

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))
    with socketserver.TCPServer(("", 8000), handler) as httpd:
        print("Serving at http://localhost:8000  (Ctrl-C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", action="store_true", help="serve the site after building")
    args = ap.parse_args()
    build()
    if args.serve:
        serve()
