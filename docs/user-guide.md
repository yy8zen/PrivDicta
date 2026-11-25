# moonshine-dictate の使い方

話した日本語を、カーソルのある場所に入力するアプリです。音声の認識はすべてこの PC の中で行い、インターネットには接続しません。

Powered by Moonshine AI

## インストールする

### Windows

1. `moonshine-dictate-<バージョン>-windows-setup.exe` を実行します。管理者権限は要りません。
2. 「Windows によって PC が保護されました」と表示されたら、「詳細情報」を押してから「実行」を押します。このアプリには電子署名がないため表示されます。
3. 「アプリケーション制御ポリシーによってこのファイルがブロックされました」と表示された場合は、もう一度実行してみてください。何度実行しても止められる場合は、「Windows セキュリティ > アプリとブラウザーの制御 > スマート アプリ コントロール」がオンになっています。このアプリを使うには、オフにする必要があります。

### macOS（Apple Silicon の Mac のみ）

1. `moonshine-dictate-<バージョン>-macos-arm64.dmg` を開き、`moonshine-dictate.app` を「Applications」フォルダにドラッグします。
2. 「アプリケーション」フォルダで moonshine-dictate を右クリックし、「開く」を選びます。開けない場合は、一度ダブルクリックして警告を閉じてから、「システム設定 > プライバシーとセキュリティ」の下にある「このまま開く」を押します。このアプリは Apple の署名と公証を受けていないため、この手順が要ります。
3. 「マイク」と「アクセシビリティ」の許可を求められたら、許可します。アクセシビリティは、ホットキーの検出と文字の入力に使います。

### Linux

1. AppImage に実行権限を付けて実行します。

   ```
   chmod +x moonshine-dictate-*-linux-x86_64.AppImage
   ./moonshine-dictate-*-linux-x86_64.AppImage
   ```

2. 「libfuse.so.2 が見つからない」と表示されたら、Ubuntu 24.04 では `sudo apt install libfuse2t64`、22.04 では `sudo apt install libfuse2` を実行します。
3. Wayland では、アプリがホットキーを登録できません。OS の設定でショートカットキーを追加し、`<AppImage のパス> toggle` を割り当ててください。

## 使う

起動すると、画面にウィンドウは出ず、タスクトレイ（Windows は画面右下、macOS は画面右上のメニューバー）にマイクのアイコンが出ます。初回だけ使い方の画面が出ます。アイコンが黄色の間はモデルを読み込んでいます。灰色になったら使えます。

1. 文字を入れたい場所（メモ帳やブラウザの入力欄など）をクリックします。
2. **Ctrl + Alt + Space**（macOS は **Control + Option + Space**）を押します。画面の下に録音ウィンドウが出て、マイクのボタンが赤くなります。
3. 話します。
4. もう一度ホットキーを押すか、録音ウィンドウのマイクのボタンを押すと、録音が終わって文字が入ります。60秒間何も話さなかった場合も終わります。

## 設定を変える

アイコンを右クリック（macOS はクリック）して「設定…」を選びます。

| 項目 | 内容 |
| --- | --- |
| ホットキー | 欄をクリックしてから、使いたいキーの組み合わせを押します |
| 入れ方 | 録音の終了時にまとめて入れるか、話の区切りごとに入れるか |
| 句読点 | 認識結果のまま／区切りの終わりに「。」を足す／句読点を入れない |
| 無音で終了するまで | 無音がこの秒数続くと録音を終えます |
| マイク | 使うマイク |
| 置換表 | 認識結果の中の文字列を別の文字列に置き換えます（例：「でぃすこーど」を「Discord」に） |
| ログインしたときに自動で起動する | オンにすると、毎回起動する必要がなくなります |

## 次に起動するとき

- Windows：スタートメニューの「moonshine-dictate」
- macOS：「アプリケーション」フォルダの moonshine-dictate
- Linux：AppImage のファイルを実行

設定で「ログインしたときに自動で起動する」をオンにしておくと、起動の操作は要りません。

## 終了する

アイコンのメニューから「終了」を選びます。

## アンインストールする

- **Windows：**「設定 > アプリ > インストールされているアプリ」で moonshine-dictate の「…」から「アンインストール」を選びます。
- **macOS：** アプリを終了し、「アプリケーション」フォルダの moonshine-dictate をゴミ箱に入れます。「システム設定 > プライバシーとセキュリティ > アクセシビリティ」の一覧からも削除します。
- **Linux：** アプリを終了し、AppImage のファイルを削除します。

設定とログは次のフォルダに残ります。不要なら削除してください。

| OS | フォルダ |
| --- | --- |
| Windows | `%APPDATA%\moonshine-dictate` |
| macOS | `~/Library/Application Support/moonshine-dictate` |
| Linux | `~/.config/moonshine-dictate` |

## うまく動かないとき

上のフォルダにある `moonshine-dictate.log` に、動作の記録が残っています。不具合を報告するときは、このファイルの内容を添えてください。

## ライセンス

- moonshine-dictate のソースコードは MIT License です。
- 同梱している日本語の音声認識モデル（base-ja）は、Moonshine AI Community License のもとで配布しています。全文は `MOONSHINE-LICENSE.txt`、帰属表示は `NOTICE.txt` にあります。
- そのほかに同梱しているソフトウェア（Qt / PySide6、pynput、numpy、ONNX Runtime など）のライセンスと、ソースコードの入手先は、`third_party_licenses` フォルダの `THIRD-PARTY-NOTICES.md` にあります。Windows ではインストール先のフォルダ、macOS では dmg の中とアプリの `Contents/Resources` にあります。
