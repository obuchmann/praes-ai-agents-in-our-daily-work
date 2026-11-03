#!/usr/bin/env python3
"""Build talk.html from talk.md and template.html.

Usage: python3 build.py [talk.md] [talk.html]

Standard library only. The result is one HTML file that loads nothing from
outside. The build fails if a slide shows a speaker's name or a link: the
speaker shows only by colour, links stay in the presenter notes.
"""
import html
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
HEADER_FIELDS = {"event", "duration", "date", "speakers"}
SLIDE_FIELDS = {"kind", "speaker", "subtitle", "branch", "demo-after", "file"}
KINDS = {"title", "tell", "end"}
COLOURS = {"blue", "yellow"}
FIELD = re.compile(r"^([a-z-]+):\s*(.*)$")
DEMO = re.compile(r"^(.+?)\s*\((\w+)\)\s*(\S+)?$")


class TalkError(Exception):
    pass


def esc(s):
    return html.escape(s, quote=True)


def inline(s):
    """Escape text and render **bold**, *em* and `code`."""
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", s)
    return s


def parse(text):
    header, slides, cur, in_note = {}, [], None, False
    for no, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if line.startswith("# "):
            cur = {"title": line[2:].strip(), "fields": {}, "branch": [], "body": [], "note": [], "line": no}
            slides.append(cur)
            in_note = False
            continue
        if cur is None:
            if not line:
                continue
            m = FIELD.match(line)
            if not m or m.group(1) not in HEADER_FIELDS:
                raise TalkError(f"line {no}: unknown header line: {line}")
            header[m.group(1)] = m.group(2)
            continue
        if in_note:
            cur["note"].append(line)
            continue
        if line.startswith("Note:"):
            in_note = True
            cur["note"].append(line[5:].strip())
            continue
        m = FIELD.match(line)
        if m and not cur["body"] and m.group(1) in SLIDE_FIELDS:
            key, val = m.groups()
            if key == "branch":
                cur["branch"].append(val)
            else:
                cur["fields"][key] = val
            continue
        if m and not cur["body"]:
            raise TalkError(f"line {no}: unknown field: {m.group(1)}")
        if line or cur["body"]:
            cur["body"].append(line)
    if not slides:
        raise TalkError("no slides: every slide starts with '# '")
    return header, slides


def speakers(header):
    out = {}
    for part in header.get("speakers", "").split(","):
        if not part.strip():
            continue
        name, _, colour = part.partition("=")
        name, colour = name.strip().lower(), colour.strip()
        if colour not in COLOURS:
            raise TalkError(f"speakers: colour must be blue or yellow: {part.strip()}")
        out[name] = colour
    if not out:
        raise TalkError("header: speakers missing, e.g. 'speakers: oliver=blue, andi=yellow'")
    return out


def resolve(header, slides):
    spk = speakers(header)
    tell_no = 0
    for s in slides:
        f = s["fields"]
        s["kind"] = f.get("kind", "tell")
        if s["kind"] not in KINDS:
            raise TalkError(f"line {s['line']}: kind must be one of {sorted(KINDS)}")
        names = [n.strip().lower() for n in f.get("speaker", "").split(",") if n.strip()]
        if not names:
            raise TalkError(f"line {s['line']}: '{s['title']}' has no speaker")
        for n in names:
            if n not in spk:
                raise TalkError(f"line {s['line']}: unknown speaker '{n}'")
        s["speakers"] = names
        s["colours"] = sorted({spk[n] for n in names}, key=["yellow", "blue"].index)
        s["demos"] = []
        for item in filter(None, (x.strip() for x in f.get("demo-after", "").split(";"))):
            m = DEMO.match(item)
            if not m or m.group(2).lower() not in spk:
                raise TalkError(f"line {s['line']}: demo-after needs 'Name (speaker) link': {item}")
            name, who, link = m.groups()
            s["demos"].append({"name": name, "speaker": who.lower(), "colour": spk[who.lower()], "link": link or "tbd"})
        if s["kind"] == "tell":
            tell_no += 1
            s["no"] = tell_no
    total = tell_no
    for s in slides:
        if "file" in s["fields"]:
            s["file"] = s["fields"]["file"]
        elif s["kind"] == "title":
            s["file"] = "00-title.md"
        elif s["kind"] == "end":
            s["file"] = f"{total + 1:02d}-{slug(s['title'])}.md"
        else:
            s["file"] = f"{s['no']:02d}-{slug(s['title'])}.md"
        s["total"] = total
    return spk


def slug(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "slide"


def colour_class(colours):
    return "both" if len(colours) > 1 else colours[0]


def track(slides, cur):
    """Two rows: Show (live demos, dashed) on top, Tell (slides) below."""
    cells = []  # (row, colour class, slide index, is live demo)
    for k, s in enumerate(slides):
        cells.append(("tell", colour_class(s["colours"]), k, False))
        if s["demos"]:
            cols = sorted({d["colour"] for d in s["demos"]}, key=["yellow", "blue"].index)
            cells.append(("show", colour_class(cols), k, True))
    n = len(cells)
    # The current cell is the slide itself. Its demo cell turns past on the next slide.
    cur_cell = next(j for j, c in enumerate(cells) if c[2] == cur and not c[3])
    out = [f'<nav class="track" aria-hidden="true" style="grid-template-columns:50px repeat({n},1fr)">']
    for row in ("show", "tell"):
        out.append(f"<b>{row.capitalize()}</b>")
        for j, (r, cls, _, live) in enumerate(cells):
            if r != row:
                out.append('<i class="empty"></i>')
                continue
            state = " cur" if j == cur_cell else " past" if j < cur_cell else ""
            out.append(f'<i class="{cls}{" live" if live else ""}{state}"></i>')
    out.append("</nav>")
    return "".join(out)


def body_lines(s, spk_header, slides):
    L = []
    if s["kind"] == "tell":
        L.append(f'<div class="l meta">&lt;!-- {s["no"]:02d} / {s["total"]:02d} --&gt;</div>')
    elif s["kind"] == "title":
        meta = " · ".join(x for x in (spk_header.get("event"), spk_header.get("duration")) if x)
        if meta:
            L.append(f'<div class="l meta">&lt;!-- {esc(meta)} --&gt;</div>')
    L.append(f'<div class="l h1"><span class="k"># </span>{inline(s["title"])}</div>')
    if "subtitle" in s["fields"]:
        L.append(f'<div class="l sub"><span class="k">&gt; </span>{inline(s["fields"]["subtitle"])}</div>')
    if s["body"]:
        L.append('<div class="l"></div>')
    for line in s["body"]:
        if line.startswith("## "):
            L.append(f'<div class="l h2"><span class="k">## </span>{inline(line[3:])}</div>')
        elif line.startswith("- "):
            L.append(f'<div class="l"><span class="k">- </span>{inline(line[2:])}</div>')
        else:
            L.append(f'<div class="l">{inline(line)}</div>')
    if s["kind"] == "title" and spk_header.get("date"):
        L.append('<div class="l"></div>')
        L.append(f'<div class="l meta">date: {esc(spk_header["date"])}</div>')
    if s["kind"] == "end":
        demos = [d["name"] for x in slides for d in x["demos"]]
        if demos:
            L.append('<div class="l"></div>')
            L.append('<div class="l h2"><span class="k">## </span>Live demos</div>')
            L.extend(f'<div class="l"><span class="k">- </span>{inline(d)}</div>' for d in demos)
    return "".join(L)



def notes(s, slides, k, spk):
    def who(name):
        return f'<span class="dot {spk[name]}"></span>{esc(name.capitalize())}'
    L = ["Speaker: " + " and ".join(who(n) for n in s["speakers"]) + "."]
    text = " ".join(x for x in s["note"] if x).strip()
    if text:
        L.append(inline(text))
    if s["demos"]:
        demos = ", ".join(f'{who(d["speaker"])}: {esc(d["name"])} ({esc(d["link"])})' for d in s["demos"])
        L.append(f'<span class="live">Then live demo: {demos}.</span>')
        nxt = slides[k + 1]["title"] if k + 1 < len(slides) else "the end"
        L.append(f"After the demo: press → for {esc(nxt)}.")
    return '<aside class="notes"><ul>' + "".join(f"<li>{x}</li>" for x in L) + "</ul></aside>"


def visible_text(fragment):
    fragment = re.sub(r'<aside class="notes">.*?</aside>', "", fragment, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment))


def render(header, slides):
    spk = resolve(header, slides)
    out = []
    for k, s in enumerate(slides):
        side = ""
        if s["branch"]:
            side = ('<aside class="side"><div class="sidel">Side note</div>'
                    + "".join(f'<div class="note">{inline(b)}</div>' for b in s["branch"]) + "</aside>")
        sec = (f'<section class="slide {s["kind"]}" data-title="{esc(s["title"])}" aria-label="{esc(s["title"])}"'
               f'{" hidden" if k else ""}>'
               f'<div class="tab"><span>{esc(s["file"])}</span></div><div class="gutter"></div>'
               f'<div class="code"><div class="lines">{body_lines(s, header, slides)}</div>{side}</div>'
               f'{track(slides, k)}{notes(s, slides, k, spk)}</section>')
        shown = visible_text(sec).lower()
        for name in spk:
            if re.search(rf"\b{re.escape(name)}\b", shown):
                raise TalkError(f"line {s['line']}: slide '{s['title']}' shows the name '{name}'. Names belong in the notes only.")
        if re.search(r"https?://", shown):
            raise TalkError(f"line {s['line']}: slide '{s['title']}' shows a link. Links belong in the notes only.")
        out.append(sec)
    return "\n".join(out)


def build(src, dst):
    header, slides = parse(src.read_text(encoding="utf-8"))
    page = (HERE / "template.html").read_text(encoding="utf-8")
    title = next((s["title"] for s in slides if s["fields"].get("kind") == "title"), slides[0]["title"])
    out = page.replace("{{TITLE}}", esc(title)).replace("{{SLIDES}}", render(header, slides))
    dst.write_text(out, encoding="utf-8")
    return slides


def main(argv):
    src = pathlib.Path(argv[1]) if len(argv) > 1 else HERE / "talk.md"
    dst = pathlib.Path(argv[2]) if len(argv) > 2 else HERE / "talk.html"
    try:
        slides = build(src, dst)
    except TalkError as e:
        raise SystemExit(f"{src.name}: {e}")
    breaks = sum(1 for s in slides if s["demos"])
    demos = sum(len(s["demos"]) for s in slides)
    print(f"{dst.name}: {len(slides)} slides, {breaks} live demo breaks ({demos} demos), "
          f"{dst.stat().st_size / 1024:.0f} KiB")


if __name__ == "__main__":
    main(sys.argv)
