"""Unit tests for tools/generate_slides.py.

These tests exercise pure functions only — they do not call any
external image-generation API.
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

# Make the repo root importable so we can do ``from tools import ...``.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools import generate_slides  # noqa: E402


# ---------------------------------------------------------------------------
# parse_slides
# ---------------------------------------------------------------------------

SAMPLE_OUTLINE = textwrap.dedent("""
    # Sample Outline

    Intro prose that should be ignored.

    #### Slide 1: Title
    *   **Layout**: Centered title page.
    *   **Scene**:
        *   **Prompt**: A title slide on white background.

    #### Slide 2: Architecture
    *   **Layout**: Two panel.
    *   **Scene**:
        *   **Prompt**: A diagram with a single asset injected.
    *   **Asset**: imgs/architecture.png

    #### Slide 3: Multi-asset
    *   **Asset**:
        * imgs/a.png
        * imgs/b.png
""")


@pytest.fixture()
def outline_file(tmp_path: Path) -> Path:
    out = tmp_path / "outline_visual.md"
    out.write_text(SAMPLE_OUTLINE, encoding="utf-8")
    return out


def test_parse_slides_finds_all_slides(outline_file: Path):
    slides = generate_slides.parse_slides(str(outline_file))
    assert [s["number"] for s in slides] == [1, 2, 3]


def test_parse_slides_extracts_single_asset(outline_file: Path):
    slides = generate_slides.parse_slides(str(outline_file))
    slide_2 = next(s for s in slides if s["number"] == 2)
    assert slide_2["asset_paths"] == ["imgs/architecture.png"]


def test_parse_slides_extracts_multi_asset(outline_file: Path):
    slides = generate_slides.parse_slides(str(outline_file))
    slide_3 = next(s for s in slides if s["number"] == 3)
    assert slide_3["asset_paths"] == ["imgs/a.png", "imgs/b.png"]


def test_parse_slides_specific_slides_filter(outline_file: Path):
    slides = generate_slides.parse_slides(str(outline_file), specific_slides=[1, 3])
    assert [s["number"] for s in slides] == [1, 3]


def test_parse_slides_range_filter(outline_file: Path):
    slides = generate_slides.parse_slides(str(outline_file), start_slide=2, end_slide=2)
    assert [s["number"] for s in slides] == [2]


# ---------------------------------------------------------------------------
# build_prompt
# ---------------------------------------------------------------------------


def test_build_prompt_includes_guideline_and_content(tmp_path: Path):
    slide = {
        "number": 1,
        "content": "#### Slide 1: Title\nSome content here.",
        "asset_paths": [],
    }
    guideline = "Test visual guideline body."

    prompt, image_inputs = generate_slides.build_prompt(slide, guideline, tmp_path)

    assert guideline in prompt
    assert "Some content here." in prompt
    assert image_inputs == []


def test_build_prompt_resolves_existing_asset(tmp_path: Path):
    asset = tmp_path / "imgs" / "foo.png"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"\x89PNG\r\n")

    slide = {
        "number": 1,
        "content": "#### Slide 1: X",
        "asset_paths": ["imgs/foo.png"],
    }

    prompt, image_inputs = generate_slides.build_prompt(slide, "guideline", tmp_path)

    assert image_inputs == [str(asset)]
    assert "REFERENCE ASSET" in prompt


def test_build_prompt_skips_missing_asset(tmp_path: Path, capsys):
    slide = {
        "number": 1,
        "content": "#### Slide 1: X",
        "asset_paths": ["imgs/does_not_exist.png"],
    }

    prompt, image_inputs = generate_slides.build_prompt(slide, "guideline", tmp_path)

    assert image_inputs == []
    captured = capsys.readouterr()
    assert "WARNING" in captured.out


# ---------------------------------------------------------------------------
# CLI argument parsing & defaults
# ---------------------------------------------------------------------------


def test_build_parser_defaults():
    parser = generate_slides.build_parser()
    args = parser.parse_args([])
    assert args.model == "gemini"
    assert args.size is None
    assert args.quality is None
    assert args.enlarge is False
    assert args.slides is None


def test_build_parser_gpt_2k_medium():
    parser = generate_slides.build_parser()
    args = parser.parse_args(["--model", "gpt", "--size", "2K", "--quality", "medium"])
    assert args.model == "gpt"
    assert args.size == "2K"
    assert args.quality == "medium"


def test_resolve_defaults_gemini():
    parser = generate_slides.build_parser()
    args = parser.parse_args(["--model", "gemini"])
    model, size, quality, workers = generate_slides._resolve_defaults(args)
    assert model == "gemini"
    assert size == "1K"  # DEFAULT_SIZES["gemini"]
    assert workers == 4  # DEFAULT_PARALLELISM["gemini"]
    assert quality == "low"  # DEFAULT_QUALITY


def test_resolve_defaults_gpt():
    parser = generate_slides.build_parser()
    args = parser.parse_args(["--model", "gpt"])
    model, size, quality, workers = generate_slides._resolve_defaults(args)
    assert model == "gpt"
    assert size == "4K"  # DEFAULT_SIZES["gpt"]
    assert workers == 8  # DEFAULT_PARALLELISM["gpt"]


def test_resolve_defaults_explicit_overrides_default():
    parser = generate_slides.build_parser()
    args = parser.parse_args([
        "--model", "gemini",
        "--size", "4K",
        "--parallelism", "2",
    ])
    model, size, _, workers = generate_slides._resolve_defaults(args)
    assert size == "4K"
    assert workers == 2


def test_build_parser_invalid_model_rejected():
    parser = generate_slides.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--model", "openai"])  # not in choices


def test_build_parser_invalid_quality_rejected():
    parser = generate_slides.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--quality", "ultra"])  # not in choices
