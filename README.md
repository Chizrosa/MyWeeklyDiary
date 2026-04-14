# MyAutoDiary 🌙🐾

ActivityWatchのログとDiscordのつぶやきから、AIが1日の日記を自動生成するローカルWebアプリケーションです。

## 特徴

*  [Open-Meteo API] を利用して、指定した日付の天気と気温を自動取得。
* **ログ自動集計**: ActivityWatchでPC操作時間、Discordから日々のつぶやきを取得。
* **プライバシー保護**: 特定アプリやメアドを自動で匿名化。さらに、AIへ送信する前に画面上でログを直接手動で編集・削除できます。
* **AI自動執筆**: ログと天候データを統合し、Geminiが自然な一人称の日記を作成。
* **夜更かし対応**: 午前3時までの活動は「前日の日記」として扱います。

## 技術スタック
* **Language**: Python 3.14+
* **Package Manager**: [uv](https://github.com/astral-sh/uv) 
* **Web UI**: [Streamlit](https://streamlit.io/) 
* **AI Engine**: [Gemini API](https://aistudio.google.com/)
* **Data Sources**:
    * [ActivityWatch](https://activitywatch.net/) (ローカル活動ログ)
    * [Discord API](https://discord.com/developers/docs/intro) (感情/思考ログ)
    * [Open-Meteo](https://open-meteo.com/) (気象データ)

## API料金とプライバシーについて
* **無料運用が可能**: Gemini API（Google AI Studio）の無料ティアの範囲内で運用可能です（1日の終わりに1回～数回程度の実行を想定）。
* **プライバシーの注意**: 無料枠のAPIはGoogleの学習に利用される可能性があります。絶対に外部に漏らしたくない機密情報等は、送信前の画面でログから削除してください。

## セットアップ

> [!IMPORTANT]
> **本ツールの実行には [ActivityWatch](https://activitywatch.net/) がバックグラウンドで起動している必要があります。**
> 起動していない場合、データの集計時にエラーが発生します。

> [!CAUTION]
> **`.env` ファイルは絶対に GitHub 等に公開しないでください。**
> あなたの Gemini API キーが盗まれ、悪用される危険があります。

**【必要なもの】**
* [uv](https://github.com/astral-sh/uv) (Pythonパッケージマネージャー)
* [ActivityWatch](https://activitywatch.net/) (ローカルで起動しておく)
* Gemini APIキー ([Google AI Studio](https://aistudio.google.com/) から取得)
* *(任意)* Discord Botトークン & チャンネルID

**【インストールと設定】**
```bash
git clone https://github.com/chizrosa/MyAutoDiary.git
cd MyAutoDiary
uv sync
cp .env.example .env
```
作成された `.env` ファイルに、取得したAPIキー等を設定してください。（※`.env`は絶対に公開しないでください）

**Discord連携を行う場合 (任意)**
1. [Developer Portal](https://discord.com/developers/applications) でBotを作成しトークンを取得。
2. Botを自分用の非公開サーバーに招待。
3. Discordの「詳細設定 ＞ 開発者モード」をオンにし、対象チャンネルを右クリックしてIDをコピー。
4. `.env` にトークンとIDを追記します。

## 使い方

以下のコマンド（または`MyAutoDiary.bat`の実行）で起動します。
```bash
uv run streamlit run main.py
```
<br>
<div align="center">
  <img src="assets/screenshots/main_ui.png" width="500">
</div>
<br>

> [!IMPORTANT]
> **MyAutoDiary.bat を実行して開いた黒い画面（コマンドプロンプト）は、アプリのサーバーです。ブラウザを使っている間は、この画面を閉じないでください。 閉じるとアプリも終了してしまいます**

1. 日付を選び **「データを集計」** をクリック。
2. プレビューを確認し、AIに見られたくないログがあればここで直接削除・修正します。
3. **「付け加えたいこと」** の入力欄に、ログには残っていないその日の出来事や感情があればメモします（※ここに書いた内容もAIに送信され、日記に反映されます）。
4. **「AIに日記を書いてもらう」** で日記を生成。
5. **「ファイルに保存する」** でMarkdown形式で保存されます。
   * *(保存されたファイルの上部には「AI日記」、下部にはAIに送らなかったデータも含めた「生ログ全件」がローカル専用の記録として残ります)*

## 📁 フォルダ構成

```text
MyAutoDiary/
├── assets/            # スクリーンショットなどの静的ファイルを格納
│   └── screenshots/   # README表示用の画像を保存
├── main.py            # メインの実行プログラム（AIモデルの指定やフィルター設定）
├── ui_parts.py        # 画面のUI（見た目）を構成するファイル
├── prompt.txt         # AIへの指示書（プロンプト・日記のトーン等をここで調整）
├── MyAutoDiary.bat    # Windows用の一発起動ショートカット
├── .env.example       # 環境変数のひな形（コピーして .env を作成します）
├── pyproject.toml     # パッケージの構成情報
└── README.md          # この説明書
```

## カスタマイズ（自分好みに調整する）

このツールは、ご自身の環境や好みに合わせて自由にカスタマイズ可能です。

* **プロンプトの変更 (`prompt.txt`)**: 
  AIの口調、日記の文字数、重視してほしいポイントを変えたい場合は、このテキストファイルを編集してください。
* **使用するAIモデルの変更 (`main.py`)**: 
  コード内のモデル指定部分（例: `gemini-1.5-flash` 等）を書き換えることで任意のモデルに変更できます。
* **プライバシーフィルターの育成 (`main.py`)**: 
  「このアプリ名も匿名化したい」「このキーワードは無視してほしい」という場合は、コード内のフィルター用リストや条件に単語を書き足すことで、自分専用にフィルターをカスタマイズしてください。

## 拡張例・応用例

このツールは、Discord に送信されたデータであれば柔軟に対応できます。
ユーザーが工夫次第で、以下のような情報も日記に統合できます：

* **iPhone ショートカット** - 歩数、ワークアウト、移動距離などのヘルスデータ
* **ゲーム監視** - Steam や各ゲームプラットフォームのプレイ時間・成績
* **IoT デバイス** - 睡眠データ、体温計、スマートホーム連携
* **外部 API** - GitHub コントリビューション、Spotify の再生履歴など

**コツ**: Discord に投稿されたメッセージなら、ActivityWatch とは無関係に AI に送信され、日記に反映されます。

### 実装例
- iPhone のショートカットで毎日の歩数を Discord に送信 → 翌日の日記に「○○歩歩きました」と自動反映
- PCゲームのプレイログを監視ツールで Discord に飛ばす → 「今日は○○をプレイしました」と統合

## Obsidianユーザーの方へ
`.env` ファイル内の `SAVE_DIR` をご自身のVault（保管庫）の絶対パスに変更すると、直接Obsidian内に日記が保存されるようになります。（重要キーワードは自動で [[ ]] リンク化されます。不要な場合は`prompt.txt`を編集してください。）

## 免責事項
本ツールは個人開発のプロジェクトです。AIの性質上、事実と異なる内容が生成される可能性があります。万が一のデータ消失やAPIの意図せぬ課金等について開発者は責任を負いかねますので、適宜バックアップを取り、自己責任の範囲でご活用ください。

## ライセンス / 開発について
* This project is licensed under the MIT License.
* コードの大部分は、AIアシスタント（Gemini）とのペアプログラミングによって作成されました。
