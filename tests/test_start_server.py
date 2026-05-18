"""Tests for the start-server CLI.

The script is named ``start-server.py`` (hyphen), which is not directly
importable. We load it via importlib.util so we can call its ``build_parser``
helper without spinning up a real server.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_server_module():
    spec = importlib.util.spec_from_file_location(
        "start_server", REPO_ROOT / "start-server.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def server_module():
    return _load_server_module()


def test_default_args(server_module):
    args = server_module.build_parser().parse_args([])
    assert args.port == 8080
    assert args.host == "localhost"
    assert args.no_browser is False


def test_custom_port(server_module):
    args = server_module.build_parser().parse_args(["-p", "8004"])
    assert args.port == 8004


def test_host_all_interfaces(server_module):
    args = server_module.build_parser().parse_args(["--host", "0.0.0.0"])
    assert args.host == "0.0.0.0"


def test_no_browser_flag(server_module):
    args = server_module.build_parser().parse_args(["--no-browser"])
    assert args.no_browser is True


def test_combined_flags(server_module):
    args = server_module.build_parser().parse_args([
        "--host", "0.0.0.0",
        "-p", "9000",
        "--no-browser",
    ])
    assert args.host == "0.0.0.0"
    assert args.port == 9000
    assert args.no_browser is True
