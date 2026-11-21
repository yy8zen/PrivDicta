# moonshine-dictate
Moonshine Voiceを使った、Windows・macOS・Linux対応のローカル音声入力ツール。

ホットキーを押すと録音が始まり、話した日本語がフォーカスのあるアプリに入力されます。操作は Windows 11 の音声入力（Win+H）に合わせています。音声認識はすべて PC の中で行い、ネットワーク通信は一切しません。

## 使い方

1. アプリを起動すると、タスクトレイ（macOS ではメニューバー）にマイクのアイコンが出ます。アイコンが灰色になったら使えます。モデルを読み込んでいる間は黄色です。
2. 文字を入れたい場所をクリックしてから、**Ctrl+Alt+Space**（macOS では **Control+Option+Space**）を押します。画面の下に録音ウィンドウが出て、マイクのボタンが赤く点灯します。
3. 話します。認識中の文字は録音ウィンドウに表示されます。
4. 次のどれかで録音が終わります。
   - もう一度ホットキーを押す
   - 録音ウィンドウのマイクのボタンを押す
   - 無音が60秒続く

テキストの入れ方は2種類あり、設定ファイルで選べます。

| 設定値 | 入るタイミング | 方法 |
| --- | --- | --- |
| `clipboard`（標準） | 録音の終了時に全文 | クリップボードに入れて Ctrl+V（macOS は Cmd+V）を送る。貼り付けの後、元のクリップボードの内容に戻す |
| `live` | 話の区切りが確定するたび | Windows と macOS はキー入力として送る。Linux はクリップボード経由で区切りごとに貼り付ける |

コマンドラインからも操作できます。OS のショートカットキーに割り当てる場合などに使います。

```
moonshine-dictate toggle   # 録音の開始・終了を切り替える（start / stop / reload / quit も使える）
```

## 設定ファイル

初回の起動時に、次の場所に標準値の設定ファイルが作られます。各項目の説明はファイルの中にコメントで書いてあります。トレイのメニューから「設定ファイルを開く」で開けます。編集した後は「設定の再読み込み」で反映されます。

| OS | 場所 |
| --- | --- |
| Windows | `%APPDATA%\moonshine-dictate\config.toml` |
| macOS | `~/Library/Application Support/moonshine-dictate/config.toml` |
| Linux | `~/.config/moonshine-dictate/config.toml` |

設定できる項目は、ホットキー、無音で終了するまでの秒数、テキストの入れ方、クリップボードを元に戻すか、マイクのデバイス、効果音、ログイン時の自動起動、ログの出力量、認識結果の置換表です。ログは設定ファイルと同じフォルダの `moonshine-dictate.log` に出ます。

## OS ごとの注意

### macOS

配布しているアプリは Apple の署名と公証を受けていません。

- 初回は、Finder でアプリを右クリックして「開く」を選んでください。ダブルクリックでは警告が出て開けません。
- 「システム設定 > プライバシーとセキュリティ」で、**マイク**と**アクセシビリティ**を許可してください。アクセシビリティは、ホットキーの検出とテキストの入力に使います。
- アップデートした後にホットキーが効かなくなったら、アクセシビリティの一覧から moonshine-dictate を一度削除して、もう一度許可してください。

### Linux（X11）

すべての機能が使えます。AppImage を使わずに動かす場合、Ubuntu では `libxcb-cursor0` と `libportaudio2` が必要です。

### Linux（Wayland）

Wayland では、セキュリティの仕組み上、ほかのアプリのキー入力を監視できません。そのため次の制限があります。

- ホットキーはアプリでは登録しません。OS の設定でショートカットキーを追加し、コマンド `moonshine-dictate toggle` を割り当ててください（GNOME では「設定 > キーボード > ショートカットを表示およびカスタマイズ > カスタムショートカット」）。
- テキストは `wl-copy`（パッケージ名 `wl-clipboard`）でクリップボードに入れ、`ydotool` があれば Ctrl+V を送ります。`ydotool` がない場合は、通知が出たら自分で Ctrl+V を押してください。
- ライブ入力は使えず、クリップボード方式で動きます。

## 開発

```
pip install -e ".[dev]"
python scripts/fetch_model.py      # 同梱する日本語モデルを models/ にダウンロードする
python -m moonshine_dictate        # 起動する
python -m pytest                   # テスト（Linux では xvfb-run -a python -m pytest）
pyinstaller packaging/moonshine-dictate.spec   # 配布用に固める
```

要件は [docs/requirements.md](docs/requirements.md) にまとめています。配布物は GitHub Actions（`.github/workflows/build.yml`）で作ります。`v` で始まるタグを push すると、Windows のインストーラー、macOS の dmg（Apple Silicon 版のみ）、Linux の AppImage をリリースの下書きに添付します。

## 📄 ライセンス

### ソースコード
このリポジトリに含まれるソースコードは [MIT License](LICENSE) の下で公開されています。

### 配布バイナリ・音声認識モデルについて
リリースページ等で配布している実行ファイル（`.exe` / `.dmg` / `.AppImage`）には、Moonshine AIの日本語音声認識モデルが同梱されています。  
そのため、同梱モデルおよびモデルを含む配布パッケージの利用には **[Moonshine Community License](https://www.moonshine.ai/license)** が適用されます。

- 配布パッケージは無料です。
- 商用目的での利用の条件は、[ライセンス全文](https://www.moonshine.ai/license)をご確認ください。
