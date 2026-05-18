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


def test_parse_slides_strips_slide_header_from_content(outline_file: Path):
    """The `#### Slide N: TITLE` header is a meta-label used to index the
    outline. It must NOT appear in the content payload sent to the image
    model — otherwise the model can render the literal text "Slide N" onto
    the generated slide. Asset extraction still runs against the original
    block, so dropping the header line is safe."""
    slides = generate_slides.parse_slides(str(outline_file))
    for s in slides:
        assert not s["content"].lstrip().startswith("#### Slide")
        # The number itself remains accessible via the dict key.
        assert isinstance(s["number"], int)


def test_parse_slides_preserves_body_after_strip(outline_file: Path):
    """Stripping the header should remove ONLY the header line — every other
    line of the slide block must survive untouched."""
    slides = generate_slides.parse_slides(str(outline_file))
    slide_2 = next(s for s in slides if s["number"] == 2)
    assert "**Layout**: Two panel." in slide_2["content"]
    assert "A diagram with a single asset injected." in slide_2["content"]


# ---------------------------------------------------------------------------
# build_prompt
# ---------------------------------------------------------------------------


def test_build_prompt_includes_guideline_and_content(tmp_path: Path):
    # The Slide N header is already stripped by parse_slides before reaching
    # build_prompt — fixture content reflects that contract.
    slide = {
        "number": 1,
        "content": "Some content here.",
        "asset_paths": [],
    }
    guideline = "Test visual guideline body."

    prompt, image_inputs = generate_slides.build_prompt(slide, guideline, tmp_path)

    assert guideline in prompt
    assert "Some content here." in prompt
    assert image_inputs == []


def test_build_prompt_does_not_inject_slide_number(tmp_path: Path):
    """Defense in depth: even if some caller forgets to strip the header, the
    prompt body itself should not introduce a `Slide N` label."""
    slide = {
        "number": 7,
        "content": "Body content without any slide-number reference.",
        "asset_paths": [],
    }
    prompt, _ = generate_slides.build_prompt(slide, "guideline", tmp_path)
    assert "Slide 7" not in prompt
    assert "Slide N" not in prompt


def test_build_prompt_resolves_existing_asset(tmp_path: Path):
    asset = tmp_path / "imgs" / "foo.png"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"\x89PNG\r\n")

    slide = {
        "number": 1,
        "content": "Some slide body referencing an asset.",
        "asset_paths": ["imgs/foo.png"],
    }

    prompt, image_inputs = generate_slides.build_prompt(slide, "guideline", tmp_path)

    assert image_inputs == [str(asset)]
    assert "REFERENCE ASSET" in prompt


def test_build_prompt_skips_missing_asset(tmp_path: Path, capsys):
    slide = {
        "number": 1,
        "content": "Some slide body.",
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
    # Default backend is gpt-image-2 — it renders 2K/4K natively and produces
    # cleaner typography than Gemini for slide-style content. Gemini remains
    # fully supported via `--model gemini`.
    assert args.model == "gpt"
    assert args.size is None
    assert args.quality is None
    assert args.enlarge is False
    assert args.slides is None


def test_build_parser_explicit_gemini():
    parser = generate_slides.build_parser()
    args = parser.parse_args(["--model", "gemini"])
    assert args.model == "gemini"


def test_resolve_defaults_no_args_yields_gpt_4k():
    """When the user passes no model/size/quality, the resolved defaults
    should be the gpt-image-2 4K low-quality batch profile."""
    parser = generate_slides.build_parser()
    args = parser.parse_args([])
    model, size, quality, workers = generate_slides._resolve_defaults(args)
    assert model == "gpt"
    assert size == "4K"
    assert quality == "low"
    assert workers == 8


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
