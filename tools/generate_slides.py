import argparse
import sys
import os
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

if __package__:
    from . import gemini_generate_image
    from . import openai_generate_image
else:
    from tools import gemini_generate_image  # type: ignore
    from tools import openai_generate_image  # type: ignore


# Model-aware defaults
DEFAULT_SIZES = {"gemini": "1K", "gpt": "4K"}
DEFAULT_QUALITY = "low"  # only used by gpt-image-2
DEFAULT_PARALLELISM = {"gemini": 4, "gpt": 8}


def parse_slides(outline_path, start_slide=1, end_slide=19, specific_slides=None):
    with open(outline_path, 'r') as f:
        content = f.read()

    slides = []
    slide_pattern = re.compile(r'#### Slide (\d+):(.*?)(?=#### Slide \d+:|$)', re.DOTALL)

    matches = slide_pattern.finditer(content)
    for match in matches:
        slide_num = int(match.group(1))

        if specific_slides and slide_num not in specific_slides:
            continue
        if not specific_slides and not (start_slide <= slide_num <= end_slide):
            continue

        slide_content = match.group(0).strip()

        asset_paths = []
        asset_header_match = re.search(r'\*\s+\*\*Asset\*\*?\s*:?', slide_content)

        if asset_header_match:
            rest_of_section = slide_content[asset_header_match.end():]
            lines = rest_of_section.split('\n')

            current_line = lines[0].strip()
            if current_line and current_line.lower() != "none":
                asset_paths.append(current_line)

            for line in lines[1:]:
                stripped = line.strip()
                if not stripped:
                    continue
                if re.match(r'^\*\s+\*\*', stripped) and not stripped.startswith('* **Asset'):
                    break
                if stripped.startswith('* ') or stripped.startswith('- '):
                    val = stripped[2:].strip()
                    if val.lower() != "none":
                        asset_paths.append(val)

        # Strip the `#### Slide N: TITLE` header line before passing content to
        # the image model. The slide number is a meta-label used to index the
        # outline file — image models occasionally render it as decorative
        # text on the slide ("Slide 12" baked into the image). Removing the
        # header eliminates that leak path without losing any prompt content.
        content_for_prompt = re.sub(
            r'^#### Slide \d+:[^\n]*\n?', '', slide_content, count=1
        ).lstrip()

        slides.append({
            'number': slide_num,
            'content': content_for_prompt,
            'asset_paths': asset_paths,
        })
    return slides


def build_prompt(slide, guideline, project_root):
    """Compose the per-slide prompt (and resolved asset paths) used by either backend."""
    prompt = f"""
    You are an expert presentation designer for a high-end tech keynote.

    VISUAL GUIDELINES (MUST FOLLOW):
    {guideline}

    SLIDE CONTENT:
    {slide['content']}

    TASK:
    Generate a high-resolution, 16:9 slide image that represents the content above while strictly adhering to the visual guidelines.
    The image should be the final slide itself, including any text or graphical elements described.
    Make it look like a professional slide from a Keynote presentation.

    CRITICAL INSTRUCTION FOR ASSETS:
    If reference images are provided, use their exact charts, tables, labels, and data values as the primary visual source.
    Place and restyle the provided asset inside the slide design, but preserve the numbers, ordering, labels, and visual structure.
    The model should not invent replacement data or redraw approximate versions from memory.
    """

    image_inputs = []
    for path_str in slide.get('asset_paths', []) or []:
        asset_path = Path(path_str) if os.path.isabs(path_str) else project_root / path_str
        if asset_path.exists():
            prompt += (
                f"\n    REFERENCE ASSET TO USE: See attached image {asset_path.name}. "
                "This contains exact data visualization that must be preserved."
            )
            image_inputs.append(str(asset_path))
        else:
            print(f"  WARNING: Asset file not found at {asset_path}. Skipping this asset.")

    return prompt, image_inputs


def generate_slide(slide, guideline, output_dir, project_root, *,
                   model: str, image_size: str, quality: str,
                   filename_suffix: str = ""):
    print(f"Starting generation for Slide {slide['number']} (model={model}, size={image_size}, quality={quality})...")

    prompt, image_inputs = build_prompt(slide, guideline, project_root)
    for asset in image_inputs:
        print(f"  Using asset: {asset}")

    base_name = f"slide_{slide['number']:02d}{filename_suffix}"
    output_filename = os.path.join(str(output_dir), base_name)

    try:
        if model == "gemini":
            gemini_generate_image.generate(
                prompt=prompt,
                image_paths=image_inputs if image_inputs else None,
                output_prefix=output_filename,
                image_size=image_size,
                aspect_ratio="16:9",
            )
        elif model == "gpt":
            openai_generate_image.generate(
                prompt=prompt,
                image_paths=image_inputs if image_inputs else None,
                output_prefix=output_filename,
                image_size=image_size,
                aspect_ratio="16:9",
                quality=quality,
            )
        else:
            raise ValueError(f"Unknown model: {model}")
        print(f"Finished Slide {slide['number']}")
    except Exception as e:
        print(f"Error generating Slide {slide['number']}: {e}")


def _resolve_defaults(args):
    """Return (model, size, quality, max_workers) honoring the model-aware defaults."""
    model = args.model
    size = args.size if args.size else DEFAULT_SIZES[model]
    quality = args.quality if args.quality else DEFAULT_QUALITY
    max_workers = args.parallelism if args.parallelism else DEFAULT_PARALLELISM[model]
    return model, size, quality, max_workers


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate slides")
    parser.add_argument("--enlarge", action="store_true",
                        help="Enlarge existing slides to 4K (Gemini only — gpt-image-2 "
                             "already renders 4K natively)")
    parser.add_argument("--slides", type=int, nargs="+",
                        help="Specific slide numbers to process (e.g., --slides 8 11)")
    parser.add_argument("--model", choices=["gemini", "gpt"], default="gpt",
                        help="Backend model (default: gpt). Gemini path remains "
                             "fully supported; pass --model gemini to use it.")
    parser.add_argument("--size", choices=["1K", "2K", "4K"],
                        help="Image size (default: 4K for gpt, 1K for gemini)")
    parser.add_argument("--quality", choices=["low", "medium", "high"],
                        help="Quality tier for gpt-image-2 only (default: low). "
                             "Ignored for gemini.")
    parser.add_argument("--filename-suffix", default="",
                        help='Suffix appended after slide_NN, before _<index>.jpg '
                             '(e.g. "_gpt_low" → slide_03_gpt_low_0.jpg)')
    parser.add_argument("--parallelism", type=int,
                        help="Max concurrent workers (default: 4 for gemini, 8 for gpt)")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    outline_path = project_root / "outline_visual.md"
    guideline_path = project_root / "visual_guideline.md"
    output_dir = project_root / "generated_slides"

    os.makedirs(output_dir, exist_ok=True)

    if args.enlarge:
        if args.model != "gemini":
            print(
                "--enlarge is only supported with --model gemini; "
                "gpt-image-2 generates the final resolution directly, no upscale needed.",
                file=sys.stderr,
            )
            sys.exit(2)
        import glob
        import subprocess

        print("Starting batch enlargement...")
        slide_patterns = [
            str(output_dir / "slide_*_0.png"),
            str(output_dir / "slide_*_0.jpg"),
            str(output_dir / "slide_*_0.jpeg"),
        ]
        files = []
        seen = set()
        for slide_pattern in slide_patterns:
            for file_path in glob.glob(slide_pattern):
                slide_key = re.sub(r"\.(png|jpe?g)$", "", file_path, flags=re.IGNORECASE)
                if slide_key in seen:
                    continue
                seen.add(slide_key)
                files.append(file_path)

        if args.slides:
            filtered = []
            for f in files:
                match = re.search(r'slide_(\d+)_0\.(png|jpe?g)$', f, re.IGNORECASE)
                if match and int(match.group(1)) in args.slides:
                    filtered.append(f)
            files = filtered

        print(f"Found {len(files)} slides to enlarge.")

        enlarge_script = script_dir / "gemini_enlarge_image.py"

        def enlarge_one(file_path):
            file_path_obj = Path(file_path)
            output_name = file_path_obj.stem + "_4k" + file_path_obj.suffix
            output_path = output_dir / output_name
            print(f"Enlarging {file_path_obj.name} -> {output_name}...")
            cmd = [sys.executable, str(enlarge_script), "--input", str(file_path), "--output", str(output_path)]
            try:
                subprocess.run(cmd, check=True)
                print(f"Finished {output_name}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to enlarge {file_path_obj.name}: {e}")

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(enlarge_one, f) for f in sorted(files)]
            for fut in futures:
                fut.result()

        print("Batch enlargement complete.")
        return

    with open(guideline_path, 'r') as f:
        guideline = f.read()

    model, size, quality, max_workers = _resolve_defaults(args)

    specific_slides = args.slides if args.slides else None
    if not specific_slides:
        slides = parse_slides(str(outline_path), 1, 19)
    else:
        slides = parse_slides(str(outline_path), specific_slides=specific_slides)

    print(f"Found {len(slides)} slides to generate. "
          f"(model={model}, size={size}, quality={quality}, parallelism={max_workers})")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                generate_slide, slide, guideline, output_dir, project_root,
                model=model, image_size=size, quality=quality,
                filename_suffix=args.filename_suffix,
            )
            for slide in slides
        ]
        for fut in futures:
            fut.result()


if __name__ == "__main__":
    main()
