# Obsidian-Flavored Markdown to PDF

Render Obsidian-style Markdown to a styled PDF from the command line using `pandoc`, headless Chrome, and a Minimal-inspired print stylesheet.

This tool is intended for local note export, not for faithfully reproducing every Obsidian plugin or internal rendering behavior.

## What It Supports

- `[[wiki links]]`
- `[[wiki links|alias]]`
- `![[embedded-image.png]]`
- Obsidian callouts such as `> [!NOTE]`
- inline comments written as `%% comment %%`
- `==highlight==`
- Mermaid code fences, rendered to SVG before PDF generation

## Requirements

Install these tools first:

- `pandoc`
- a Chromium-based browser with headless printing support
- `mmdc`

Notes:

- The script will try `google-chrome`, `chrome`, `chromium`, and `chromium-browser` for PDF printing.
- You can override browser detection with `--browser /path/to/browser` or `--browser chrome`.
- `mmdc` is only needed when your note contains Mermaid blocks.
- The script can render Markdown from any location.
- If the note lives inside an Obsidian vault, the nearest parent containing `.obsidian` is auto-detected and used as an extra search base for wiki links and embedded assets.
- You can override or supply that extra search base explicitly with `--vault /path/to/vault`.

## Installation

Run:

```bash
./install.sh
```

This installs the tool to:

- command: `~/.local/bin/obsidian-flavored-md-to-pdf`
- program files: `~/.local/share/obsidian-flavored-md-to-pdf/`
- stylesheet: `~/.local/share/obsidian-flavored-md-to-pdf/obsidian-minimal-print.css`

Make sure `~/.local/bin` is in your `PATH`.

## Usage

Export a note to PDF:

```bash
obsidian-flavored-md-to-pdf /path/to/note.md
```

Write to a specific output path:

```bash
obsidian-flavored-md-to-pdf /path/to/note.md -o /path/to/output.pdf
```

Generate HTML only:

```bash
obsidian-flavored-md-to-pdf /path/to/note.md --html-only
```

Keep the intermediate HTML file next to the PDF:

```bash
obsidian-flavored-md-to-pdf /path/to/note.md --keep-html
```

Use an explicit vault root as an extra search base for wiki links and embedded assets:

```bash
obsidian-flavored-md-to-pdf /path/to/note.md --vault /path/to/vault
```

Use a custom stylesheet:

```bash
obsidian-flavored-md-to-pdf /path/to/note.md --css /path/to/custom.css
```

Use a specific browser executable:

```bash
obsidian-flavored-md-to-pdf /path/to/note.md --browser chromium
```

Set an explicit title block:

```bash
obsidian-flavored-md-to-pdf /path/to/note.md --title "Custom Title"
```

Disable the generated title block:

```bash
obsidian-flavored-md-to-pdf /path/to/note.md --no-title-block
```

## How It Works

1. The input Markdown is preprocessed to handle Obsidian-style syntax.
2. Mermaid blocks are rendered to SVG with `mmdc`.
3. `pandoc` generates a standalone HTML file with embedded resources.
4. Headless Chrome prints that HTML file to PDF.

By default:

- the PDF is written next to the source note
- an intermediate HTML file is created temporarily and then removed
- the source note directory is always used for relative links and assets
- if a `.obsidian` directory is found above the note, that vault root is also used when resolving Obsidian-style wiki links
- if the source note has no level-1 heading, a title block is generated from the file name
- if the source note already has a level-1 heading, no extra title block is added by default
- `--title` forces an explicit title block, and `--no-title-block` disables it

## Mermaid Behavior

Mermaid blocks are rendered locally before the final HTML and PDF are produced.

- Mermaid comments such as `%%` and config blocks such as `%%{init: ...}%%` are preserved inside Mermaid code fences.
- Single-line Obsidian comments in normal document text are removed during preprocessing.

## Limitations

- This is not a 1:1 clone of Obsidian's built-in export.
- Plugin-generated content such as Excalidraw or Dataview is not reproduced automatically.
- Embedded Markdown notes such as `![[another-note]]` are not expanded inline.
- If a wiki link resolves outside the current note directory, it may be converted to a file URI in the generated HTML.
