import tomllib

from ototype import config


def test_template_parses_to_defaults():
    raw = tomllib.loads(config.render(config.Config()))
    cfg = config.parse(raw)
    assert cfg.errors == []
    assert cfg == config.Config()


def test_load_creates_file(tmp_path):
    path = tmp_path / "sub" / "config.toml"
    cfg = config.load(path)
    assert path.exists()
    assert cfg.errors == []


def test_invalid_items_fall_back_individually():
    cfg = config.parse({
        "insert_method": "typing",
        "silence_timeout_sec": True,  # bool は int として受け付けない
        "sound": False,
        "hotkey": "ctrl+hyper+x",
        "unknown_key": 1,
    })
    assert cfg.insert_method == "clipboard"
    assert cfg.silence_timeout_sec == 60
    assert cfg.sound is False  # 正しい項目は反映される
    assert cfg.hotkey == config.default_hotkey()
    assert len(cfg.errors) == 4
    assert any("insert_method" in e and "clipboard, live" in e for e in cfg.errors)


def test_syntax_error_uses_defaults(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("hotkey = \n", encoding="utf-8")
    cfg = config.load(path)
    assert cfg.hotkey == config.default_hotkey()
    assert "書式に誤り" in cfg.errors[0]


def test_replace_table():
    cfg = config.parse({"replace": {"でぃすこーど": "Discord", "x": 1}})
    assert cfg.replace == {"でぃすこーど": "Discord"}
    assert len(cfg.errors) == 1


def test_migrate_old_settings(tmp_path, monkeypatch):
    from ototype import migrate

    new_dir = tmp_path / "ototype"
    old_dir = tmp_path / "moonshine-dictate"
    old_dir.mkdir()
    (old_dir / "config.toml").write_text('hotkey = "f9"\n', encoding="utf-8")
    monkeypatch.setattr(migrate, "config_dir", lambda: new_dir)
    monkeypatch.setattr(migrate, "_remove_old_autostart", lambda: None)
    assert migrate.migrate_old_settings() is True
    assert config.load(new_dir / "config.toml").hotkey == "f9"
    # 2回目は、新しい設定があるので何もしない
    assert migrate.migrate_old_settings() is False
