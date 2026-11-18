# メンテナ向けガイド

一覧ID: `io.github.baxter.vpm`。公開URL: https://malaybaku.github.io/baku-vpm/index.json

## 現在の掲載状態

2026-11-17にCore v0.3.4の公開リリースと添付ZIP3点を確認しました。ZIPはローカル生成物と完全一致し、パッケージのバージョン・URPチェック・テンプレートの参照タグを検査済みです。source.jsonへ0.3.4の配布URLを追加しています。 テスト11件と、Coreのみを対象にした一覧・HTML・0.3.4のZIPハッシュの検証は成功しました。全体の一覧生成は、既存のVRC 0.1.0掲載予定URLがHTTP 404のため停止します。

2026-11-15の確認時点では、公開中の一覧とGitHub側のsource.jsonには、基盤パッケージMaterialOverrideVrm 0.3.2のみが掲載されています。PagesとAdd to VCCの動作は確認済みです。

ローカルのsource.jsonは0.3.2を残して、公開済みCore 0.3.3のZIPを追加しています。ローカル生成で0.3.2と0.3.3の掲載を確認していますが、この差分はまだcommit/pushしていません。反映後にGitHub Actions・Pages・VCC / ALCOMで確認してください。

ローカルのsource.jsonには、VRC用パッケージ0.1.0の掲載予定URLも追加しています。本体のリリースとZIPはまだ未公開です。VRC本体のタグは `0.1.0`（`v`接頭辞なし）、添付ファイル名は `com.baxter.material-override-vrm-vrc-0.1.0.zip` を前提とし、本体のビルドスクリプト・リリースworkflowと揃えています。

**VRCのZIP公開前にこのsource.jsonをpushして一覧生成を実行すると、404で失敗します。先にVRC本体のリリースと添付ZIPを公開し、その後この一覧を更新してください。** Core 0.3.3だけを先に配信する場合は、VRCの項目を含めずCoreの追加差分だけを反映します。VRC側はCore 0.3.3以上0.4未満を要求するため、VRC掲載時にはCore 0.3.3も一覧から解決できる状態にします。

## 一覧とページの生成

Python 3.10以降の標準ライブラリだけで生成します。pip、.NET、Scriban、外部の一覧ビルダーは使用しません。GitHub ActionsではPython 3.14を使用します。

```text
python -m unittest discover -s tests -v
python scripts/build_listing.py
```

出力はGit管理対象外のdist/index.json、dist/index.html、dist/.nojekyllです。GitHub Pagesにはdist/だけをアップロードします。Website/index.htmlはPython string.Template形式の雛形です。パッケージ等の文字列はHTMLエスケープし、テンプレートとして再評価しません。

source.jsonのpackages[].releasesで公開済みのパッケージZIPを指定します。githubReposからのリリース自動探索は対応しません。ZIP直下のpackage.jsonから情報を取得し、ダウンロードURLとZIP全体のSHA-256を一覧へ追加します。依存関係はマニフェストからそのまま引き継ぎます。依存パッケージそのものの可用性やUnityでの動作を検証する処理ではありません。

## 過去バージョンと失敗時の扱い

通常はsource.jsonのurlから既存の公開一覧を読み、過去のパッケージ・バージョンを保持したまま追加します。最初の公開で一覧がHTTP 404の場合のみ空から開始します。それ以外の取得失敗や不正なJSONは停止します。現在は公開済みの一覧があるため、通常の更新ではそれを引き継ぎます。

同じパッケージID・バージョンのマニフェストやZIPのハッシュが既存一覧と異なる場合は、公開済み版を上書きせず停止します。修正時はパッケージのバージョンを上げてください。

未公開ZIPの404、壊れたZIP、名前の不一致、不正なバージョン等も失敗扱いです。失敗を無視して不完全な一覧を公開しません。ワークフローが生成に失敗した場合はPagesのデプロイも行われません。

過去版を保持するため、掲載済みパッケージをsource.jsonから外しても公開一覧からは消えません。掲載停止が必要な場合は別途明示的な対応を行ってください。

公開一覧の取得を使わず、保存済みの一覧を指定して検証することもできます。新規一覧としての検証には空オブジェクト{}を書いたJSONを指定します。

```text
python scripts/build_listing.py --source source.json --previous previous.json --output dist
```

既存のVCC等への公開を継続する際は、意図せず空のprevious.jsonを指定して過去版を消さないようにしてください。

## 公開・更新

1. 新しいパッケージを初公開する場合は、本体と依存の導入経路を整備し、クローズドテストを完了する。
2. 本体リリースを公開し、source.jsonに公開済みZIPのURLを追加する。過去のURLは残す。
3. unittestと一覧生成を実行し、掲載ID・バージョン・配布URLを確認する。
4. 差分をレビューしてcommit/pushする。mainへのsource.json、scripts、tests、Website、workflowの変更で生成が走る。手動実行も可能。
5. 生成・配信成功後、一覧JSONとページ、VCC / ALCOMでの追加・導入・更新を検証する。

GitHub側のSettings → Pages → SourceはGitHub Actionsを使用します。本体のリリース公開だけでは、この別リポジトリの一覧は更新されません。

## 依存関係の実装状況と残作業

基盤のMaterialOverrideVrmはVPM用メタデータと条件付きコンパイルに対応済みで、v0.3.4まで公開済みです。URPは基盤のUPM依存です。

VRC用パッケージでは、CoreをvpmDependenciesへ追加し、依存導入前の条件付きコンパイルと、独立したSetup画面を実装済みです。UniVRMは利用者がPackage Managerから手動で追加し、Setupは手順案内とURLコピーだけを提供します。案内する版は0.131.4です。パッケージ取得APIは呼びません。

新規VRCプロジェクトで配布ZIP相当の本体と公開済みCoreを用いた検証は完了しています。UniVRM未導入からの手動セットアップと、両モードの.mouv生成・AssetBundle再読み込みを確認済みです。今後必要なのはVRC本体の初回リリース公開、この掲載差分の配信、および公開VPM一覧からの最終導入確認です。VRC本体の具体的な公開手順は同リポジトリのMAINTENANCE.mdを参照してください。

## 検証記録

### 一覧生成処理

- unittest: 11件（過去版保持、公開版改変拒否、SemVer順序、ZIP/JSON検証、HTMLエスケープ、危険なURL拒否、404と部分出力防止、生成ファイルの確認等）。2026-11-15にも全件成功。
- 初期実装時に、公開済みCore 0.3.1のZIPを別の検証用source.jsonで取得し、マニフェスト・ハッシュ・生成結果を確認。再生成結果の一致とactionlintによるworkflowの静的検証も実施。
- Core 0.3.2のみを掲載した状態で、ユーザーがPagesとAdd to VCCを確認済み。

### Core 0.3.3追加のローカル検証（2026-11-15）

- 公開v0.3.3リリースがdraft / prereleaseではないことと、source.jsonのURLが添付パッケージZIPに一致することを確認。
- 通常の生成コマンドで、公開中の0.3.2の一覧と、公開済み0.3.2 / 0.3.3のZIPを取得し、生成成功を確認。
- dist/index.jsonの掲載IDがcom.baxter.material-override-vrmのみ、掲載版が0.3.2と0.3.3のみであることを確認。0.3.3のversion・配布URLと、index.html・.nojekyllの生成も確認。
- 0.3.3 ZIPのSHA-256: `865644a59795693eb07dbbcd3dfa222b9b8019d9da8f593e51eae622970765b2`。以前にローカル成果物と照合した値と一致。
- 0.3.3のGitHub Actions実行・Pages配信・VCC / ALCOMからの導入確認は、この差分の反映後に行う。

なお、公開v0.3.2タグのpackage.jsonは説明文のみ添付ZIPと異なります。ID・表示名・バージョン・依存設定は一致しており、一覧はZIP側の説明文を使用します。

### VRC 0.1.0掲載予定のローカル検証（2026-11-16）

source.jsonへVRC 0.1.0の配布予定URLを追加しました。タグは `0.1.0` です。VRCのURLに対するダウンロードだけをローカル生成ZIPへ差し替えたプレビューで、公開中の一覧と公開Core ZIPを引き継ぎ、Core 0.3.2 / 0.3.3とVRC 0.1.0のJSON・HTML生成を確認しました。VRCの配布URL・ZIPハッシュ・Core依存も確認し、unittest 11件も成功しています。

これは未公開ZIPを使うローカル検証であり、本番の404エラーを無視する処理は追加していません。公開予定URLからの実取得とPages配信は、VRCリリース公開後に確認してください。今回の差分はcommit/pushしていません。
