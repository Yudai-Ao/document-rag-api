# Document RAG API — Amazon Bedrock障害対応Runbook

## 1. 目的

本Runbookは、Document RAG APIからAmazon Bedrockを利用する際に発生する障害の確認および切り分け手順を定める。

対象となる主な事象は以下とする。

- `/chat` が503を返す
- Embedding生成に失敗する
- Claudeによる回答生成に失敗する
- Bedrock呼び出し時にAccessDeniedが発生する
- Model IDまたはInference Profileの設定に問題がある
- 利用できないモデルを指定している

---

## 2. Document RAG APIにおけるBedrockの役割

Document RAG APIでは、Amazon Bedrockを以下の2つの処理で利用する。

### Embedding生成

Amazon Titan Text Embeddings V2を利用する。

テキストをVectorへ変換し、S3 Vectorsへの保存および類似検索に利用する。

Embedding生成ではBedrock Runtimeの `InvokeModel` APIを使用する。

### 回答生成

Claude Sonnet 4.6を利用する。

S3 Vectorsから取得した参考文書とユーザーの質問を入力として、RAG回答を生成する。

回答生成ではBedrock Runtimeの `Converse` APIを使用する。

Embedding生成と回答生成は異なるモデルおよび処理であるため、Bedrock障害時はどちらで失敗しているかを切り分ける。

---

## 3. /chat の処理フロー

`POST /chat` の主な処理フローは以下とする。

1. ユーザーから質問を受信する
2. Titan Text Embeddings V2で質問のEmbeddingを生成する
3. S3 Vectorsで関連チャンクを検索する
4. 検索結果からPromptを構築する
5. Claude Sonnet 4.6へPromptを送信する
6. 生成された回答をユーザーへ返す

したがって `/chat` が503を返す場合、BedrockだけでなくEmbedding、S3 Vectors、回答生成のどの段階で失敗しているかをCloudWatch Logsから確認する。

---

## 4. Embedding生成に失敗する場合

Embedding生成に失敗した場合は、CloudWatch Logsで `EmbeddingServiceError` およびその原因となるBedrockエラーを確認する。

主な確認項目は以下とする。

- Embedding Model IDが正しいこと
- AWS Regionが正しいこと
- ECS Task Roleに `bedrock:InvokeModel` が許可されていること
- 対象Foundation Modelへアクセス可能であること

Document RAG APIではEmbedding ModelとしてAmazon Titan Text Embeddings V2を利用する。

Embedding生成に失敗すると質問Vectorを作成できないため、S3 Vectorsによる検索処理へ進むことができない。

---

## 5. Claudeによる回答生成に失敗する場合

S3 Vectorsによる検索が成功しているにもかかわらず回答生成に失敗する場合は、Claude呼び出しを確認する。

CloudWatch Logsで `BedrockServiceError` およびBedrock Runtimeから返されたエラーを確認する。

主な確認項目は以下とする。

- ClaudeのModel IDまたはInference Profile ID
- AWS Region
- `bedrock:InvokeModel` 権限
- Inference Profileの状態
- 対象Foundation Modelが利用可能であること

検索結果が取得できている場合、Embedding生成とS3 Vectors検索は成功しているため、回答生成側へ調査対象を絞ることができる。

---

## 6. Inference Profileを利用する場合

Document RAG APIのClaude Sonnet 4.6呼び出しではInference Profileを利用する。

Inference Profileを使用する場合は、設定されているInference Profile IDが正しいことを確認する。

また、Inference Profileが `ACTIVE` であることを確認する。

Inference Profileは複数RegionのFoundation Modelへリクエストをルーティングする場合がある。

そのため、IAM Policyを確認する際はInference Profileだけでなく、Profileが利用するFoundation Modelへのアクセスも考慮する。

---

## 7. Model IDに問題がある場合

Bedrockで指定するModel IDが誤っている場合、モデル呼び出しに失敗する。

障害発生時はアプリケーション設定のModel IDと、Bedrockで現在利用可能なModel IDが一致していることを確認する。

Embeddingと回答生成では異なるModel IDを使用するため、どちらの設定値に問題があるかを切り分ける。

Document RAG APIでは以下を利用する。

- Embedding: Amazon Titan Text Embeddings V2
- Answer Generation: Claude Sonnet 4.6

Model IDを変更した場合は、アプリケーション設定だけでなく、必要に応じてIAM PolicyのResourceも確認する。

---

## 8. 利用できないモデルを指定している場合

過去に利用できたModel IDであっても、現在利用可能とは限らない。

ResourceNotFoundなどモデル利用に関連するエラーが発生した場合は、指定したモデルが対象Regionで現在利用可能か確認する。

利用できないモデルを指定している場合は、現在利用可能なモデルへ変更する。

モデルを変更した後は、以下を確認する。

1. Model IDが正しい
2. 対象Regionで利用可能
3. IAM Policyが対象モデルを許可している
4. Bedrock Runtimeから正常にレスポンスを取得できる

---

## 9. AccessDeniedが発生する場合

Bedrock呼び出しでAccessDeniedが発生した場合は、CloudWatch Logsから拒否されたActionおよびResourceを確認する。

Document RAG APIでBedrockモデルを呼び出す際の主なActionは以下とする。

- `bedrock:InvokeModel`

アプリケーションからBedrockを呼び出す権限はECS Task Roleへ付与する。

Task Execution RoleへBedrock呼び出し権限を追加して解決してはならない。

IAM Policyの詳細な切り分けについてはIAM AccessDenied障害対応Runbookを参照する。

---

## 10. 503発生時の切り分け

`POST /chat` が503を返す場合は、CloudWatch Logsを確認して処理のどの段階で失敗しているかを判断する。

### EmbeddingServiceErrorの場合

Embedding生成処理を調査する。

Titan Text Embeddings V2のModel ID、Region、IAM権限を確認する。

### VectorStoreServiceErrorの場合

S3 Vectorsの検索処理を調査する。

Bedrockの回答生成より前の処理で失敗しているため、Claude側の障害として扱わない。

### BedrockServiceErrorの場合

S3 Vectors検索後のClaude回答生成処理を調査する。

ClaudeのModel ID、Inference Profile、