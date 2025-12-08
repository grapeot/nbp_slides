# The Generative Kernel

A next-generation presentation system where "Context is King." This project implements the **Generative Kernel** philosophy: instead of manually assembling slides, we inject raw assets and prompts into a generative model to render the final presentation layer.

## Philosophy

*   **Beyond DRY**: Don't just repeat yourself; generate yourself.
*   **Asset Injection**: The core technique. We take raw functional assets (QR codes, logos, diagrams) and "inject" them into the generative process. The model renders the lighting, texture, and environment *around* the asset, creating a seamless organic integration.
*   **The Glass Garden**: Our visual language. Translucent interfaces, matte ceramic accents, and soft, diffused lighting.

## Workflow

The system is designed for an AI-assisted loop:

### 1. Define the Context
Edit `outline_visual.md`. This is the source of truth.
*   **Structure**: Markdown headers define slides.
*   **Prompts**: Self-contained visual descriptions for each slide.
*   **Assets**: Paths to local images (e.g., `imgs/qrcode.png`) to be injected.

### 2. Generate (Draft Mode)
Run the generator to create 1K previews. This is fast and cheap for iteration.
```bash
python tools/generate_slides.py
```
This parses the outline, calls the Gemini 3 Pro Image Preview API, and saves images to `generated_slides/`.

### 3. Refine & Upscale (Production Mode)
Once specific slides are approved, upscale them to 4K resolution using the generative upscaler.
```bash
# Upscale everything
python tools/generate_slides.py --enlarge

# Upscale specific slides
python tools/generate_slides.py --enlarge --slides 8 11
```

### 4. Present
Open `index.html`.
The presentation uses **Reveal.js** to display the generated "Mega-Images" as full-screen backgrounds. It is simple, robust, and visually stunning.

## Setup

1.  **Environment**:
    ```bash
    uv venv  # using uv is recommended
    source .venv/bin/activate
    pip install -r requirements.txt
    ```
2.  **Credentials**:
    Create a `.env` file with your API key:
    ```
    GOOGLE_API_KEY=your_key_here
    ```

## Project Structure

*   `outline_visual.md`: The "Source Code" of the presentation.
*   `visual_guideline.md`: The "Visual Language" definition (The Glass Garden).
*   `speak_notes.md`: The script for the presentation.
*   `tools/`: Python scripts for generation and upscaling.
    *   `generate_slides.py`: Main orchestrator.
    *   `gemini_generate_image.py`: API wrapper for generation.
    *   `gemini_enlarge_image.py`: API wrapper for upscaling.
*   `generated_slides/`: The render targets.
*   `index.html`: The viewer.