# Phase 18：Chunk-level Retrieval評価・改善

## 1. 目的とスコープ

Phase 17でEvidence Gateを導入した結果、回答可能な24問のうち4問が回答保留となった。本Phaseでは、回答根拠の検索漏れが原因となったケースを調査し、最小限の設定変更で改善できるか検証する。

対象は **Retrievalの根拠取得とTop-Kの改善**。チャンクサイズ・オーバーラップの変更、Adaptive Retrievalの実装、回答品質の詳細なLLM-as-a-Judge評価は行わない。

## 2. Phase 16・17からの接続

- **Phase 16：Retrieval評価** — 正解文書がTop-2以内に含まれる割合（Expected Document Hit@2）が24/24＝100%となり、`top_k=2` を採用した。ただし、文書名の一致は回答に必要な**チャンク本文**の取得を保証しない。
- **Phase 17：Evidence-Aware RAG** — 検索したチャンク本文だけで回答できるかをEvidence Gateで判定し、根拠不足時には回答保留する仕組みを実装。Top-2・34問評価では、Answerable 24問中4問が保留、Unanswerable 10問中10問が保留となった。
- **Phase 18：原因分析と改善** — 保留された4問の実際の検索チャンクを調査し、正解文書の取得（Document Hit）と正解根拠の取得（Evidence Hit）が異なることを具体的に確認した。

## 3. 課題と仮説

**課題：** `top_k=2` では、正解文書に該当するチャンクが含まれていても、回答に必要な情報を含むチャンクが検索範囲外となる場合がある。

**仮説：** 回答根拠がRank 3にあるケースでは、`top_k=3` とすることで回答可能な質問の過剰な保留を減らせる。一方、検索候補が増えることでUnanswerableに誤って回答する副作用がないか、34問で検証する必要がある。

## 4. 失敗4問の分析

| ID | 質問概要 | Top-2の状況 | 分類・発見 |
|---|---|---|---|
| ecs-001 | Application Port | 「8000」を含むチャンクなし | 正解根拠はALB RunbookのRank 3（ECS RunbookではRank 7も確認） |
| ecs-002 | エスカレーションまでの時間 | 「15分以内」を含むチャンクなし | ECS RunbookのRank 3に正解根拠 |
| ecs-003 | ECS CPUアーキテクチャ | 「Linux / ARM64」を含むチャンクなし | ECS RunbookのRank 3に正解根拠 |
| alb-004 | `/health` 正常、`/chat` 503時の切り分け | アプリケーション・依存サービス障害を疑う記述あり | Gate判定のFalse Negative疑い。生の判定出力は未確認 |

`ecs-002` と `ecs-003` は調査用に `search_vectors(..., top_k=10)` を実行して検索順位を確認した。`ecs-001` も先行調査でRank 3に根拠があることを確認済み。調査用のTop-10は本番設定の変更を意味しない。

## 5. 改善実験

### 5.1 3問での先行確認

`generate_rag_answer(..., top_k=3)` を用いて `ecs-001`・`ecs-002`・`ecs-003` を再実行した。

| ID | Top-2 | Top-3の回答 | Top-3の`abstained` |
|---|---|---|---|
| ecs-001 | 回答保留 | Application Port = 8000 | `False` |
| ecs-002 | 回答保留 | エスカレーション = 15分以内 | `False` |
| ecs-003 | 回答保留 | Linux / ARM64 | `False` |

3問とも正解根拠を取得し、期待する回答が生成された。

### 5.2 34問での比較

同じ34問の評価データセットで、Top-2（`evidence_gate_v3.json`）とTop-3（`evidence_gate_top3.json`）を比較した。

| 指標 | Top-2 | Top-3 | 差分 |
|---|---:|---:|---:|
| Answerable質問数 | 24 | 24 | — |
| Unanswerable質問数 | 10 | 10 | — |
| Answerable通過数 | 20 | 23 | +3問 |
| Answerable通過率 | 83.33% | 95.83% | +12.50ポイント |
| Answerable保留数 | 4 | 1 | −3問 |
| False Negative Rate（回答可能なのに保留） | 16.67% | 4.17% | −12.50ポイント |
| Unanswerable保留数 | 10 | 10 | 変化なし |
| Unanswerable保留率 | 100% | 100% | 変化なし |

**残存ケース：** `alb-004` はTop-3でも回答保留となった。

**指標の解釈：** Answerable通過率は「回答生成に進んだ割合」であり、回答のCorrectnessやFaithfulnessを保証しない。また、34問の1回ずつの比較であり、モデル判定のばらつきや追加データへの一般化は未検証。

## 6. 採用判断・設定

現行の評価セットでは、Top-3がTop-2より回答可能な質問の取りこぼしを減らし、Unanswerableの保留性能も維持したため、**`top_k=3` を採用**した。

```text
chunk_size    = 500
chunk_overlap = 100
top_k         = 3
```

`app/config.py` と `.env` のTop-K設定を3に変更。チャンクサイズとオーバーラップは今回の改善対象から除外した。

## 7. 学びと残課題

1. **Document HitとEvidence Hitは異なる。** 正解PDFが検索結果に入っていても、必要な記述を含むチャンクが取得できるとは限らない。
2. **回答保留の原因を分離する。** Retrieval不足とEvidence Gateの判定ミスは異なる問題であり、同じ対処を適用しない。
3. **設定変更は小さく、比較は同じデータで。** 今回はTop-Kのみ変更し、既存34問で通過率と回答保留率を比較した。
4. **Top-3は現行データでの採用値。** コスト、遅延、回答品質、再現性を含む最適性の確定ではない。

### 後続Phaseへの引き継ぎ

- **Phase 19：LLM-as-a-Judge・回答品質評価** — Correctness / Faithfulnessを評価し、`alb-004` のGate判定（根拠があるのに保留）も確認する。
- **Phase 20：RAG改善** — 固定Top-KとAdaptive Retrieval（Evidence不足時だけKを拡張）の比較を検討する。回答品質・レイテンシ・コストも評価する。

## 8. ポートフォリオ・採用スキルとの対応

| 証明したい能力 | 今回の具体的な成果 |
|---|---|
| RAG・ベクトル検索の実装と理解 | S3 Vectorsの検索順位と取得チャンクを分析 |
| ML/AIシステムの評価・改善 | 34問でのBaseline比較、問題発見、Top-K変更、再検証 |
| 根拠に基づく回答制御 | Evidence GateとRetrievalの相互作用を調査 |
| 技術的な問題解決の説明力 | Phase 16→17→18の仮説・検証・改善判断を記録 |

※個人開発による技術実証であり、求人票にある実務経験年数の充足を自動的に意味するものではない。

## 9. 関連ファイル

- `evaluation/results/baseline.json`、`baseline_metrics.json`：Phase 16の評価
- `evaluation/results/evidence_gate_v3.json`：Top-2・Evidence Gate評価
- `evaluation/results/evidence_gate_top3.json`：Top-3・Evidence Gate評価
- `app/services/rag.py`、`app/services/evidence.py`：RAGとEvidence Gate
- `evaluation/evaluate.py`：評価スクリプト

---

**Phase 18の結論：** Phase 16のDocument-level評価では見逃していた正解チャンクの取りこぼしをPhase 17で発見し、Phase 18で検索順位を調査した。Top-Kを2から3へ変更することで、Answerable通過率は83.33%から95.83%に改善し、Unanswerable保留率100%を維持した。残る`alb-004`の判定と回答品質は後続Phaseで検証する。
