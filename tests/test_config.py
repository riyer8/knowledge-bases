import os
import tempfile
from pathlib import Path

import pytest


def test_default_kb_root():
    # Ensure no override present
    os.environ.pop("KB_ROOT", None)
    # Re-import with fresh state
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    assert cfg_mod.config.kb_root == Path("~/.kb").expanduser()


def test_kb_root_env_override(tmp_path):
    os.environ["KB_ROOT"] = str(tmp_path)
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    assert cfg_mod.config.kb_root == tmp_path
    os.environ.pop("KB_ROOT")


def test_derived_paths(tmp_path):
    os.environ["KB_ROOT"] = str(tmp_path)
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    c = cfg_mod.config
    assert c.events_raw_dir == tmp_path / "events" / "raw"
    assert c.events_clean_dir == tmp_path / "events" / "clean"
    assert c.index_dir == tmp_path / "index"
    assert c.graph_dir == tmp_path / "graph"
    assert c.hashes_dir == tmp_path / "hashes"
    assert c.buckets_dir == tmp_path / "buckets"
    assert c.auth_dir == tmp_path / "auth"
    assert c.pages_dir == tmp_path / "pages"
    assert c.paused_log == tmp_path / "events" / "paused.log"
    assert c.hash_map_path == tmp_path / "hashes" / "map.json"
    assert c.hash_salt_path == tmp_path / "hashes" / "salt"
    os.environ.pop("KB_ROOT")


def test_model_defaults():
    os.environ.pop("KB_CHAT_MODEL", None)
    os.environ.pop("KB_EMBED_MODEL", None)
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    assert cfg_mod.config.chat_model == "qwen2.5:3b"
    assert cfg_mod.config.embed_model == "nomic-embed-text"


def test_model_env_overrides():
    os.environ["KB_CHAT_MODEL"] = "phi4-mini"
    os.environ["KB_EMBED_MODEL"] = "mxbai-embed-large"
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    assert cfg_mod.config.chat_model == "phi4-mini"
    assert cfg_mod.config.embed_model == "mxbai-embed-large"
    os.environ.pop("KB_CHAT_MODEL")
    os.environ.pop("KB_EMBED_MODEL")


def test_port_default():
    os.environ.pop("KB_PORT", None)
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    assert cfg_mod.config.backend_port == 8765


def test_port_env_override():
    os.environ["KB_PORT"] = "9000"
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    assert cfg_mod.config.backend_port == 9000
    os.environ.pop("KB_PORT")


def test_ensure_dirs_creates_paths(tmp_path):
    os.environ["KB_ROOT"] = str(tmp_path)
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    cfg_mod.config.ensure_dirs()
    assert (tmp_path / "events" / "raw").is_dir()
    assert (tmp_path / "events" / "clean").is_dir()
    assert (tmp_path / "index").is_dir()
    assert (tmp_path / "graph").is_dir()
    assert (tmp_path / "hashes").is_dir()
    assert (tmp_path / "buckets").is_dir()
    assert (tmp_path / "auth").is_dir()
    assert (tmp_path / "pages").is_dir()
    os.environ.pop("KB_ROOT")
