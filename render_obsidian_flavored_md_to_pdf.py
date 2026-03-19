#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import shutil
import subprocess
import tempfile


DEFAULT_CSS = pathlib.Path(__file__).with_name("obsidian-minimal-print.css")


WIKILINK_RE = re.compile(r'(!)?\[\[([^\]\n]+)\]\]')
CALLOUT_RE = re.compile(r'^(?P<indent>\s*)>\s*\[!(?P<kind>[^\]\n]+)\]\s*(?P<title>.*)$')
FENCE_START_RE = re.compile(r"^(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
ATX_H1_RE = re.compile(r"^\s*#\s+(?P<title>.+?)\s*#*\s*$")
SETEXT_H1_RE = re.compile(r"^\s*=+\s*$")
BROWSER_CANDIDATES = [
    "google-chrome",
    "chrome",
    "chromium",
    "chromium-browser",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render Obsidian-flavored Markdown to PDF with a Minimal-inspired print style."
    )
    parser.add_argument("input", help="Input Markdown file")
    parser.add_argument("-o", "--output", help="Output PDF path")
    parser.add_argument(
        "--vault",
        help="Optional vault root used as an extra search base for wiki links and embedded assets.",
    )
    parser.add_argument(
        "--css",
        default=str(DEFAULT_CSS),
        help="CSS file used for HTML/PDF styling",
    )
    parser.add_argument(
        "--keep-html",
        action="store_true",
        help="Keep the intermediate HTML file next to the PDF",
    )
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="Only generate HTML and skip PDF rendering",
    )
    parser.add_argument(
        "--browser",
        help="Browser command used for PDF printing. Defaults to the first available Chrome/Chromium executable.",
    )
    parser.add_argument(
        "--title",
        help="Explicit document title for the generated title block. Defaults to the first level-1 heading, then the file name.",
    )
    parser.add_argument(
        "--no-title-block",
        action="store_true",
        help="Do not inject a Pandoc title block into the output document.",
    )
    return parser.parse_args()


def find_vault_root(path: pathlib.Path) -> pathlib.Path | None:
    for parent in [path.parent, *path.parents]:
        if (parent / ".obsidian").exists():
            return parent
    return None


def slugify_callout(kind: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "-", kind.strip().lower())
    return slug.strip("-") or "note"


def render_mermaid(mermaid_source: str, index: int, tmpdir: pathlib.Path) -> str:
    if shutil.which("mmdc") is None:
        raise SystemExit("mmdc is not installed, Mermaid rendering is unavailable")

    mermaid_hash = hashlib.sha1(mermaid_source.encode("utf-8")).hexdigest()[:10]
    source_path = tmpdir / f"mermaid-{index}-{mermaid_hash}.mmd"
    image_path = tmpdir / f"mermaid-{index}-{mermaid_hash}.svg"
    source_path.write_text(mermaid_source, encoding="utf-8")

    cmd = [
        "mmdc",
        "-q",
        "-i",
        str(source_path),
        "-o",
        str(image_path),
        "-e",
        "svg",
        "-b",
        "transparent",
        "-t",
        "default",
    ]
    result = subprocess.run(cmd, cwd=str(tmpdir), text=True, capture_output=True)
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise SystemExit(f"Failed to render Mermaid block {index}: {details}")
    return image_path.name


def convert_wikilink(
    raw: str, note_dir: pathlib.Path, vault_root: pathlib.Path | None, is_embed: bool
) -> str:
    target_part = raw
    alias = None
    if "|" in raw:
        target_part, alias = raw.split("|", 1)
    target_part = target_part.strip()
    alias = alias.strip() if alias else None

    if "#" in target_part:
        path_part, anchor = target_part.split("#", 1)
    else:
        path_part, anchor = target_part, None

    path_part = path_part.strip()
    display = alias or path_part or "link"

    if not path_part:
        return display

    candidates = []
    raw_path = pathlib.Path(path_part)
    if raw_path.is_absolute():
        candidates.append(raw_path)
    else:
        candidates.append(note_dir / raw_path)
        if vault_root is not None:
            candidates.append(vault_root / raw_path)
        if raw_path.suffix == "":
            candidates.append(note_dir / f"{path_part}.md")
            if vault_root is not None:
                candidates.append(vault_root / f"{path_part}.md")

    resolved = None
    for candidate in candidates:
        if candidate.exists():
            resolved = candidate.resolve()
            break

    href = path_part
    if resolved is not None:
        try:
            href = resolved.relative_to(note_dir.resolve()).as_posix()
        except ValueError:
            href = resolved.as_uri()
        if resolved.suffix.lower() == ".md":
            href = href[:-3] + ".html"

    if anchor:
        href = f"{href}#{anchor}"

    if is_embed:
        alt = alias or pathlib.Path(path_part).stem
        return f"![{alt}]({href})"
    return f"[{display}]({href})"


def preprocess_markdown(
    text: str, note_path: pathlib.Path, vault_root: pathlib.Path | None, tmpdir: pathlib.Path
) -> str:
    note_dir = note_path.parent

    def replace_wikilink(match: re.Match[str]) -> str:
        is_embed = bool(match.group(1))
        raw = match.group(2)
        return convert_wikilink(raw, note_dir, vault_root, is_embed)

    lines = text.splitlines()
    out: list[str] = []
    i = 0
    mermaid_index = 0
    while i < len(lines):
        line = lines[i]
        fence_start = FENCE_START_RE.match(line)
        if fence_start:
            fence = fence_start.group("fence")
            info = fence_start.group("info").strip().split(None, 1)
            language = info[0].lower() if info else ""
            block_lines = [line]
            i += 1
            while i < len(lines):
                current = lines[i]
                block_lines.append(current)
                if current.startswith(fence):
                    i += 1
                    break
                i += 1

            if language == "mermaid":
                mermaid_index += 1
                mermaid_source = "\n".join(block_lines[1:-1]).strip() + "\n"
                image_name = render_mermaid(mermaid_source, mermaid_index, tmpdir)
                out.append(f"![Mermaid diagram]({image_name}){{.mermaid-diagram}}")
            else:
                out.extend(block_lines)
            continue

        if line.strip().startswith("%%") and line.strip().endswith("%%"):
            i += 1
            continue

        callout = CALLOUT_RE.match(line)
        if not callout:
            out.append(WIKILINK_RE.sub(replace_wikilink, line))
            i += 1
            continue

        kind = slugify_callout(callout.group("kind"))
        title = callout.group("title").strip() or callout.group("kind").strip()
        indent = callout.group("indent")
        out.append(f'{indent}::: {{.callout .callout-{kind}}}')
        out.append(f'{indent}**{title}**')
        i += 1
        while i < len(lines):
            current = lines[i]
            if current.startswith(f"{indent}> "):
                content = current[len(indent) + 2 :]
                out.append(indent + WIKILINK_RE.sub(replace_wikilink, content))
                i += 1
                continue
            if current == f"{indent}>":
                out.append("")
                i += 1
                continue
            break
        out.append(f"{indent}:::")

    return "\n".join(out) + "\n"


def infer_document_title(text: str, fallback: str) -> tuple[str, bool]:
    lines = text.splitlines()
    in_front_matter = False
    in_fence: str | None = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        if i == 0 and stripped == "---":
            in_front_matter = True
            continue
        if in_front_matter:
            if stripped == "---" or stripped == "...":
                in_front_matter = False
            continue

        fence_start = FENCE_START_RE.match(line)
        if in_fence is not None:
            if line.startswith(in_fence):
                in_fence = None
            continue
        if fence_start:
            in_fence = fence_start.group("fence")
            continue

        if stripped.startswith("%%") and stripped.endswith("%%"):
            continue

        atx_h1 = ATX_H1_RE.match(line)
        if atx_h1:
            return atx_h1.group("title").strip(), True

        if i + 1 < len(lines) and line.strip() and SETEXT_H1_RE.match(lines[i + 1]):
            return line.strip(), True

    return fallback, False


def run(cmd: list[str], cwd: pathlib.Path) -> None:
    result = subprocess.run(cmd, cwd=str(cwd), text=True)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def find_browser(browser: str | None) -> str:
    candidates = [browser] if browser else BROWSER_CANDIDATES
    for candidate in candidates:
        if not candidate:
            continue
        resolved = shutil.which(candidate)
        if resolved is not None:
            return resolved

    if browser:
        raise SystemExit(f"Browser executable not found: {browser}")

    available = ", ".join(BROWSER_CANDIDATES)
    raise SystemExit(f"No supported browser executable found. Tried: {available}")


def main() -> None:
    args = parse_args()
    input_path = pathlib.Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    vault_root = pathlib.Path(args.vault).expanduser().resolve() if args.vault else find_vault_root(input_path)
    css_path = pathlib.Path(args.css).expanduser().resolve()
    if not css_path.exists():
        raise SystemExit(f"CSS file not found: {css_path}")

    output_pdf = pathlib.Path(args.output).expanduser().resolve() if args.output else input_path.with_suffix(".pdf")
    output_html = output_pdf.with_suffix(".html")

    if shutil.which("pandoc") is None:
        raise SystemExit("pandoc is not installed")
    browser_cmd = None if args.html_only else find_browser(args.browser)

    with tempfile.TemporaryDirectory(prefix="obsidian-export-") as tmp:
        tmpdir = pathlib.Path(tmp)
        raw = input_path.read_text(encoding="utf-8")
        prepared = preprocess_markdown(raw, input_path, vault_root, tmpdir)
        prepared_md = tmpdir / input_path.name
        html_path = tmpdir / output_html.name
        prepared_md.write_text(prepared, encoding="utf-8")
        inferred_title, has_h1 = infer_document_title(raw, input_path.stem)
        document_title = args.title if args.title is not None else inferred_title

        resource_paths = [str(tmpdir), str(input_path.parent)]
        if vault_root is not None and vault_root != input_path.parent:
            resource_paths.append(str(vault_root))

        pandoc_cmd = [
            "pandoc",
            str(prepared_md),
            "--from=markdown+mark+wikilinks_title_after_pipe+fenced_divs+pipe_tables+task_lists+strikeout+smart",
            "--to=html5",
            "--standalone",
            "--embed-resources",
            f"--resource-path={':'.join(resource_paths)}",
            f"--css={css_path}",
            "--output",
            str(html_path),
        ]
        if not args.no_title_block and (args.title is not None or not has_h1):
            pandoc_cmd.insert(-2, f"--metadata=title:{document_title}")
        run(pandoc_cmd, cwd=input_path.parent)

        shutil.copy2(html_path, output_html)
        if args.html_only:
            print(f"HTML written to {output_html}")
            return

        chrome_cmd = [
            browser_cmd,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={output_pdf}",
            html_path.as_uri(),
        ]
        run(chrome_cmd, cwd=input_path.parent)

    if not args.keep_html and output_html.exists():
        output_html.unlink()

    print(f"PDF written to {output_pdf}")
    if args.keep_html:
        print(f"HTML written to {output_html}")


if __name__ == "__main__":
    main()
