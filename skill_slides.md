# AI-Generated Presentation Slides Workflow

## Metadata

- **Type**: Workflow
- **Use cases**: Building high-quality presentations — internal corporate training, technical talks, conference keynotes, executive decks.
- **Repo**: https://github.com/grapeot/nbp_slides/
- **Origin**: Distilled from the Samsara AI talk series and follow-on production decks.

---

## Core Idea

Use an AI image-generation model (Gemini Image, or GPT-Image-2) to *render* an entire slide deck rather than assemble one. Each slide is a single high-resolution image — text and visual elements are generated as one cohesive whole.

**Key contrast:**

- Old way: Open PowerPoint or Keynote, drag elements onto the canvas, align them by hand.
- New way: Write a Markdown prompt per slide, let the model render the full image, then play the deck with Reveal.js.

---

## Step 1: Clone the Repo

```bash
git clone https://github.com/grapeot/nbp_slides/
cd nbp_slides
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Create a `.env` file (pick the backend you'll use):

```
# Gemini backend
GEMINI_API_KEY=your_key_here

# GPT-Image-2 backend
OPENAI_API_KEY=your_key_here
```

---

## Step 2: Define the Visual Style

Edit `visual_guideline.md`. This is the *visual anchor* every slide is generated against. Without a strong guideline, slides drift in style between renders.

### Yan's preferred style: "Clean Ink"

```
- Background: cool light grey (#F0F4F8) with an ultra-fine grid.
- Illustration style: deep navy line work, flat color fills, the precision of an engineering blueprint.
- Typography: sans-serif (Inter / SF Pro), every slide carries a bold header.
- Forbidden: photorealistic images, glossy 3D, generic clipart.
- Mascot: Samsara Owl (title and closing slide only).
```

### The critical balance: Presentation vs Handout (read this carefully)

**Slides must be Dual-Use — they are simultaneously a presentation tool and a handout.**

This is the central trade-off. At one extreme is Steve Jobs style (pure visual, indecipherable without the speaker). At the other extreme is the classroom-textbook style (pure text, "death by PowerPoint"). The sweet spot is in the middle:

- **As a handout**: Someone who didn't attend the talk should be able to grasp the core argument by reading the slides alone, without needing extra context.
- **As a presentation**: A latecomer or distracted listener can use the current slide to catch up to where the speaker is.

The dual requirement forces a hard rule: the text on each slide is not a "label" or "keyword cue" (Steve Jobs style) — it has to carry the actual argument. But it also cannot be paragraph-after-paragraph of body copy.

**Concrete execution standard:**

- **Target ratio**: roughly 40% illustration / 60% readable text.
- **Layout model**: left-right split — illustration / diagram / flow on the left, 2–4 lines of key text on the right.
- **Choosing the text**: the text on the slide should be the core argument itself, not a hint at it. A reader sees the text and immediately knows what you are saying.
- **Choosing the visual**: the illustration should be a conceptual diagram, comparison, or flow — something that aids understanding of the argument — not decorative filler.
- Text must be readable from the back of the room.
- **Self-check**: after writing a slide, cover the speaker notes and ask — would a smart reader who never attended this talk understand what this slide is saying from text alone? If not, add text. If they understand but find it boring, strengthen the visual.

### Color semantics (especially useful for contrast-driven talks)

- **Orange (#C75B39)**: old paradigm / problem side (e.g. ChatGPT, Before).
- **Teal (#0A6A74)**: new paradigm / solution side (e.g. Cursor, After).
- **Navy (#1C2526)**: body ink color.

---

## Step 3: Write `outline_visual.md`

This is the *source code* of the deck. Format for each slide:

```markdown
#### Slide N: Title

*   **Layout**: Layout description (e.g. left diagram + right text panel).
*   **Scene**:
    *   **Prompt**: [Detailed visual description including:
        - The bold header text
        - The specific content and style of the illustration area
        - The exact, readable text content of the text area (write it word-for-word)
        - Color, line weight, typography instructions]
*   **Asset**: imgs/some_logo.png  ← Optional, use when a logo or screenshot is needed.
```

### Prompt-writing principles

1. **Write text content into the prompt word-for-word.** Don't say "add some explanatory text" — write the actual text.
2. Make the illustration description specific ("a large circle with a notch in the lower-left, a human silhouette standing in the notch").
3. Text-area content must be complete (not placeholder, actual content).
4. When the layout has two panels, mark them explicitly in the prompt: `LEFT PANEL` / `RIGHT PANEL`.

### On negative phrasing

**Avoid negation in slide text** (e.g. "you're not a user", "it doesn't know"). Use positive phrasing that conveys the same meaning:

| Avoid | Use instead |
|------|-----------|
| "you're not a user of the tool" | "you end up serving as a component of the tool" |
| "it doesn't know your config" | "it goes in blind: config unknown" |
| "this isn't just faster" | "this is a categorical shift" |
| "not just coding" | "brainstorming, drafting, planning, everything" |

---

## Step 4: Prepare Assets (Optional)

If a slide needs a brand logo, screenshot, or QR code:

1. Drop the file into `imgs/`.
2. Add an asset line to the slide block in `outline_visual.md`: `*   **Asset**: imgs/filename.png`
3. The prompt will inject the image automatically at generation time.

**Common asset sources:**
- Company logos: download from the official site or uxwing.com (PNG).
- Screenshots: capture and save directly.
- QR codes: use the Python `qrcode` library or any online generator.

> ⚠️ AI cannot reliably generate brand logos (it hallucinates them). When a logo is needed, always provide the real file as an asset.

---

## Step 5: Generate 1K / 2K Versions (Fast Iteration)

The repo supports two backends — **Gemini** (default) for cheap, fast 1K renders, and **GPT-Image-2** for cleaner typography and direct higher-res rendering.

```bash
# Default: Gemini at 1K, 4 workers in parallel
python tools/generate_slides.py

# Generate specific slides only (use while iterating)
python tools/generate_slides.py --slides 3 5 8

# Use GPT-Image-2 backend at 2K with medium quality
python tools/generate_slides.py --model gpt --size 2K --quality medium
```

Output goes to `generated_slides/slide_NN_0.jpg` (or `.png` depending on backend).

### Backend choice: Gemini vs GPT-Image-2

- **Gemini** — cheaper per image, faster, more permissive with style descriptions. Best for early iteration and when style coherence across many slides is critical.
- **GPT-Image-2** — much stronger at rendering legible text within the image, including tables and labels. Best for final-quality decks where the text-on-slide is critical (which, given the Dual-Use principle above, is most of the time). Quality tiers: `low` / `medium` / `high`.

A common workflow: prototype with Gemini at 1K, then re-render the final deck with GPT-Image-2 at 2K medium.

> **Note**: when using the Gemini backend with `tools/generate_slides.py`, ensure `ThreadPoolExecutor(max_workers=8)` for slide-batch parallelism. With GPT-Image-2 the default is already 8.

---

## Step 6: Preview

```bash
python start-server.py            # localhost:8080
python start-server.py -p 8004    # custom port
python start-server.py --host 0.0.0.0 -p 8004   # expose to LAN
```

`index.html` uses Reveal.js to display the images. Press `S` to open the speaker-notes window.

---

## Step 7: Enlarge to 4K (Before Final Publish)

**Critical: test on a single slide first to confirm the enlargement works at 4K or higher, then run the full batch.**

```bash
# Step 1: test on one slide
python tools/generate_slides.py --enlarge --slides 1

# Verify the file size
file generated_slides/slide_01_0_4k.jpg
# Should report something like "3840 x 2160" or larger.

# Step 2: once confirmed, run the full enlargement
python tools/generate_slides.py --enlarge
```

⚠️ Enlargement re-invokes the Gemini API and is relatively expensive. Always validate on one slide before committing to a full pass.

> When using GPT-Image-2, you can skip enlargement entirely — it renders 2K / 4K directly. `--enlarge` is Gemini-only.

---

## Step 8: Update `index.html`

In `index.html`, each section's `data-background` path:

- 1K version: `generated_slides/slide_NN_0.jpg`
- 4K version: `generated_slides/slide_NN_0_4k.jpg`

Write speaker notes inside each section's `<aside class="notes">` block.

---

## Speaker Notes — Writing Principles

- Native-speaker English, conversational, written so it can be read out loud verbatim.
- ~120–150 words per slide.
- **Avoid negation** (same rule as slide text).
- First person — use "I." Have a voice and a point of view.
- Concrete details beat abstract summaries.

---

## Common Issues and Fixes

| Problem | Cause | Fix |
|------|------|------|
| AI-generated logos look garbled | Hallucination — logos are not stored as real pixels | Provide the real logo file in `imgs/` as an asset |
| Style drifts across slides | Per-slide prompts differ too much | Strengthen the "container" description in `visual_guideline.md`; regenerate |
| Text is unreadable / decorative | Generated font is too small or stylized | Add to the prompt: "all text must be fully legible printed sans-serif" |
| AI draws a mouse cursor when you wanted "Cursor" | Cursor (the company) vs cursor (the pointer) collision | Provide the Cursor company logo as an asset; specify "Cursor company logo" in the prompt |

---

## Project File Structure

```
nbp_slides/
├── outline_visual.md      # Source code (edit here)
├── visual_guideline.md    # Visual language definition
├── speak_notes.md         # Speaker notes (English, read aloud)
├── index.html             # Reveal.js player + speaker notes
├── imgs/                  # Assets (logos, screenshots)
├── generated_slides/      # Render outputs
│   ├── slide_01_0.jpg     # 1K / 2K version
│   └── slide_01_0_4k.jpg  # 4K version (Gemini only)
├── tools/
│   ├── generate_slides.py        # Dispatcher (Gemini or GPT-Image-2)
│   ├── gemini_generate_image.py  # Gemini API wrapper
│   ├── gemini_enlarge_image.py   # 4K upscaler (Gemini only)
│   └── openai_generate_image.py  # GPT-Image-2 API wrapper
├── tests/                 # Unit tests (parse, host arg, etc.)
├── .env                   # GEMINI_API_KEY=... or OPENAI_API_KEY=...
└── skill_slides.md        # This document
```
