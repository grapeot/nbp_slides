# Deprecated: use `presentation_skill`

This repository has been superseded by [presentation_skill](https://github.com/grapeot/presentation_skill), which consolidates the image-generated deck workflow from `nbp_slides` and the HTML fallback workflow from `cursor_slides` into one public AI-agent skill.

Use `presentation_skill` for new presentation deck work. This repository remains available as historical reference for the older Nano Banana Pro slide generation implementation.

---

# nbp_slides — AI Slide Deck Generator

An AI-powered slide deck generator that turns a content outline into a complete, visually styled presentation. Swap styles without touching the content — the same outline renders as clay sculpture, ink-wash calligraphy, dark-mode tech, or 30+ other looks.

This repository ships with the slides from the talk:

**从小龙虾看到的：Agent Harness 解读** (ADG 广州站)

Blog post: [中文](https://yage.ai/nano-banana-pro.html) · [English](https://yage.ai/nano-banana-pro-en.html)

---

## How It Works

```
outline_visual.md   ←  what to say (content, layout intent)
visual_guideline.md ←  how it looks (active style)
        │
        ▼
tools/generate_slides.py
        │  calls Gemini image generation API
        ▼
generated_slides/slide_NN_0.png  ...
        │
        ▼
openclaw-harness.pptx  +  index.html (Reveal.js viewer)
```

**Key design principle**: `outline_visual.md` only describes *what* to show (layout, text, data). All visual decisions come exclusively from `visual_guideline.md`, so changing the style is a one-file swap with no outline edits needed.

---

## Quick Start

### 1. Setup

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Create `.env` with your API key:

```
GOOGLE_API_KEY=your_key_here
```

### 2. Generate slides

```bash
# Generate all slides
python tools/generate_slides.py

# Generate specific slides only
python tools/generate_slides.py --slides 0 1 5

# Use SDK backend instead of llm-call
python tools/generate_slides.py --backend sdk
```

Images are saved to `generated_slides/slide_NN_0.png`.

### 3. Upscale to 4K

```bash
# Upscale all slides
python tools/generate_slides.py --enlarge

# Upscale specific slides
python tools/generate_slides.py --enlarge --slides 3 7
```

### 4. Export PPTX

```bash
python tools/export_pptx.py
```

Outputs `openclaw-harness.pptx` with speaker notes.

### 5. Present

Open `index.html` in a browser. Press `S` for speaker notes view (Reveal.js).

---

## Switching Styles

1. Copy the style definition you want from `styles/<category>/<style-id>/<style-id>.md` into `visual_guideline.md`
2. Archive the current run first (optional but recommended):
   ```bash
   python .claude/skills/archive-slides/scripts/archive_slides.py <topic> <old-style-id> --project-root .
   ```
3. Regenerate:
   ```bash
   python tools/generate_slides.py
   ```

---

## Style Library

34 styles across 6 categories. The complete catalog lives in `styles/manifest.json`.

Each style is self-contained:

```text
styles/<category>/<style-id>/
├── <style-id>.md          # reusable style definition
└── reference/
    ├── prompts.md         # prompts used for preview images
    └── *.jpg              # preview/reference images
```

| Category | Styles |
|---|---|
| business | `corporate-saas`, `minimalist-data`, `ted-style`, `archival-casefile`, `thermal-receipt-checklist` |
| creative | `ink-wash-wuxia` ⭐, `clay-mimicry`, `comic-book`, `rick-morty`, `vector-illustration`, `vintage-travel` |
| editorial | `bold-editorial`, `gradient-hero`, `retro-pop-swiss-grid`, `theater-ticket-scrapbook` |
| education | `ikea-style`, `mind-map`, `process-flow`, `sketchnote`, `soft-pastel-edu`, `storyboard`, `warm-academic-humanism`, `stationery-folder-clipboard`, `terracotta-doodle-notes`, `vintage-scrapbook-journal` |
| fun | `8bit-retro`, `cinematic-poster`, `minion-mayhem`, `whiteboard-strategy` |
| tech | `dark-mode-tech`, `gradient-glass`, `neon-nightlife`, `acid-retrofuturist-blocks`, `blueprint-pop-lab` |

⭐ = currently active style

---

## Project Structure

```
nbp_slides/
├── outline_visual.md        # Presentation content (style-agnostic)
├── visual_guideline.md      # Active style definition ← edit to switch styles
├── index.html               # Reveal.js viewer
├── openclaw-harness.pptx    # Exported presentation
│
├── tools/
│   ├── generate_slides.py        # Main generator
│   ├── gemini_generate_image.py  # Image generation API wrapper
│   ├── gemini_enlarge_image.py   # 4K upscaling wrapper
│   └── export_pptx.py            # PPTX builder with speaker notes
│
├── generated_slides/        # Output images (slide_NN_M.png)
│
├── styles/
│   ├── manifest.json        # Style catalog
│   ├── README.md
│   ├── business/
│   ├── creative/            # includes ink-wash-wuxia, clay-mimicry
│   ├── editorial/
│   ├── education/
│   ├── fun/
│   └── tech/
│       └── <style-id>/
│           ├── <style-id>.md
│           └── reference/
│
└── archive/                 # Versioned backups of previous style runs
    └── YYYY-MM-DD_topic_style/
```

---

## Writing Slide Content

Edit `outline_visual.md` using the `#### Slide N: Title` format. Each slide supports:

- `**Layout**`: spatial arrangement intent (e.g. "三列并排 + 底部汇聚框")
- `**Scene** > **文字叠加**`: text content to display
- `**Asset**`: path to a local image to inject, or `none`

**Do not** write style-specific rendering instructions in the outline. Style instructions belong in `visual_guideline.md` only.

---

## Archive Previous Runs

```bash
python .claude/skills/archive-slides/scripts/archive_slides.py <topic> <style-id> --project-root .
# Example:
python .claude/skills/archive-slides/scripts/archive_slides.py openclaw-harness clay-mimicry --project-root .
```

Archives are saved to `archive/YYYY-MM-DD_topic_style/` and include `visual_guideline.md`, `outline_visual.md`, and all slide PNGs.
