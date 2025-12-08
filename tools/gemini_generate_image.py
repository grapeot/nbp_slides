#!/usr/bin/env python3
"""
Command-line tool for generating images using Gemini 3 Pro Image Preview.
Supports text-only generation or text + image input.
"""

from typing import Optional, List
from pathlib import Path
import argparse
import mimetypes
import os
import sys

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables from .env file (in project root)
script_dir = Path(__file__).parent
project_root = script_dir.parent
env_path = project_root / ".env"
load_dotenv(env_path)


def save_binary_file(file_name: str, data: bytes) -> None:
    """Save binary data to disk."""
    with open(file_name, "wb") as f:
        f.write(data)
    print(f"File saved to: {file_name}")


def generate(
    prompt: str,
    image_paths: Optional[List[str]] = None,
    output_prefix: str = "output",
    image_size: str = "1K", # kept in signature for compatibility but ignored
    aspect_ratio: Optional[str] = None,
) -> None:
    """Send text (and optionally images) to Gemini 3 Pro Image Preview and stream responses."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # Build content parts
    parts = [types.Part.from_text(text=prompt)]
    
    if image_paths:
        for image_path in image_paths:
            if not Path(image_path).exists():
                print(f"Error: Image file not found: {image_path}", file=sys.stderr)
                sys.exit(1)
            
            image_bytes = Path(image_path).expanduser().read_bytes()
            mime_type, _ = mimetypes.guess_type(image_path)
            if not mime_type:
                mime_type = "image/png"
            
            parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))

    contents = [
        types.Content(
            role="user",
            parts=parts,
        )
    ]

    image_config_dict = {}
    if aspect_ratio:
        image_config_dict["aspect_ratio"] = aspect_ratio
    
    # Enable image_size again as SDK updated
    if image_size:
        image_config_dict["image_size"] = image_size

    generate_content_config = types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(**image_config_dict),
    )

    file_index = 0
    for chunk in client.models.generate_content_stream(
        model="gemini-3-pro-image-preview",
        contents=contents,
        config=generate_content_config,
    ):
        if not chunk.candidates or not chunk.candidates[0].content:
            continue

        for part in chunk.candidates[0].content.parts:
            if getattr(part, "text", None):
                print(part.text, end="", flush=True)
            elif getattr(part, "inline_data", None) and part.inline_data.data:
                inline_data = part.inline_data
                file_extension = mimetypes.guess_extension(inline_data.mime_type) or ".png"
                file_name = f"{output_prefix}_{file_index}{file_extension}"
                file_index += 1
                save_binary_file(file_name, inline_data.data)


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using Gemini 3 Pro Image Preview",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Text-only generation
  python gemini_generate_image.py --prompt "A minimalist tech presentation slide"

  # Text + image input
  python gemini_generate_image.py --prompt "Enhance this image" --input input.png

  # Custom output prefix and image size
  python gemini_generate_image.py --prompt "Generate slide" --output slide6 --size 2K
  
  # With aspect ratio
  python gemini_generate_image.py --prompt "Generate slide" --aspect-ratio 16:9 --size 2K
        """
    )
    
    parser.add_argument(
        "--prompt", "-p",
        required=True,
        help="Text prompt for image generation"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        default=None,
        action="append", # Allow multiple inputs
        help="Optional input image file path (can be used multiple times)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="output",
        help="Output file prefix (default: output)"
    )
    
    parser.add_argument(
        "--size", "-s",
        type=str,
        default="1K",
        choices=["1K", "2K", "4K"],
        help="Image size: 1K, 2K or 4K (default: 1K)"
    )
    
    parser.add_argument(
        "--aspect-ratio", "-a",
        type=str,
        default=None,
        choices=["1:1", "4:3", "16:9", "9:16", "3:4"],
        help="Aspect ratio: 1:1, 4:3, 16:9, 9:16, or 3:4 (default: auto/not set)"
    )
    
    args = parser.parse_args()
    
    generate(
        prompt=args.prompt,
        image_paths=args.input,
        output_prefix=args.output,
        image_size=args.size,
        aspect_ratio=args.aspect_ratio,
    )


if __name__ == "__main__":
    main()
