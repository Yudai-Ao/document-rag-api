# Document RAG API — ALB障害対応Runbook

## 1. 目的

本Runbookは、Document RAG APIで使用するApplication Load Balancer（ALB）およびTarget Groupに関連する障害が発生した場合の初動確認と切り分け手順を定める。

対象となる主な事象は以下とする。

- ALBから502 Bad Gatewayが返される
- ALBから503 Service Unavailableが返される
- Target GroupのTargetがUnhealthyになる
- Health Checkが失敗する
- ALBからECS Taskへ通信できない

---

## 2. システム基本情報

Document RAG APIのALB構成は以下とする。

| 項目 | 設定値 |
|---|---|
| ALB Listener Protocol | HTTP |
| ALB Listener Port | 80 |
| Target Group Protocol | HTTP |
| Target Group Port | 8000 |
| Target Type | IP |
| Health Check Path | `/health` |
| Application Port | 8000 |
| Healthy Response Code | 200 |

ALBはインターネットからHTTP 80番ポートでリクエストを受信し、Target Groupを経由してECS Taskの8000番ポートへ転送する。

---

## 3. ALB障害対応の基本フロー

ALB経由でDocument RAG APIへアクセスできない場合は、以下の順序で確認する。

1. ALB Listenerの状態を確認する
2. Target GroupのTarget Healthを確認する
3. ECS TaskがRunningであることを確認する
4. Security Groupの通信許可を確認する
5. Health Checkの設定を確認する
6. CloudWatch Logsでアプリケーションログを確認する

TargetがHealthyであるにもかかわらずAPIがエラーを返す場合は、ALBよりもアプリケーションまたは依存AWSサービスの障害を疑う。

---

## 4. 502 Bad Gatewayが返される場合

ALBから502 Bad Gatewayが返される場合は、ALBがTargetから正常なHTTPレスポンスを受信できていない可能性がある。

最初にTarget GroupのTarget Healthを確認する。

次に以下を確認する。

- ECS TaskがRunningであること
- FastAPIがApplication Port 8000で待ち受けていること
- Target GroupのPortが8000であること
- コンテナが異常終了していないこと
- CloudWatch Logsにアプリケーションエラーが記録されていないこと

Target GroupとECS Application Portが一致していない場合は、ポート設定を確認する。

---

## 5. 503 Service Unavailableが返される場合

ALBから503 Service Unavailableが返される場合は、Target Groupにリクエストを処理できるHealthy Targetが存在するか確認する。

TargetがUnhealthyの場合は、ECS Taskの状態とHealth Checkを確認する。

一方、TargetがHealthyであるにもかかわらずDocument RAG API自身が503を返している場合は、アプリケーション内部の障害である可能性が高い。

この場合はCloudWatch Logsを確認し、Bedrock、S3、S3 Vectorsなどの依存サービスでエラーが発生していないか確認する。

---

## 6. TargetがUnhealthyの場合

Target GroupのTargetがUnhealthyの場合は、以下を確認する。

1. ECS TaskがRunningであること
2. Health Check Pathが `/health` であること
3. `/health` がHTTP 200を返すこと
4. Target Group Portが8000であること
5. ECS Security GroupがALBから8000番ポートへの通信を許可していること

Health Checkの設定が正しくてもUnhealthyが継続する場合は、CloudWatch LogsでFastAPIの起動状態を確認する。

---

## 7. Security Groupの確認

Document RAG APIでは、ALBとECSで異なるSecurity Groupを使用する。

ALB Security GroupはインターネットからHTTP 80番ポートへの通信を許可する。

ECS Security GroupはApplication Port 8000への通信を許可するが、SourceはALB Security Groupのみに限定する。

ECS Security Groupで8000番ポートを `0.0.0.0/0` へ公開してはならない。

正常な通信経路は以下とする。

Internet → ALB:80 → ECS:8000

---

## 8. Health Checkの確認

ALBは `/health` を使用してDocument RAG APIの稼働状態を確認する。

正常時には以下のレスポンスをHTTP 200で返す。

```json
{
  "status": "ok"
}
```

Health Checkが失敗する場合は以下を確認する。

- Health Check Pathが `/health` であること
- FastAPIが起動していること
- ECS Taskが8000番ポートで待ち受けていること
- ALBからECSへの通信がSecurity Groupで許可されていること

`/health` が正常でも `/chat` や `/documents` が503を返す場合は、ALB障害ではなくアプリケーションまたは依存サービスの障害として切り分ける。

---

## 9. 復旧確認

設定変更または障害対応後は以下を確認する。

1. ECS TaskがRunningであること
2. Target GroupのTargetがHealthyであること
3. `/health` がHTTP 200を返すこと
4. ALB経由でSwagger UIへアクセスできること
5. Document RAG APIの主要APIが正常に実行できること

TargetがHealthyになっただけで復旧完了とは判断せず、実際のAPIリクエストまで確認する。

---

## 10. エスカレーション

以下の場合はクラウド基盤担当者へエスカレーションする。

- Targetが継続してUnhealthyになる
- ALB ListenerまたはTarget Groupの設定変更が必要
- Security Groupの変更が必要
- ECS Taskが正常にもかかわらずALB経由で通信できない
- 原因を15分以内に特定できない

エスカレーション時には以下を共有する。

- 発生しているHTTPステータス
- Target Health
- ECS Taskの状態
- Health Checkの結果
- Security Groupの確認結果
- CloudWatch Logsの関連エラー
- 実施済みの切り分け