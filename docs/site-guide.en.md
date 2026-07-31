---
title: Lesson site guide
description: How to run, edit, verify, and hand off this project's MkDocs lesson site.
---

<p class="lesson-kicker">SITE GUIDE · READ · EDIT · VERIFY</p>

# Turn Markdown lessons into a website

This page is for readers, maintainers, and coding agents entering the repository for the first
time. After reading it, you should be able to start the lesson site, edit lessons, maintain both
languages, and verify the generated result.

## 1. What MkDocs does here

MkDocs is a static documentation site generator. It reads Markdown, site configuration, and style
files, then generates HTML, CSS, and JavaScript that a browser can open.

```text
Markdown lessons in docs/
          +
navigation and plugin configuration in mkdocs.yml
          +
custom CSS and JavaScript
          ↓
        MkDocs
          ↓
static website in site/
```

This project adds three layers on top of MkDocs:

| Component | Purpose |
| --- | --- |
| Material for MkDocs | Provides navigation, search, code copying, color schemes, and responsive pages |
| `mkdocs-static-i18n` | Builds Chinese and English sites and switches languages on the same page |
| Custom styles and scripts | Provide the lesson palette, typography, course cards, and reading progress bar |

!!! tip "The most important rule"

    Edit the Markdown and assets in `docs/`; do not edit `site/`. Every build regenerates `site/`,
    so manual changes there will be lost.

## 2. Know the project files

| Location | Purpose | Edit manually? |
| --- | --- | --- |
| `mkdocs.yml` | Site name, navigation, theme, languages, and Markdown extensions | Yes |
| `docs/` | Markdown lesson sources | Yes |
| `docs/assets/stylesheets/extra.css` | Lesson visual design | Yes |
| `docs/assets/javascripts/reading-progress.js` | Reading progress bar | Yes |
| `pyproject.toml`, `uv.lock` | Locked MkDocs and plugin versions | Only when upgrading dependencies |
| `site/` | Generated static site, ignored by Git | No |

## 3. Run it for the first time

From the repository root, run:

```bash
uv sync
uv run mkdocs serve
```

`uv sync` installs the project's locked dependencies. `mkdocs serve` starts a local development
server and watches files for changes. The terminal prints the actual address, usually something
like:

```text
http://127.0.0.1:8000/openai-agents-sdk-learning-lab/
```

Use the address printed by the terminal. After it opens, changing a Markdown or style file causes
MkDocs to rebuild, and the browser normally refreshes automatically.

To choose a port explicitly, run:

```bash
uv run mkdocs serve --dev-addr 127.0.0.1:8123
```

The port must not already be in use. To stop the server, press `Ctrl+C` in its terminal.

## 4. Everyday editing workflow

A normal lesson change needs only these steps:

1. Find the relevant Markdown source under `docs/`.
2. Update the Chinese and English versions together.
3. Keep `uv run mkdocs serve` running and inspect layout and links in the browser.
4. Run a strict build when the edit is complete.
5. Review the Git diff and confirm that no generated or unrelated file changed.

The strict build command is:

```bash
uv run mkdocs build --strict
```

This command regenerates `site/`. Invalid configuration, pages MkDocs cannot process, or a MkDocs
warning fails the strict build, so this is a better handoff check than looking only at the browser.

## 5. Chinese and English file rules

The site uses the suffix structure. Chinese is the default version; English adds `.en` to the file
name:

```text
docs/topic.md
docs/topic.en.md
```

Each document pair must keep the same code, commands, link targets, status, numbers, and completion
criteria. Accepted professional terms may remain in English in the Chinese page; interface names
must not change for translation.

In the main `nav` in `mkdocs.yml`, use only the default file name:

```yaml
nav:
  - 新页面: topic.md
```

Then add the English navigation title:

```yaml
nav_translations:
  新页面: New page
```

Internal Markdown links should also point to the default file name, for example:

```markdown
[M00](lessons/m00-first-agent.md)
```

When the English site is built, the i18n plugin selects the matching `.en.md` page. Chinese and
English headings may produce different anchors, so check both pages when linking to a heading.

## 6. Add a lesson page

Follow this order:

1. Create the Chinese `docs/<name>.md`.
2. Create the English `docs/<name>.en.md`.
3. Give both files the same scope and completion criteria.
4. Add the default file to `nav` in `mkdocs.yml`.
5. Add its navigation translation to `nav_translations` for English.
6. Open the Chinese and English pages, then test language switching and internal links.
7. Run `uv run mkdocs build --strict`.

The plugin can fall back to the default page when only one language exists, but this project does
not use that fallback as the normal practice for user documentation.

## 7. Verification and handoff

For a lesson-only change, run at least:

```bash
uv run mkdocs build --strict
```

Before handing off a complete repository change, also run:

```bash
uv run ruff check .
uv run pyright
uv run pytest
```

Finally, confirm that:

- both Chinese and English pages open;
- language switching stays on the same chapter;
- code blocks, tables, admonitions, and expandable answers render correctly;
- no local link is broken;
- `site/` is not tracked by Git;
- no API key or other sensitive data appears in a document or screenshot.

## 8. Troubleshooting

### The `mkdocs` command is missing

Do not globally install a different version. From the repository root, run:

```bash
uv sync
```

Then always use the project's locked version through `uv run mkdocs ...`.

### The port is already in use

Choose an unused port:

```bash
uv run mkdocs serve --dev-addr 127.0.0.1:8124
```

### The page does not change after an edit

Confirm that you edited a source under `docs/`, not `site/`. Check that the server terminal finished
rebuilding, then refresh the browser. If it still does not change, stop and restart
`uv run mkdocs serve`.

### The English page is missing or language switching returns home

Confirm that the English file has the `.en.md` suffix and that both files have matching relative
locations and default names. Run a strict build to see the exact error.

### The build prints an announcement or warning

First check the command's final exit status. Locked tools sometimes print an upstream project
announcement; an announcement alone does not mean the build failed. A real warning returns a
nonzero status under `--strict` and must be fixed according to its specific message.

## Agent operating checklist

An agent maintaining the lesson site should work in this order:

1. Read `mkdocs.yml`, this page, and the affected lesson sources first.
2. Inspect Git status and preserve existing user changes.
3. Modify only the Markdown, configuration, or assets required by the task.
4. Maintain the Chinese and English files together; never edit `site/`.
5. Run a strict build and inspect affected pages in the browser.
6. Check local links, language switching, and sensitive data.
7. In the handoff, list the changed locations, commands run, and verification results.

## References

- [MkDocs user guide](https://www.mkdocs.org/user-guide/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [MkDocs static i18n quick start](https://ultrabug.github.io/mkdocs-static-i18n/getting-started/quick-start/)
