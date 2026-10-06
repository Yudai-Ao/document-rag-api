# Phase 16 — RAG Retrieval Evaluation & Improvement

## 1. 目的

Phase 16では、Document RAG APIのRetrieval性能を定量的に評価し、評価結果に基づいてRAG設定を改善する。

単純にパラメータを変更するのではなく、以下のサイクルで検証を行う。

1. Baselineを計測する
2. 問題単位で失敗ケースを確認する
3. カテゴリ別に性能を分析する
4. 改善仮説を立てる
5. 必要な実験のみ実施する
6. 結果から設定変更の要否を判断する

---

# 2. Baseline

Phase 15で以下の評価環境を構築した。

## Evaluation Dataset

- Runbooks: 5
  - ECS
  - ALB
  - IAM
  - S3
  - Amazon Bedrock
- Evaluation Cases: 34
  - Answerable: 24
  - Unanswerable: 10
- S3 Vectors: 44

質問は以下のカテゴリに分類している。

- direct
- paraphrase
- multi_step
- unanswerable

## Initial Retrieval Configuration

```text
chunk_size     = 500
chunk_overlap  = 100
top_k          = 3
```

## Baseline Metrics

```text
Expected Source Hit@3       100.00%
Expected Source Top-1        91.67%

Answerable Avg Distance       0.424
Unanswerable Avg Distance     0.620
```

---

# 3. Top-1 Retrieval Failure Analysis

Answerable 24問のうち、Expected SourceがTop-1にならなかった質問は2問だった。

## ecs-001

Question:

```text
Document RAG APIのApplication Portは何番ですか？
```

Retrieval Result:

```text
1. bedrock-troubleshooting.pdf  0.615
2. ecs-troubleshooting.pdf      0.626
3. alb-troubleshooting.pdf      0.640
```

Expected Sources:

```text
ecs-troubleshooting.pdf
alb-troubleshooting.pdf
```

Expected SourceはTop-2およびTop-3に存在している。

---

## ecs-007

Question:

```text
ECS TaskはRunningでALB TargetもHealthyですが、
POST /chatだけが503になります。
どのように切り分けますか？
```

Retrieval Result:

```text
1. alb-troubleshooting.pdf  0.360
2. ecs-troubleshooting.pdf  0.361
3. alb-troubleshooting.pdf  0.396
```

Expected Source:

```text
ecs-troubleshooting.pdf
```

Top-1とTop-2のdistance差はわずか0.001だった。

### 考察

これらはRetrievalそのものに失敗しているというより、複数Runbookに類似した情報が存在するため、文書間で順位が入れ替わっていると考えられる。

Expected Sourceは全AnswerableケースでTop-3以内に存在している。

---

# 4. Category Analysis

質問カテゴリ別にRetrieval性能を分析した。

| Category | Cases | Hit Rate | Top-1 Rate | Avg Top-1 Distance |
|---|---:|---:|---:|---:|
| direct | 7 | 100.00% | 85.71% | 0.445 |
| paraphrase | 11 | 100.00% | 100.00% | 0.454 |
| multi_step | 6 | 100.00% | 83.33% | 0.346 |
| unanswerable | 10 | - | - | 0.620 |

## Initial Hypothesis

当初は、複数条件を含む `multi_step` 質問ほどRetrievalが難しくなると予想した。

## Result

実際には `multi_step` の平均Top-1 Distanceが最も小さかった。

```text
direct       0.445
paraphrase   0.454
multi_step   0.346
```

## Interpretation

Multi-step質問には、

- ECS
- ALB
- `/chat`
- 503

など障害状況を表す具体的な情報が複数含まれる。

そのため、関連チャンクとの意味的類似度が高くなった可能性がある。

### Decision

全AnswerableカテゴリでHit Rateが100%だったため、カテゴリ固有のRetrieval改善は実施しない。

---

# 5. Top-K Evaluation

## Initial Plan

当初は以下を比較する予定だった。

```text
top_k = 1
top_k = 3
top_k = 5
```

しかしBaselineですでに `top_k=3` のHit Rateが100%だった。

そのため `top_k=5` に増加してもRecallを改善できず、以下のデメリットだけが増える可能性がある。

- Context増加
- Prompt Token増加
- Bedrock入力コスト増加
- 無関係なEvidence混入

そこで実験目的を、

> Retrieval性能を維持したままContext数を削減できるか

に変更した。

比較対象を以下へ変更した。

```text
top_k = 1
top_k = 2
top_k = 3
```

## Evaluation Method

BaselineではTop-3の検索結果を順位付きで保存している。

そのためVector Searchを再実行せず、保存済み結果から、

```text
Top-1 → sources[:1]
Top-2 → sources[:2]
Top-3 → sources[:3]
```

としてHit Rateを再計算した。

これにより追加のEmbedding生成・S3 Vectors検索・Claude呼び出しは行っていない。

## Result

```text
Top-1    22 / 24     91.67%
Top-2    24 / 24    100.00%
Top-3    24 / 24    100.00%
```

## Decision

Retrieval観点では `top_k=2` が最小十分値と判断した。

```text
top_k: 3 → 2
```

へ変更した。

変更後、既存pytestがすべてPASSすることを確認した。

---

# 6. chunk_size Evaluation

当初は以下のような比較を検討していた。

```text
300
500
700
```

しかし現在の `chunk_size=500` で、

```text
Hit@2 = 100%

Direct       Hit Rate = 100%
Paraphrase   Hit Rate = 100%
Multi-step   Hit Rate = 100%
```

となっている。

つまり、chunk_sizeが原因で必要なEvidenceを取得できない問題は観測されていない。

### Decision

改善対象が存在しない状態でのパラメータ探索は行わず、

```text
chunk_size = 500
```

を維持する。

今後以下の問題が観測された場合に再検討する。

- 必要なEvidenceが取得できない
- 1チャンクが大きすぎてノイズが増える
- 回答に必要な情報が複数チャンクへ過度に分散する

---

# 7. chunk_overlap Evaluation

現在の設定は、

```text
chunk_overlap = 100
```

である。

Overlapはチャンク境界で重要情報が分断されることを防ぐ目的で使用する。

しかし今回の評価では、

> チャンク境界によるEvidence欠落

は観測されなかった。

### Decision

目的のないパラメータ探索は行わず、

```text
chunk_overlap = 100
```

を維持する。

---

# 8. Unanswerable Analysis

Phase 16で最も重要だった発見はUnanswerable質問の分析だった。

## Unanswerable Top-1 Distance

```text
ECS vCPU                 0.458
S3 Versioning            0.482
S3 Lifecycle             0.552
IAM MFA                  0.572
Claude Context Length    0.590
ALB TLS Certificate      0.656
S3 Backup Retention      0.691
IAM Password Rotation    0.721
Claude Pricing           0.735
RDS CPU                  0.744
```

平均値では、

```text
Answerable Avg Distance      0.424
Unanswerable Avg Distance    0.620
```

と差が存在する。

しかし個別ケースでは分布が重なっている。

例えば、

```text
Unanswerable
ECS vCPU            0.458

Answerable
ecs-001             0.615
```

となっている。

つまり、

```text
Vector Distanceが近い
        ≠
Evidenceに質問への答えが存在する
```

ことが分かった。

## Example

Question:

```text
Document RAG APIのS3バケットでは
Versioningを有効にしていますか？
```

S3 Runbookは意味的には非常に近いため、Vector Searchでは近いチャンクが取得される。

しかしRunbookにはVersioningの設定有無は記載されていない。

そのためDistanceだけでは、

> 回答可能かどうか

を判断できない。

---

# 9. Distance Threshold Hypothesis

当初は、

```text
distance > threshold
→ Evidence不足
→ Abstain
```

という単純なEvidence Gateも候補として考えた。

しかし、

```text
Unanswerable  0.458
Answerable    0.615
```

という逆転ケースが存在した。

### Decision

単純なVector Distance thresholdのみを使用したEvidence Gateは採用しない。

Evidenceそのものに質問への回答根拠が含まれているかを評価する必要がある。

この課題はPhase 17 `Evidence-Aware RAG` で扱う。

---

# 10. Final Retrieval Configuration

Phase 16終了時点のRetrieval設定は以下とする。

## Before

```text
chunk_size       = 500
chunk_overlap    = 100
top_k            = 3
```

## After

```text
chunk_size       = 500
chunk_overlap    = 100
top_k            = 2
```

変更したパラメータは `top_k` のみである。

---

# 11. Rejected / Skipped Approaches

Phase 16では以下を意図的に採用しなかった。

## top_k = 5

理由:

`top_k=3`ですでにHit Rateが100%であり、Recall改善余地がなかった。

---

## chunk_size tuning

理由:

現行設定でRetrieval上の問題が観測されなかった。

---

## chunk_overlap tuning

理由:

チャンク境界によるEvidence欠落が観測されなかった。

---

## Distance-only Evidence Gate

理由:

Answerable / UnanswerableのDistance分布が重複していた。

---

# 12. Phase 16で得られた知見

Phase 16開始時点では、

> RAG性能を改善するためにはRetrievalパラメータのチューニングが必要

と考えていた。

しかし評価を進めた結果、Retrieval性能はすでに高く、

```text
Hit@2 = 100%
```

であることが分かった。

一方で、本質的な課題として、

> 類似したEvidenceを取得できることと、
> そのEvidenceに質問への答えが存在することは別

という問題が明確になった。

そのため、次の改善対象はRetrievalパラメータではなく、

> Evidenceの十分性を判断する仕組み

であると判断した。

---

# 13. Next Phase

次のPhaseでは `Evidence-Aware RAG` を実装する。

```text
Question
    ↓
Retrieval
    ↓
Top-2 Evidence
    ↓
Evidence Sufficiency Check
    ↓
┌─────────────┬─────────────┐
│ sufficient  │ insufficient│
↓             ↓
Generate      Abstain
Answer        「文書からは分かりません」
```

主な検討対象は以下とする。

- Evidence Sufficiency
- LLM-as-a-Judge
- Correctness
- Faithfulness
- Evidence Gate
- Abstention
- Distanceを補助指標として利用できるか

Phase 16で確認したHard Negativeを利用し、Evidenceに回答根拠が存在しない場合に適切に回答を控えられるRAGを目指す。