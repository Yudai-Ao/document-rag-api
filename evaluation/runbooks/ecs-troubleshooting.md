# Document RAG API — ECS障害対応Runbook

## 1. 目的

本Runbookは、Document RAG APIを稼働させているAmazon ECS / AWS Fargate環境で障害が発生した場合の初動確認および切り分け手順を定める。

対象となる主な事象は以下とする。

- ECSタスクが起動しない
- ECSタスクが予期せず停止する
- Application Load Balancerから502または503が返される
- Document RAG APIから503が返される
- AWSサービスへのアクセス時にAccessDeniedが発生する

---

## 2. システム基本情報

Document RAG APIの通常稼働時の構成は以下とする。

| 項目 | 設定値 |
|---|---|
| ECS Desired Task Count | 1 |
| Application Port | 8000 |
| ALB Health Check Path | `/health` |
| 正常時のHealth Check Response | `{"status":"ok"}` |
| CloudWatch Log Group | `/ecs/document-rag-api` |
| Application Runtime | AWS Fargate |
| Container Architecture | Linux / ARM64 |

通常時はECS Serviceに1つのRunning Taskが存在し、ALB Target GroupのTarget HealthがHealthyであること。

---

## 3. 障害対応の基本フロー

Document RAG APIで障害が発生した場合は、以下の順序で確認する。

1. ALB Target GroupのTarget Healthを確認する
2. ECS ServiceのRunning Task数を確認する
3. ECS Taskの状態およびStopped Reasonを確認する
4. CloudWatch Logsでアプリケーションログを確認する
5. AccessDeniedが記録されている場合はECS Task Roleを確認する

調査開始から15分以内に原因を特定できない場合は、クラウド基盤担当者へエスカレーションする。

---

## 4. ECSタスクが起動しない場合

ECS ServiceのDesired Task Countが1であるにもかかわらずRunning Taskが0の場合、停止済みTaskのStopped Reasonを確認する。

確認対象は以下とする。

- Essential container exited
- ResourceInitializationError
- CannotPullContainerError
- OutOfMemoryError
- コンテナ起動コマンドのエラー

コンテナが起動直後に停止している場合は、CloudWatch Logsの起動ログも確認する。

`exec format error` が記録されている場合は、Docker ImageのCPUアーキテクチャとECS Task DefinitionのRuntime Platformが一致しているか確認する。

Document RAG APIのECS TaskはLinux / ARM64を使用する。

---

## 5. ALBから502または503が返される場合

ALBから502または503が返される場合、最初にTarget GroupのTarget Healthを確認する。

TargetがUnhealthyの場合は、以下を確認する。

1. ECS TaskがRunningであること
2. Security GroupでALBからECSのApplication Port 8000への通信が許可されていること
3. Health Check Pathが `/health` であること
4. `/health` がHTTP 200を返すこと

Target Healthが3回連続でUnhealthyとなった場合は、CloudWatch Logsを確認してアプリケーション起動時のエラーを調査する。

---

## 6. APIが503を返す場合

ALB TargetがHealthyで、ECS TaskもRunningであるにもかかわらずDocument RAG APIが503を返す場合は、アプリケーション内部または依存AWSサービスの障害を疑う。

最初にCloudWatch Log Group `/ecs/document-rag-api` を確認する。

主な確認対象は以下とする。

- BedrockServiceError
- EmbeddingServiceError
- VectorStoreServiceError
- S3ServiceError
- AccessDeniedException

`/chat` のみ503となる場合は、Embedding、S3 Vectors、Amazon Bedrockの順にエラーの有無を確認する。

`GET /documents` が503となる場合は、Amazon S3へのアクセスエラーを確認する。

---

## 7. AccessDeniedが発生する場合

CloudWatch LogsにAccessDeniedExceptionが記録されている場合、ECS Task RoleのIAM Policyを確認する。

Document RAG APIでは、アプリケーションからAWSサービスへアクセスする権限はECS Task Execution RoleではなくECS Task Roleに付与する。

確認対象は以下とする。

- エラーに記録されているAction
- エラーに記録されているResource ARN
- ECS Task Roleに対象Actionが許可されているか
- IAM PolicyのResourceが対象リソースを含んでいるか

権限不足が確認された場合でも、原因調査担当者が独断でFull Access Policyを付与してはならない。

必要なActionおよびResourceを特定し、最小権限となるようIAM Policyの変更を申請する。

---

## 8. CloudWatch Logsの確認

アプリケーションログはCloudWatch Log Group `/ecs/document-rag-api` に出力される。

障害調査時は、ユーザーに返却されたHTTPステータスだけで原因を判断せず、対応する時間帯のCloudWatch Logsを確認する。

アプリケーションでは内部例外の詳細をAPIレスポンスへ直接返さず、以下のような汎用メッセージへ変換する。

```json
{
  "detail": "AI service is temporarily unavailable."
}
```

そのため、503の詳細原因を特定する場合はCloudWatch Logsのスタックトレースを確認する必要がある。

---

## 9. 復旧確認

原因への対応後は以下を確認する。

1. ECS TaskがRunningであること
2. ALB TargetがHealthyであること
3. `/health` がHTTP 200を返すこと
4. `GET /documents` が正常に実行できること
5. `POST /chat` が正常に回答を返すこと

IAM Policyを変更した場合は、変更対象となったAWSサービスを利用するAPIについても動作確認を実施する。

---

## 10. エスカレーション

以下のいずれかに該当する場合はクラウド基盤担当者へエスカレーションする。

- 調査開始から15分以内に原因を特定できない
- ECS Taskが繰り返し停止する
- 複数のAWSサービスで同時にエラーが発生している
- IAM Policy変更が必要
- AWSサービス自体の障害が疑われる

エスカレーション時には、以下の情報を共有する。

- 障害発生時刻
- 発生しているHTTPステータス
- ECS Taskの状態
- ALB Target Health
- CloudWatch Logsのエラー内容
- 実施済みの確認事項