#!/usr/bin/env python3
"""Local wrapper around OpenAI gpt-image-2 with the same signature shape
as `gemini_generate_image.generate`, so `generate_slides.py` can dispatch
to either backend by name.

Quality tiers (gpt-image-2 only): low / medium / high. Defaults to "low"
in the slide-generation flow to keep batches cheap; raise to medium/high
for final-quality renders.

Sizes (1K / 2K / 4K) map to concrete pixel dimensions identical to the
workspace-level `tools/generate_image.py` mapping. Only 16:9 is needed
for slides, but we keep the full mapping table for symmetry.
"""
from __future__ import annotations

import base64
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

script_dir = Path(__file__).parent
project_root = script_dir.parent
load_dotenv(project_root / ".env")


SIZE_MAP = {
    ("1K", "1:1"): "1024x1024",
    ("1K", "16:9"): "1536x864",
    ("1K", "9:16"): "864x1536",
    ("1K", "4:3"): "1152x896",
    ("1K", "3:4"): "896x1152",
    ("2K", "1:1"): "2048x2048",
    ("2K", "16:9"): "2560x1440",
    ("2K", "9:16"): "1440x2560",
    ("4K", "1:1"): "3072x3072",
    ("4K", "16:9"): "3840x2160",
    ("4K", "9:16"): "2160x3840",
}


def _map_size(image_size: str, aspect_ratio: Optional[str]) -> str:
    aspect = aspect_ratio or "1:1"
    key = (image_size, aspect)
    if key not in SIZE_MAP:
        raise ValueError(
            f"Unsupported size mapping for image_size={image_size}, aspect_ratio={aspect}"
        )
    return SIZE_MAP[key]


def _save_b64_image(b64: str, out_path: Path) -> bool:
    try:
        raw = base64.b64decode(b64)
    except (TypeError, ValueError) as exc:
        print(f"Error decoding OpenAI image payload: {exc}", file=sys.stderr)
        return False

    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Persist as PNG first, then convert to JPG for parity with Gemini wrapper.
    png_path = out_path.with_suffix(".png")
    png_path.write_bytes(raw)
    try:
        from PIL import Image  # imported lazily to keep startup fast

        Image.open(png_path).convert("RGB").save(out_path, quality=92)
    finally:
        if png_path.exists():
            try:
                png_path.unlink()
            except OSError:
                pass
    print(f"File saved to: {out_path}")
    return True


def _build_output_path(output_prefix: str, index: int, ext: str = ".jpg") -> Path:
    prefix = Path(output_prefix)
    return prefix.with_name(f"{prefix.name}_{index}{ext}")


def generate(
    prompt: str,
    image_paths: Optional[list[str]] = None,
    output_prefix: str = "output",
    image_size: str = "4K",
    aspect_ratio: Optional[str] = None,
    quality: str = "low",
) -> Optional[Path]:
    """Generate one image via gpt-image-2. Defaults to 4K low for cheap
    batch slide rendering. Returns the first saved path or None."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    size = _map_size(image_size, aspect_ratio)
    print(
        f"OpenAI gpt-image-2 | Size: {size} | Quality: {quality}",
        file=sys.stderr,
    )

    client = OpenAI(api_key=api_key)
    if image_paths:
        if len(image_paths) != 1:
            print(
                "Error: gpt-image-2 currently supports at most one input image.",
                file=sys.stderr,
            )
            sys.exit(1)
        with open(image_paths[0], "rb") as image_file:
            result = client.images.edit(
                model="gpt-image-2",
                image=image_file,
                prompt=prompt,
                quality=quality,
                output_format="png",
                extra_body={"size": size},
            )
    else:
        result = client.images.generate(
            model="gpt-image-2",
            prompt=prompt,
            quality=quality,
            output_format="png",
            extra_body={"size": size},
        )

    first_saved: Optional[Path] = None
    for index, item in enumerate(result.data or []):
        if not item.b64_json:
            continue
        out_path = _build_output_path(output_prefix, index)
        if _save_b64_image(item.b64_json, out_path) and first_saved is None:
            first_saved = out_path

    return first_saved
