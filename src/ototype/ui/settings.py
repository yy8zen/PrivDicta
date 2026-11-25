"""設定画面（要件 R6.3）。保存すると設定ファイル（TOML）に書き出す。"""

from __future__ import annotations

import dataclasses

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ototype.config import LOG_LEVELS, Config
from ototype.hotkey import parse_hotkey
from ototype.platform_info import IS_MACOS

MODEL_LABELS = {
    "base": "base（標準。区切りが確定してから文字が出る）",
    "small-streaming": "small-streaming（話している途中から文字が出るが、精度は低い）",
    "tiny-streaming": "tiny-streaming（軽いが精度はさらに低い）",
}
PUNCTUATION_LABELS = {
    "keep": "認識結果のまま",
    "add": "区切りの終わりに「。」を足す",
    "remove": "句読点（、。！？）を入れない",
}
INSERT_LABELS = {
    "clipboard": "録音の終了時にまとめて入れる",
    "live": "話の区切りごとに入れる（ライブ入力）",
}
LOG_LABELS = {"error": "エラーだけ", "info": "通常", "debug": "詳しく"}

_NAMED_KEYS = {
    Qt.Key_Space: "space", Qt.Key_Return: "enter", Qt.Key_Enter: "enter", Qt.Key_Tab: "tab",
    Qt.Key_Backspace: "backspace", Qt.Key_Insert: "insert", Qt.Key_Delete: "delete",
    Qt.Key_Home: "home", Qt.Key_End: "end", Qt.Key_PageUp: "pageup", Qt.Key_PageDown: "pagedown",
    Qt.Key_Up: "up", Qt.Key_Down: "down", Qt.Key_Left: "left", Qt.Key_Right: "right",
    Qt.Key_Pause: "pause", Qt.Key_ScrollLock: "scrolllock",
}
_MODIFIER_KEYS = {Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Meta, Qt.Key_AltGr}


def key_event_to_hotkey(key: int, modifiers, is_macos: bool = IS_MACOS) -> str | None:
    """キー操作を設定ファイルの書き方（"ctrl+alt+space" など）に変える。使えないキーなら None。"""
    if key in _MODIFIER_KEYS:
        return None
    if Qt.Key_A <= key <= Qt.Key_Z:
        name = chr(key).lower()
    elif Qt.Key_0 <= key <= Qt.Key_9:
        name = chr(key)
    elif Qt.Key_F1 <= key <= Qt.Key_F20:
        name = f"f{key - Qt.Key_F1 + 1}"
    elif key in _NAMED_KEYS:
        name = _NAMED_KEYS[key]
    else:
        return None
    mods = []
    # macOS の Qt は、Command キーを ControlModifier、Control キーを MetaModifier として渡す
    if is_macos:
        if modifiers & Qt.MetaModifier:
            mods.append("ctrl")
        if modifiers & Qt.AltModifier:
            mods.append("option")
        if modifiers & Qt.ShiftModifier:
            mods.append("shift")
        if modifiers & Qt.ControlModifier:
            mods.append("cmd")
    else:
        if modifiers & Qt.ControlModifier:
            mods.append("ctrl")
        if modifiers & Qt.AltModifier:
            mods.append("alt")
        if modifiers & Qt.ShiftModifier:
            mods.append("shift")
        if modifiers & Qt.MetaModifier:
            mods.append("win")
    text = "+".join(mods + [name])
    try:
        parse_hotkey(text)
    except ValueError:
        return None
    return text


class HotkeyEdit(QLineEdit):
    """クリックしてからキーを押すと、そのキーの組み合わせを登録する入力欄。"""

    rejected_key = Signal()

    def __init__(self, value: str, parent: QWidget | None = None):
        super().__init__(value, parent)
        self.setReadOnly(True)
        # 画面を開いた直後に、この欄へフォーカスが入らないようにする。入ると、押したキーで書き換わってしまう
        self.setFocusPolicy(Qt.ClickFocus)
        self.setPlaceholderText("ここをクリックしてキーを押す")
        self._value = value

    def value(self) -> str:
        return self._value

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self.setText("キーを押してください（Esc で取り消し）")

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self.setText(self._value)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape and not event.modifiers():
            self.clearFocus()
            return
        text = key_event_to_hotkey(event.key(), event.modifiers())
        if text is None:
            if event.key() not in _MODIFIER_KEYS:
                self.rejected_key.emit()
            return
        self._value = text
        self.setText(text)
        self.clearFocus()


class SettingsDialog(QDialog):
    open_file_requested = Signal()

    def __init__(self, cfg: Config, models: list[str], devices: list[str],
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("OtoType の設定")
        self.setMinimumWidth(520)
        self._base = cfg

        # ---- 録音と入力 ----
        self.hotkey = HotkeyEdit(cfg.hotkey)
        self._hotkey_hint = QLabel("修飾キー（Ctrl、Alt など）と組み合わせてください。単独で使えるのは F1〜F20 だけです")
        self._hotkey_hint.setWordWrap(True)
        self._hotkey_hint.setStyleSheet("color: gray;")
        self.hotkey.rejected_key.connect(
            lambda: self._hotkey_hint.setStyleSheet("color: #e5484d;"))
        self.insert_method = QComboBox()
        for key, label in INSERT_LABELS.items():
            self.insert_method.addItem(label, key)
        self._select(self.insert_method, cfg.insert_method)
        self.punctuation = QComboBox()
        for key, label in PUNCTUATION_LABELS.items():
            self.punctuation.addItem(label, key)
        self._select(self.punctuation, cfg.punctuation)
        self.restore_clipboard = QCheckBox("貼り付けた後に、元のクリップボードの内容に戻す")
        self.restore_clipboard.setChecked(cfg.restore_clipboard)
        self.silence = QSpinBox()
        self.silence.setRange(1, 3600)
        self.silence.setSuffix(" 秒")
        self.silence.setValue(cfg.silence_timeout_sec)

        basic = QGroupBox("録音と入力")
        form = QFormLayout(basic)
        form.addRow("ホットキー", self.hotkey)
        form.addRow("", self._hotkey_hint)
        form.addRow("入れ方", self.insert_method)
        form.addRow("", self.restore_clipboard)
        form.addRow("句読点", self.punctuation)
        form.addRow("無音で終了するまで", self.silence)

        # ---- 音声認識 ----
        self.device = QComboBox()
        self.device.addItem("OS の既定のマイク", "")
        for name in devices:
            self.device.addItem(name, name)
        if cfg.input_device and self.device.findData(cfg.input_device) < 0:
            self.device.addItem(f"{cfg.input_device}（見つかりません）", cfg.input_device)
        self._select(self.device, cfg.input_device)
        self.model = QComboBox()
        for key in models:
            self.model.addItem(MODEL_LABELS.get(key, key), key)
        if self.model.findData(cfg.model_arch) < 0:
            self.model.addItem(f"{cfg.model_arch}（モデルが見つかりません）", cfg.model_arch)
        self._select(self.model, cfg.model_arch)
        self.sound = QCheckBox("録音の開始・終了時に効果音を鳴らす")
        self.sound.setChecked(cfg.sound)

        speech = QGroupBox("音声認識")
        form = QFormLayout(speech)
        form.addRow("マイク", self.device)
        form.addRow("モデル", self.model)
        form.addRow("", self.sound)

        # ---- 置換表 ----
        self.replace = QTableWidget(0, 2)
        self.replace.setHorizontalHeaderLabels(["認識結果の文字列", "置き換え後"])
        self.replace.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.replace.verticalHeader().setVisible(False)
        self.replace.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.replace.setMinimumHeight(140)
        for src, dst in cfg.replace.items():
            self._add_row(src, dst)
        add = QPushButton("行を追加")
        add.clicked.connect(lambda: self._add_row("", "", edit=True))
        remove = QPushButton("選んだ行を削除")
        remove.clicked.connect(self._remove_rows)
        replace_box = QGroupBox("置換表")
        lay = QVBoxLayout(replace_box)
        lay.setSpacing(8)
        lay.addWidget(self.replace, 1)
        row = QHBoxLayout()
        row.addWidget(add)
        row.addWidget(remove)
        row.addStretch()
        lay.addLayout(row)

        # ---- その他 ----
        self.autostart = QCheckBox("OS にログインしたときに自動で起動する")
        self.autostart.setChecked(cfg.autostart)
        self.log_level = QComboBox()
        for key in LOG_LEVELS:
            self.log_level.addItem(LOG_LABELS[key], key)
        self._select(self.log_level, cfg.log_level)
        other = QGroupBox("その他")
        form = QFormLayout(other)
        form.addRow("", self.autostart)
        form.addRow("ログの出力量", self.log_level)

        # ---- ボタン ----
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("保存")
        buttons.button(QDialogButtonBox.Cancel).setText("キャンセル")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        open_file = QPushButton("設定ファイルを開く")
        open_file.clicked.connect(self.open_file_requested)
        bottom = QHBoxLayout()
        bottom.addWidget(open_file)
        bottom.addStretch()
        bottom.addWidget(buttons)

        layout = QVBoxLayout(self)
        for box in (basic, speech, replace_box, other):
            layout.addWidget(box)
        layout.addLayout(bottom)
        buttons.button(QDialogButtonBox.Save).setFocus()

    def result_config(self) -> Config:
        """画面の内容を設定にして返す。画面にない項目（model_dir）は元の値のまま。"""
        replace = {}
        for r in range(self.replace.rowCount()):
            src = (self.replace.item(r, 0) or QTableWidgetItem("")).text()
            dst = (self.replace.item(r, 1) or QTableWidgetItem("")).text()
            if src:
                replace[src] = dst
        return dataclasses.replace(
            self._base,
            hotkey=self.hotkey.value(),
            insert_method=self.insert_method.currentData(),
            restore_clipboard=self.restore_clipboard.isChecked(),
            punctuation=self.punctuation.currentData(),
            silence_timeout_sec=self.silence.value(),
            input_device=self.device.currentData(),
            model_arch=self.model.currentData(),
            sound=self.sound.isChecked(),
            autostart=self.autostart.isChecked(),
            log_level=self.log_level.currentData(),
            replace=replace,
            errors=[],
        )

    # ---- 内部 ----

    @staticmethod
    def _select(combo: QComboBox, data) -> None:
        index = combo.findData(data)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _add_row(self, src: str, dst: str, edit: bool = False) -> None:
        r = self.replace.rowCount()
        self.replace.insertRow(r)
        self.replace.setItem(r, 0, QTableWidgetItem(src))
        self.replace.setItem(r, 1, QTableWidgetItem(dst))
        if edit:
            self.replace.setCurrentCell(r, 0)
            self.replace.editItem(self.replace.item(r, 0))

    def _remove_rows(self) -> None:
        for r in sorted({i.row() for i in self.replace.selectedIndexes()}, reverse=True):
            self.replace.removeRow(r)
