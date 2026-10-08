# Phase 17 — Evidence-Aware RAG 実装・評価・振り返り

## 1. 目的とPhase 16からの接続

Phase 16では、5つの障害対応Runbook、34問（Answerable 24問、Unanswerable 10問）を用いてRetrievalを評価した。`chunk_size=500`、`chunk_overlap=100`、`top_k=3` のBaselineでは、期待文書のHit@3が100%、Top-1が91.67%だった。保存済みTop-3の検索順位を切り出すと、期待文書Hit@2も100%だったため、`top_k`を3から2へ変更した。

しかし、この指標は**期待するPDFが検索結果に含まれるか**を測るものであり、**取得チャンクに回答の根拠があるか**は保証しない。またPhase 16では、Answerableの平均Top-1 distanceが0.424、Unanswerableが0.620である一方、Unanswerableのdistanceが0.458となるケースもあり、距離の閾値だけで回答可能性を判定するのは難しいと分かった。

そこでPhase 17の目的を、**取得したEvidenceだけで質問に回答できるかを判定し、根拠が不足していれば回答生成を控えること**とした。

## 2. 仮説と設計

仮説：Vector検索の類似度だけでなく、検索結果の本文をLLMに読ませてEvidenceの十分性を判定すれば、根拠がない質問への不用意な回答を減らせる。

処理フロー：

```text
Question
  ↓
Embedding → S3 Vectors検索（Top-2）
  ↓
Evidence Gate（ClaudeによるSUFFICIENT / INSUFFICIENT判定）
  ├─ SUFFICIENT → Claudeで回答生成 → abstained=False
  └─ INSUFFICIENT → 「文書からは分かりません」 → abstained=True
```

`app/services/evidence.py` に `build_evidence_prompt()` と `has_sufficient_evidence()` を実装。`app/services/rag.py` にGateを組み込み、`abstained` フラグを返すようにした。検索結果が空の場合も回答生成せず `abstained=True` とする。Evidence判定のClaude呼び出しが増えるため、コスト・レイテンシへの影響は今後の評価対象である。

## 3. 実装過程で発見した課題

### 3.1 正解文書Hitと正解Evidence Hitは異なる

`ecs-001`（Application Portは何番か）では、Top-2にECSのPDFが含まれたにもかかわらず、そのチャンクには`8000`の記載がなく、Evidence Gateは回答保留した。Top-10の調査では、`Application Port: 8000`を含むALBチャンクがRank 3、ECSチャンクがRank 7に存在した。Top-1/2/3でGateを試すと `MISS / MISS / HIT` となった。

これはPhase 16の**期待文書Hit@2=100%**を、**回答根拠Hit@2=100%**と解釈してはいけないことを示す。

`ecs-003`（CPUアーキテクチャ）でも、Top-2にはECSのPDFが含まれるが、取得チャンクには`Linux / ARM64`がなく回答保留した。チャンクの境界や検索順位の問題は、別のPhaseで評価する。

### 3.2 Chunk-level評価の試作とスコープ管理

`ecs-001`に一時的に`expected_evidence`を付与し、グループ内AND・グループ間ORの文字列一致評価を試作。Top-1/2/3が `MISS / MISS / HIT` となり、AND/ORのpytestも通過した。

ただし、24問すべてに根拠注釈を付ける作業はPhase 17の本来の目的を超えるため、**Chunk-level Retrieval評価を独立したPhase 18に移管**した。評価用の試作コードは今後の再利用候補とし、通常の評価Datasetは従来の構造に戻す方針とした。

### 3.3 設定の不一致

`config.py`のデフォルト`top_k=2`に対し、`.env`が`TOP_K=3`のままで、Swagger APIでは3件の`source`が返っていた。`.env`を2に修正し、実行時の値と取得件数が2であることを確認した。

教訓：実験では**コード上のデフォルト値ではなく、実行時に有効な設定値**を記録する。

### 3.4 `abstained`フラグの不整合

当初は回答文の「分かりません／わかりません」を正規化して回答保留を推定していたが、表記揺れに依存するため、RAGから明示的に`abstained`を返す方式へ変更した。変更時に回答生成後の経路まで`abstained=True`となってしまい、初回34問評価では24/24 Answerableと10/10 Unanswerableが保留と集計された。

実際には回答が生成されていたケースがあり、`rag.py`の最後の返却値を`False`に修正。テストのモックデータにも`abstained`を追加した。初回結果はフラグ不整合のため正式な評価値として使用しない。

### 3.5 Bedrock Throttlingと評価の再開

修正後の34問再評価は`alb-003`で`ThrottlingException`により停止した。Evidence Gate導入後は回答可能な質問でClaude呼び出しが増える。評価スクリプトに、質問間の待機（初期値5秒）、1問ごとの原子的な途中保存、`--resume`による再開を追加した。待機時間だけでThrottlingを完全に防げるわけではない。

## 4. 最終評価結果（evidence_gate_v3.json）

- 評価件数：34問（Answerable 24、Unanswerable 10）
- Answerable Pass Rate：20/24 = **83.33%**
- Unanswerable Abstention Rate：10/10 = **100%**
- Answerable False Negative Rate：4/24 = **16.67%**

上記は**Gateが回答生成を許可／保留した割合**であり、生成回答の正確性・Faithfulnessを示すものではない。また、34問という小規模な評価セット上の観測結果であり、一般的な性能を保証しない。

### 回答可能だが保留された4問

| ID | カテゴリ | 質問（要旨） |
|---|---|---|
| ecs-001 | direct | Application Portは何番か |
| ecs-002 | direct | 何分以内に原因特定できなければエスカレーションするか |
| ecs-003 | direct | ECS TaskのCPUアーキテクチャは何か |
| alb-004 | multi_step | ECS Running・/health正常・/chatが503の場合、ALB調査を続けるべきか |

`ecs-001`、`ecs-002`、`ecs-003`は確認したTop-2チャンクに必要な直接根拠がなかった。`alb-004`はまだ原因を切り分けていないため、Retrieval不足かGate判定の問題かを断定しない。

## 5. Phase 16との比較で分かったこと

- Phase 16：期待する**文書**を取得できるかを定量評価し、Top-2で24/24の文書Hitを確認した。
- Phase 17：取得した**チャンクの本文**に回答根拠があるかを判定する仕組みを追加した。
- 結果：Unanswerable 10問すべてで回答保留したが、Answerable 4問も保留した。
- 解釈：文書Hit率だけでは回答可能率を説明できない。検索の根拠充足とGateの判定品質を分けて評価する必要がある。

**Phase 16での`top_k=2`の採用は、文書Hit率に基づく暫定的な最適化だった。Phase 17の結果によって、その限界が明確になった。**

## 6. 採用・保留した判断

**採用**：Evidence Gateによる回答生成の制御、`abstained`明示フラグ、実行時`top_k=2`の統一、評価結果の別名保存・途中保存・再開。

**保留**：全24問へのEvidence注釈付け、Chunk-level Hit@Kの本格評価、LLM-as-a-JudgeによるCorrectness/Faithfulness評価、Adaptive Retrieval（GateがFalseならTop-Kを段階的に増やす）。これらは中止ではなく、専用Phaseで扱う。

## 7. 次のPhaseへ引き継ぐ課題

### Phase 18：Chunk-level Retrieval評価

回答保留となった4問を優先的に調査し、期待文書Hitと正解Evidence Hitの差を測定する。特に`alb-004`の原因は未確定。必要な根拠がどの順位のチャンクに現れるかを確認し、`top_k=2`の妥当性を再評価する。

### Phase 19：LLM-as-a-Judge・回答品質評価

Gate通過後に生成された20問の回答について、Correctness・Faithfulness等を評価する。Gateの通過率と生成回答の品質を混同しない。

### Phase 20：評価結果に基づくRAG改善

固定Top-2／固定Top-3／Adaptive Retrievalなどを比較し、回答可能率、誤回答率、コスト、レイテンシのトレードオフを検証する。

## 8. 開発方針としての学び

新たな課題が見つかっても、現在のPhaseを無制限に拡張しない。現Phaseの目的達成を阻むクリティカルな不具合は修正し、それ以外の重要な改善・評価は独立した後続Phaseに分離する。各Phaseで、**仮説 → 実装 → 観測 → 原因の切り分け → 採用／保留の判断 → 次Phaseへの引き継ぎ**を記録する。

---

### 実行・参照コマンド

```bash
uv run pytest -v
uv run python -m evaluation.evaluate --output evidence_gate_v3.json --delay 5
# 途中停止後、同一条件で再開する場合
uv run python -m evaluation.evaluate --output evidence_gate_v3.json --delay 10 --resume
jq 'length' evaluation/results/evidence_gate_v3.json
```

記録対象：`app/services/evidence.py`、`app/services/rag.py`、`evaluation/evaluate.py`、`evaluation/results/evidence_gate_v3.json`、Phase 16の振り返りMD。
