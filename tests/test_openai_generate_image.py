"""Unit tests for tools/openai_generate_image.py.

Pure-function tests only — no API calls are made.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools import openai_generate_image  # noqa: E402


def test_map_size_16_9_2k():
    assert openai_generate_image._map_size("2K", "16:9") == "2560x1440"


def test_map_size_16_9_4k():
    assert openai_generate_image._map_size("4K", "16:9") == "3840x2160"


def test_map_size_1k_default_square():
    # Default aspect_ratio=None falls back to "1:1".
    assert openai_generate_image._map_size("1K", None) == "1024x1024"


def test_map_size_unknown_combination_raises():
    with pytest.raises(ValueError):
        openai_generate_image._map_size("8K", "16:9")  # not in SIZE_MAP


def test_build_output_path_appends_index(tmp_path: Path):
    prefix = tmp_path / "slide_03"
    result = openai_generate_image._build_output_path(str(prefix), 0)
    assert result.name == "slide_03_0.jpg"
    assert result.parent == tmp_path


def test_build_output_path_respects_custom_ext(tmp_path: Path):
    prefix = tmp_path / "slide_03"
    result = openai_generate_image._build_output_path(str(prefix), 1, ext=".png")
    assert result.name == "slide_03_1.png"
