# Lab website

A small static site. Content lives in plain text files under `content/`;
`build.py` turns them into HTML in `_site/`; GitHub Actions publishes that to
GitHub Pages on every push to `main`.

You do not need to understand the code to update the site. Almost every change
is an edit to one file in `content/`.

---

## One-time setup

1. Create a repository. If you name it `YOURNAME.github.io` the site lives at
   `https://yourname.github.io`; any other name puts it at
   `https://yourname.github.io/reponame/` — both work, no config needed.
2. Push this directory to it.
3. In the repo, go to **Settings → Pages → Build and deployment** and set
   **Source** to **GitHub Actions**.
4. Push once more. The site is live in about a minute.

For a custom domain, add a file called `CNAME` at the top level containing just
`lab.example.edu`, and point the DNS record at GitHub. The build copies it
across.

## Working on it locally

```bash
pip install -r requirements.txt
python build.py --serve      # http://localhost:8000
```

Rerun the command after editing. There is no watcher — a rebuild takes well
under a second.

---

## How to make the usual changes

### Add or remove a person

Edit `content/team.yml`. Copy an existing block, change the fields. Only `name`
is required.

```yaml
      - name: Wei Chen
        role: PhD student, 1st year
        photo: wei.jpg          # optional; omit for an initials tile
        bio: One sentence about what they work on.
        email: wei@example.edu
        links:
          - label: GitHub
            url: https://github.com/example
```

Photos go in `static/img/`. Anything roughly square works; the site crops to a
square and scales it. **Do not hold up adding someone because you lack a
photo** — the initials tile is a deliberate part of the design, and a page where
half the lab is missing is worse than one with mixed portraits.

When someone leaves, move their entry to the `alumni:` list at the bottom of
the file and add where they went. Prospective students read that section
closely.

### Add a paper

Paste the BibTeX into `content/publications.bib`. That is the whole job —
sorting, grouping by year and bolding lab members happen automatically.

Four non-standard fields are understood:

| Field | Effect |
| --- | --- |
| `pdf = {https://...}` | adds a PDF link |
| `code = {https://...}` | adds a Code link |
| `data = {https://...}` | adds a Data link |
| `award = {Best paper}` | shown next to the venue |
| `selected = {true}` | also shows it on the homepage |

Anything else in the entry (abstract, keywords, pages) is ignored, so paste the
full record without trimming it.

**If a name is not bolded** it is because the spelling on the paper differs from
`team.yml` — accents, initials, a changed surname. Add the variant to
`lab_authors` in `content/site.yml`. Matching is on surname plus first initial,
so `I. Molnár` and `István Molnár` already match each other.

### Add a project

Edit `content/projects.yml`. `blurb` is the summary; `body` is the longer text
that appears only on the research page and accepts Markdown. Set
`featured: true` to put it on the homepage — two or three is plenty.

### Post news

Add an entry at the top of `content/news.yml`. Newest first; the homepage shows
six. Markdown links work. Keep each to one line — it is a changelog, not a blog.

### Add a page

Drop a Markdown file in `content/pages/`. It gets its own URL and appears in the
nav automatically. Front matter is optional:

```markdown
---
title: Teaching
slug: teaching
nav: true        # set false to keep it out of the nav
---

Text goes here.
```

### Change how it looks

- **Accent colour**: `accent:` in `content/site.yml`. That one value drives
  links, buttons and highlights across the whole site.
- **Everything else**: the top of `static/css/site.css`. Colours, fonts and
  spacing are all variables in the `:root` block.
- **The opening sentence**: `statement:` in `content/site.yml`. It is the most
  read line on the site. Say what you study, not what field you are in.
- **A hero image**: uncomment `hero_image:` in `content/site.yml` and put the
  file in `static/img/`. A real figure from your work is the strongest thing
  you can put there.

---

## If something breaks

The build fails loudly rather than publishing a broken page, and pull requests
build without deploying, so a bad edit shows up as a failed check.

- **The Actions run failed.** Open the run and read the error. It is nearly
  always YAML indentation. YAML wants spaces, never tabs, and every item in a
  list needs the same indent as its siblings.
- **A colon inside a value.** Wrap the value in quotes:
  `role: "Postdoc: imaging"`.
- **A person's photo does not appear.** The build prints a warning naming the
  missing file. Check the filename matches exactly, including case.
- **Changes are not showing up.** Check the Actions tab finished green, then
  hard-reload the page.

## For whoever inherits this

`build.py` is about 200 lines and has no framework underneath it. The pieces:

```
content/            everything you edit
templates/          Jinja2 templates, one per page type
static/             CSS, JS and images, copied across as-is
build.py            reads content/, renders templates/, writes _site/
.github/workflows/  build and publish on push
```

Adding a new page type means adding a template and one line to the `targets`
list in `build.py`. Nothing else is coupled.
