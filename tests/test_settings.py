import tomllib

import pytest
from PySide6.QtCore import Qt

from ototype import config
from ototype.session import BROKEN, IDLE, LOADING
from ototype.ui.settings import SettingsDialog, key_event_to_hotkey
from tests.test_session import make


def test_render_round_trip(tmp_path):
    cfg = config.Config(model_arch="base", input_device='USB "Mic"', silence_timeout_sec=30,
                        replace={"でぃすこーど": "Discord", 'a"b': "c\\d\nx"})
    path = tmp_path / "config.toml"
    config.save(path, cfg)
    loaded = config.load(path)
    assert loaded.errors == []
    assert loaded == cfg
    # 説明のコメントが残っている
    assert "# 使うモデルの種類" in path.read_text(encoding="utf-8")


def test_default_file_parses_without_errors(tmp_path):
    path = tmp_path / "config.toml"
    config.write_default(path)
    assert config.parse(tomllib.loads(path.read_text(encoding="utf-8"))) == config.Config()


@pytest.mark.parametrize("key, mods, mac, expected", [
    (Qt.Key_Space, Qt.ControlModifier | Qt.AltModifier, False, "ctrl+alt+space"),
    (Qt.Key_D, Qt.ControlModifier | Qt.ShiftModifier, False, "ctrl+shift+d"),
    (Qt.Key_F9, Qt.NoModifier, False, "f9"),
    # macOS の Qt では Control キーが MetaModifier、Command キーが ControlModifier
    (Qt.Key_Space, Qt.MetaModifier | Qt.AltModifier, True, "ctrl+option+space"),
    (Qt.Key_K, Qt.ControlModifier, True, "cmd+k"),
])
def test_key_event_to_hotkey(key, mods, mac, expected):
    assert key_event_to_hotkey(key, mods, is_macos=mac) == expected


@pytest.mark.parametrize("key, mods", [
    (Qt.Key_A, Qt.NoModifier),          # 修飾キーなしの通常キーは使えない
    (Qt.Key_Control, Qt.ControlModifier),  # 修飾キーだけ
    (Qt.Key_Eacute, Qt.ControlModifier),   # 対応していないキー
])
def test_key_event_to_hotkey_rejects(key, mods):
    assert key_event_to_hotkey(key, mods, is_macos=False) is None


def test_dialog_returns_edited_config(qapp):
    cfg = config.Config(replace={"あ": "い"}, model_dir="")
    dialog = SettingsDialog(cfg, ["small-streaming", "base"], ["Mic A", "Mic B"])
    dialog.model.setCurrentIndex(dialog.model.findData("base"))
    dialog.device.setCurrentIndex(dialog.device.findData("Mic B"))
    dialog.insert_method.setCurrentIndex(dialog.insert_method.findData("live"))
    dialog.silence.setValue(90)
    dialog.sound.setChecked(False)
    dialog._add_row("でぃすこーど", "Discord")
    result = dialog.result_config()
    assert result.model_arch == "base"
    assert result.input_device == "Mic B"
    assert result.insert_method == "live"
    assert result.silence_timeout_sec == 90
    assert result.sound is False
    assert result.replace == {"あ": "い", "でぃすこーど": "Discord"}
    assert result.hotkey == cfg.hotkey


def test_dialog_keeps_unknown_values(qapp):
    cfg = config.Config(input_device="消えたマイク", model_arch="base")
    dialog = SettingsDialog(cfg, ["small-streaming"], [])
    result = dialog.result_config()
    assert result.input_device == "消えたマイク"
    assert result.model_arch == "base"


def test_model_reload_keeps_old_model_on_failure(qapp):
    session, engine, _, _, notes, _ = make()
    engine.is_loaded = True
    engine.loaded.emit()
    assert session.state == IDLE
    session.begin_loading()
    assert session.state == LOADING
    engine.load_failed.emit("壊れたモデル")
    assert session.state == IDLE
    assert "前のモデル" in notes[-1]


def test_first_load_failure_is_broken(qapp):
    session, engine, *_ = make()
    engine.is_loaded = False
    engine.load_failed.emit("なし")
    assert session.state == BROKEN


def test_dialog_punctuation(qapp):
    dialog = SettingsDialog(config.Config(), ["base"], [])
    assert dialog.result_config().punctuation == "keep"
    dialog.punctuation.setCurrentIndex(dialog.punctuation.findData("remove"))
    assert dialog.result_config().punctuation == "remove"


def test_base_is_default_model():
    assert config.Config().model_arch == "base"


def test_welcome_dialog_builds(qapp):
    from ototype.ui.welcome import POWERED_BY, WelcomeDialog, build_html

    html = build_html("ctrl+alt+space")
    assert "Ctrl + Alt + Space" in html
    assert POWERED_BY in html
    dialog = WelcomeDialog("ctrl+alt+space", autostart=True)
    assert dialog.autostart.isChecked()
