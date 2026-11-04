# メンテナ向けガイド

一覧ID: `io.github.baxter.vpm`。公開URL: https://malaybaku.github.io/baku-vpm/index.json

## 一覧とページの生成

Python 3.10以降の標準ライブラリだけで生成します。pip、.NET、Scriban、外部の一覧ビルダーは使用しません。GitHub ActionsではPython 3.14を使用します。

    python -m unittest discover -s tests -v
    python scripts/build_listing.py

出力はGit管理対象外のdist/index.json、dist/index.html、dist/.nojekyllです。GitHub Pagesにはdist/だけをアップロードします。Website/index.htmlはPython string.Template形式の雛形です。パッケージ等の文字列はHTMLエスケープし、テンプレートとして再評価しません。

source.jsonのpackages[].releasesで公開済みのパッケージZIPを指定します。githubReposからのリリース自動探索は対応しません。ZIP直下のpackage.jsonから情報を取得し、ダウンロードURLとZIP全体のSHA-256を一覧へ追加します。依存関係はマニフェストからそのまま引き継ぎます。依存パッケージそのものの可用性やUnityでの動作を検証する処理ではありません。

## 過去バージョンと失敗時の扱い

通常はsource.jsonのurlから既存の公開一覧を読み、過去のパッケージ・バージョンを保持したまま追加します。最初の公開で一覧がHTTP 404の場合のみ空から開始します。それ以外の取得失敗や不正なJSONは停止します。

同じパッケージID・バージョンのマニフェストやZIPのハッシュが既存一覧と異なる場合は、公開済み版を上書きせず停止します。修正時はパッケージのバージョンを上げてください。

未公開ZIPの404、壊れたZIP、名前の不一致、不正なバージョン等も失敗扱いです。失敗を無視して不完全な一覧を公開しません。ワークフローが生成に失敗した場合はPagesのデプロイも行われません。

現在source.jsonは未公開のVRC用パッケージ0.1.0を参照しています。このZIPの取得失敗は生成処理の置き換えでは解消していません。公開時に実際の配布URL・版番号を合わせてください。

公開一覧の取得を使わず、保存済みの一覧を指定して検証することもできます。新規一覧としての検証には空オブジェクト{}を書いたJSONを指定します。

    python scripts/build_listing.py --source source.json --previous previous.json --output dist

既存のVCC等への公開を継続する際は、意図せず空のprevious.jsonを指定して過去版を消さないようにしてください。

## 公開・更新

1. 本体と依存の導入経路を整備し、クローズドテストを完了する。
2. 本体リリースを公開し、source.jsonに公開済みZIPのURLを追加する。過去のURLは残す。
3. 差分をレビューしてcommit/pushする。mainへのsource.json、scripts、tests、Website、workflowの変更で生成が走る。手動実行も可能。
4. GitHub側のSettings → Pages → SourceをGitHub Actionsに設定する。
5. 生成・配信成功後、一覧JSONとページ、VCC / ALCOMでの追加・導入・更新を検証する。

本体のリリース公開だけでは、この別リポジトリの一覧は更新されません。

## 依存関係の残作業

基盤のMaterialOverrideVrm v0.3.1には単体ZIPも公開済みですが、今回のVRC用パッケージとUniVRMの依存導入は別途整備が必要です。VRC用パッケージに依存なしで起動するセットアップ部分を設け、UPMで必要なパッケージを取得する方針です。未導入時に出力機能がコンパイルエラーを起こさないようにする作業も含みます。

## ローカル検証

- unittest: 11件（過去版保持、公開版改変拒否、SemVer順序、ZIP/JSON検証、HTMLエスケープ、危険なURL拒否、404と部分出力防止、生成ファイルの確認等）。
- 公開済みMaterialOverrideVrm 0.3.1のZIPを、本番とは別の検証用source.jsonでダウンロードし、マニフェスト・既知のSHA-256・JSON/HTML出力を確認。
- その出力をpreviousとして再実行し、生成物がバイト単位で一致することを確認。
- actionlintによるworkflowの静的検証。
