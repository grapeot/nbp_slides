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

from concurrent.futures import ThreadPoolExecutor

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
    api_key: str = None
) -> None:
    """Upscale the given image to 4K."""
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set", file=sys.stderr)
        return

    if not Path(image_path).exists():
        print(f"Error: Input image not found: {image_path}", file=sys.stderr)
        return

    client = genai.Client(api_key=api_key)
    model = "gemini-3-pro-image-preview"

    # Read input image
    image_bytes = Path(image_path).expanduser().read_bytes()
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/jpeg"

    # Construct Prompt
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

    tools = [
        types.Tool(googleSearch=types.GoogleSearch()),
    ]
    
    # Configuration for output based on user recommendation for 4K
    generate_content_config = types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(
            aspect_ratio="16:9",
            image_size="4K"
        ),
        tools=tools,
    )

    print(f"Upscaling {image_path} to 4K...")
    
    try:
        # Using the generator loop as recommended for reliability
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if not chunk.candidates or not chunk.candidates[0].content:
                continue

            for part in chunk.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    save_binary_file(output_path, part.inline_data.data)
                    return # Done after saving first image

    except Exception as e:
        print(f"Error upscaling {image_path}: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Upscale image(s) to 4K")
    parser.add_argument("--input", "-i", action="append", help="Input image path (can be used multiple times)")
    parser.add_argument("--output", "-o", action="append", help="Output image path (can be used multiple times)")
    parser.add_argument("--workers", "-w", type=int, default=5, help="Number of parallel workers (default: 5)")
    
    args = parser.parse_args()
    
    if not args.input or not args.output:
        print("Error: Both --input and --output are required.")
        sys.exit(1)
        
    if len(args.input) != len(args.output):
        print("Error: Number of inputs must match number of outputs.")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        for inp, outp in zip(args.input, args.output):
            executor.submit(enlarge, inp, outp, api_key)

if __name__ == "__main__":
    main()
