#!/usr/bin/env python3
"""
Command-line tool for upscaling images to 4K using Gemini 3 Pro Image Preview.
Takes a 1K image and regenerates it at 4K resolution while preserving content.
"""

import sys
import os
import argparse
import mimetypes
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
script_dir = Path(__file__).parent
project_root = script_dir.parent
env_path = project_root / ".env"
load_dotenv(env_path)

def save_binary_file(file_name: str, data: bytes) -> None:
    """Save binary data to disk."""
    with open(file_name, "wb") as f:
        f.write(data)
    print(f"File saved to: {file_name}")

def enlarge(
    image_path: str,
    output_path: str,
) -> None:
    """Upscale the given image to 4K."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    if not Path(image_path).exists():
        print(f"Error: Input image not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # Read input image
    image_bytes = Path(image_path).expanduser().read_bytes()
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/jpeg"

    # Construct Prompt
    # "Upscale this image to 4K resolution..."
    prompt = "Upscale this image to 4K resolution. Maintain all details, text, and structure exactly. Do not add or remove elements. Just increase the resolution and sharpness."

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            ],
        )
    ]

    # Configuration for 4K output based on updated SDK support
    generate_content_config = types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(
            aspect_ratio="16:9",
            image_size="4K"
        ),
    )

    print(f"Upscaling {image_path} to 4K...")
    
    try:
        # We only expect one image back
        response_stream = client.models.generate_content_stream(
            model="gemini-3-pro-image-preview",
            contents=contents,
            config=generate_content_config,
        )

        for chunk in response_stream:
            if not chunk.candidates or not chunk.candidates[0].content:
                continue

            for part in chunk.candidates[0].content.parts:
                if getattr(part, "inline_data", None) and part.inline_data.data:
                    inline_data = part.inline_data
                    save_binary_file(output_path, inline_data.data)
                    return # Done after saving first image

    except Exception as e:
        print(f"Error during upscaling: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Upscale image to 4K")
    parser.add_argument("--input", "-i", required=True, help="Input image path")
    parser.add_argument("--output", "-o", required=True, help="Output image path")
    
    args = parser.parse_args()
    
    enlarge(args.input, args.output)

if __name__ == "__main__":
    main()
