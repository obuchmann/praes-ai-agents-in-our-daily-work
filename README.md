# Tell & Show

Slides for the talk "Agentic Development - Tell & Show" at a .NET meetup.

Two speakers share the talk. Tell parts are slides. Show parts are live demos without slides. The speaker of a slide shows only by colour in the two-track strip at the bottom.

## Build

```bash
python3 build.py
```

This makes `talk.html` from `talk.md` and `template.html`. It uses the standard library only. The result is one file and works offline.

The build stops if a slide shows a speaker's name or a link. Notes stay in `talk.html`, so sharing the file shares the notes.

## Tests

```bash
python3 -m unittest
```

## Format of talk.md

The header holds the talk details:

```
event: .NET Meetup
duration: 45 min
date: tbd
speakers: oliver=blue, andi=yellow
```

Each `#` heading starts a slide. Fields follow directly below it:

| Field | Meaning |
|---|---|
| `speaker:` | Who speaks: one name, or two separated by a comma. Required. |
| `kind:` | `title`, `tell` (default) or `end` |
| `subtitle:` | Line below the title |
| `branch:` | Branch from the flow diagram, shown as a side note. May repeat. |
| `demo-after:` | Live demos after the slide: `Name (speaker) link`, several separated by `;` |
| `file:` | Name in the editor tab. Default: number and title, e.g. `05-skills.md`. |

The content comes next. Lines with `- ` are bullet points. `## ` is a sub-heading. `**bold**`, `*italic*` and `` `code` `` work too. Everything after `Note:` up to the next slide is a speaker note.

`demo-after` shows up in the notes ("Then live demo: ...") and in the strip at the bottom as a dashed box in the Show track.

## Present

Open `talk.html` in a browser.

| Key | Action |
|---|---|
| → ↓ PageDown Space | next slide |
| ← ↑ PageUp | previous slide |
| Home / End | first / last slide |
| F | fullscreen |
| N | presenter notes in a second window (clock, next slide) |

In the notes window, → and ← move the slides too. T resets the clock. The address remembers the slide (`talk.html#5`), so a reload stays there.

## Print

Print to PDF from the browser, without headers and footers. One slide per page.
