# baxter's VPM Packages

BaxterのVMagicMirror関連ツール用VPM一覧。

- ID: `io.github.baxter.vpm`
- 配信予定: https://malaybaku.github.io/baku-vpm/index.json
- 作者: Baxter（メールアドレスは掲載しません）

## 公開準備

この作業フォルダではコミット・pushを行わず、差分のみ作成します。

1. パッケージ本体と依存先のVPM導入経路を整備し、公開前テストを完了する。
2. パッケージ本体の配布用Git履歴を別作業で整理する。
3. パッケージ本体の手動Build Draft Releaseを実行し、ZIP内のpackage.jsonと内容を確認する。
4. 本体のGitHub Releaseを公開し、source.jsonのZIP URLが実際に取得できることを確認する。
5. このリポジトリのSettings → Pages → SourceをGitHub Actionsに設定する。
6. 変更をレビューしてcommit/pushし、Build Repo Listingの成功を確認する。
7. ローカル参照のないVCC / ALCOMプロジェクトで一覧追加から導入・更新を検証する。

現在source.jsonに記載した0.1.0のURLは公開予定値です。未公開の間は一覧ビルドの成功を期待できません。公開版番号が変わる場合はZIP URLも変更します。

## バージョン追加

source.jsonのpackages[].releasesに公開済みZIPのURLを追加し、Build Repo Listingを実行します。過去バージョンのURLは削除しません。本体のリリース公開だけでは別リポジトリの一覧は更新されません。

作者の表示名とIDはBaxterで統一します。GitHubアカウント名はURL内のみで使用します。

## 依存関係の未完了項目

MaterialOverrideVrm v0.3.0の既存リリースはUnityプロジェクトZIP、UniVRM v0.131.4はunitypackageであり、そのままVPMの依存として自動取得できる形ではありません。基盤パッケージのVPM化とUniVRMの導入方式を別途整える必要があります。現時点では新規環境での自動導入完了を保証しません。

## 構成の出典

一覧ビルドはVRChat公式テンプレートのworkflowを基にしています。
https://github.com/vrchat-community/template-package-listing
