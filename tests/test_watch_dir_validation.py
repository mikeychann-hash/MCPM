"""Unit tests for watch directory validation and preparation."""

import os
import platform

import pytest

from mcp_backend import FGDMCPServer


def _make_server(config):
    server = object.__new__(FGDMCPServer)
    server.config = config
    return server


def test_validate_paths_requires_watch_dir():
    server = _make_server({})
    with pytest.raises(ValueError, match="watch_dir is not configured"):
        server._validate_paths()


def test_validate_paths_rejects_windows_path_on_non_windows():
    server = _make_server({"watch_dir": "C:/Temp"})
    if platform.system() == "Windows":
        pytest.skip("Windows-specific path is valid on Windows")
    with pytest.raises(ValueError, match="Windows-specific path"):
        server._validate_paths()


def test_validate_paths_rejects_file_path(tmp_path):
    file_path = tmp_path / "not_a_dir"
    file_path.write_text("content")
    server = _make_server({"watch_dir": str(file_path)})
    with pytest.raises(ValueError, match="not a directory"):
        server._validate_paths()


def test_prepare_watch_dir_creates_missing_directory(tmp_path):
    target = tmp_path / "new_dir"
    server = _make_server({"watch_dir": str(target)})
    resolved = server._prepare_watch_dir(target)
    assert resolved == target
    assert target.exists() and target.is_dir()


def test_prepare_watch_dir_requires_permissions(tmp_path, monkeypatch):
    target = tmp_path / "dir"
    target.mkdir()
    server = _make_server({"watch_dir": str(target)})
    monkeypatch.setattr(os, "access", lambda path, mode: False)
    with pytest.raises(ValueError, match="readable and writable"):
        server._prepare_watch_dir(target)
