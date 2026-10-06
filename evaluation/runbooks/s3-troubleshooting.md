# Document RAG API — Amazon S3障害対応Runbook

## 1. 目的

本Runbookは、Document RAG APIが文書ストレージとして利用するAmazon S3で障害またはデータ不整合が発生した場合の確認および切り分け手順を定める。

対象となる主な事象は以下とする。

- PDFのアップロードに失敗する
- 登録済み文書を取得できない
- 文書の削除に失敗する
- S3上のPDFとDocument Metadataに不整合が発生する
- S3とS3 Vectorsの登録状態に不整合が発生する
- S3アクセス時にAccessDeniedが発生する

---

## 2. Document RAG APIにおけるS3の役割

Document RAG APIでは、Amazon S3を文書データの永続ストレージとして使用する。

S3には主に以下を保存する。

- アップロードされたPDFファイル
- Document Metadata
- document_id
- filename
- chunk_count

一方、Embeddingおよびチャンク検索用VectorはAmazon S3 Vectorsへ保存する。

そのため、Document RAG APIではAmazon S3とAmazon S3 Vectorsを別のストレージとして扱う。

---

## 3. 文書登録の基本フロー

PDF登録時の基本処理は以下とする。

1. PDFを受信する
2. document_idを生成する
3. PDFからテキストを抽出する
4. テキストをチャンクへ分割する
5. Embeddingを生成する
6. PDFをAmazon S3へ保存する
7. Document MetadataをAmazon S3へ保存する
8. チャンクとEmbeddingをAmazon S3 Vectorsへ保存する

Document Metadataには、少なくとも以下を記録する。

- document_id
- filename
- chunk_count

登録処理の途中で失敗した場合は、S3とS3 Vectorsの登録状態が一致しているか確認する。

---

## 4. PDFアップロードに失敗する場合

PDFの保存時にエラーが発生した場合は、CloudWatch LogsでS3関連エラーを確認する。

主な確認項目は以下とする。

- 対象S3 Bucketが存在すること
- アプリケーションが正しいBucket名を参照していること
- ECS Task Roleに `s3:PutObject` が許可されていること
- IAM PolicyのResourceが対象Objectを含んでいること

AccessDeniedが発生している場合は、S3設定だけでなくECS Task RoleのIAM Policyも確認する。

---

## 5. 登録済み文書を取得できない場合

Document Metadata上では文書が存在するにもかかわらずPDFを取得できない場合は、以下を確認する。

1. S3上に対象PDF Objectが存在すること
2. document_idと保存先Object Keyの対応が正しいこと
3. ECS Task Roleに `s3:GetObject` が許可されていること
4. IAM PolicyのResourceが対象Objectを含んでいること

Document Metadataのみ存在し、PDF Objectが存在しない状態はデータ不整合として扱う。

---

## 6. 文書削除に失敗する場合

文書削除では、対象文書に関連するデータを複数ストレージから削除する必要がある。

削除対象は以下とする。

- Amazon S3上のPDF
- Amazon S3上のDocument Metadata
- Amazon S3 Vectors上の対象文書のVector

削除後は、対象document_idに紐づくデータが各ストレージに残っていないことを確認する。

S3のDocument Metadataのみ削除し、S3 Vectors上のVectorが残った状態を「孤児Vector」とする。

孤児Vectorは全文書横断検索時に検索対象となり、削除済み文書がRAGの回答根拠として利用される可能性がある。

---

## 7. S3とS3 Vectorsのデータ不整合

全文書横断検索を行う場合、Amazon S3上のDocument MetadataとAmazon S3 Vectors上のVectorが整合している必要がある。

例えば、Document Metadata上では2文書のみ存在するにもかかわらず、S3 Vectors Indexに過去の文書Vectorが残っている場合は不整合と判断する。

確認時は以下を比較する。

- S3に登録されているdocument_id
- 各Document Metadataのchunk_count
- S3 Vectorsに存在するVector Key
- Vector Metadata内のdocument_id
- Vector Metadata内のsource
- Vector Metadata内のchunk_index

各文書について、S3 Vectors上のVector数とDocument Metadataのchunk_countが一致することを確認する。

---

## 8. 孤児Vectorが発生した場合

孤児Vectorが確認された場合は、まず削除対象を特定する。

現在有効なdocument_idに紐づくVectorは削除してはならない。

削除対象を特定した後、不要なVectorのみS3 Vectorsから削除する。

削除後は再度Vector一覧を取得し、以下を確認する。

1. 不要なVectorが存在しない
2. 有効なdocument_idのVectorが残っている
3. 各文書のVector数がchunk_countと一致する
4. Vector Metadataに必要な項目が存在する

データ不整合を隠す目的で、欠落したMetadataへデフォルト値を設定して処理を継続してはならない。

---

## 9. AccessDeniedが発生する場合

S3操作でAccessDeniedが発生した場合は、CloudWatch Logsから拒否されたActionとResourceを確認する。

Document RAG APIで主に利用するS3 Actionは以下とする。

- `s3:PutObject`
- `s3:GetObject`
- `s3:DeleteObject`
- `s3:ListBucket`

Object操作とBucket操作では対象Resourceが異なるため注意する。

IAM Policyの詳細な切り分けについてはIAM AccessDenied障害対応Runbookを参照する。

---

## 10. 復旧確認

S3関連の障害対応後は以下を確認する。

1. PDFを正常にアップロードできる
2. Document Metadataを取得できる
3. 登録済み文書を正常に取得できる
4. RAG検索が正常に実行できる
5. 文書削除後に関連データが残っていない
6. S3とS3 Vectorsのdocument_idおよび件数が整合している

データ不整合を修正した場合は、単一文書検索だけでなく全文書横断検索も実行し、削除済み文書が検索結果へ含まれないことを確認する。

---

## 11. エスカレーション

以下の場合はクラウド基盤担当者へエスカレーションする。

- S3上のデータ欠損が発生している
- 削除対象のVectorを安全に特定できない
- S3とS3 Vectorsの不整合原因を特定できない
- IAM Policy上は許可されているにもかかわらずS3へアクセスできない
- 複数文書で継続的にデータ不整合が発生する

エスカレーション時には以下を共有する。

- document_id
- filename
- S3 Objectの状態
- Document Metadata
- chunk_count
- S3 Vectors上のVector数
- CloudWatch Logsの関連エラー
- 実施済みの確認および復旧作業