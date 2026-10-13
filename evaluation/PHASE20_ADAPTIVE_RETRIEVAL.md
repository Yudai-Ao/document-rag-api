# Phase 20：Adaptive Retrievalの実装・評価

## 1. 背景・目的

### 1.1 Phase 18・19からの接続

Phase 18では、RetrievalのTop-Kを2から3に変更することで、Answerable通過率を83.33%から95.83%へ改善した。一方、24問のAnswerableのうち、`alb-004` の1問はEvidence Gateによって回答保留されていた。

対象質問：

> ECS TaskはRunningで /health も正常ですが、/chat が503を返します。ALBの問題として調査を続けるべきですか？

Top-3のチャンクには関連情報が含まれていたものの、Evidence Gateは根拠不十分と判定した。Phase 19ではLLM-as-a-Judgeを導入し、回答生成された23問のCorrectness・Faithfulnessを評価した。両指標とも23/23問でPASSしたが、回答保留された`alb-004`は対象外だった。

このため、回答生成後の品質評価とは別に、回答生成前のEvidence取得・判定プロセスの改善を検討した。

### 1.2 Phase 20の目的

Evidence Gateが根拠不十分と判定した場合に検索範囲を拡張する**Adaptive Retrieval**を実装し、回答可能な質問の取りこぼしを減らす。

- Answerable通過率を向上させる
- Unanswerable保留率100%を維持する
- 検索距離による再検索省略の可能性も検討するが、十分な根拠がなければ実装しない

---

## 2. 課題分析と仮説

### 2.1 Top-K拡張の事前検証

`alb-004`について、Adaptive Retrieval導入前の固定Top-3と固定Top-5を比較した。

| 設定 | Evidence判定 | 結果 |
|---|---|---|
| 固定Top-3 | 根拠不足 | 回答保留 |
| 固定Top-5 | 根拠十分 | 期待回答に沿った回答を生成 |

Top-5では、ALB障害ではなくアプリケーション内部または依存AWSサービスを調査すべきと回答できた。

**仮説：Evidence不足時にTop-Kを拡張することで、通常検索では回答保留される質問を救済できる。**

ただしTop-3にも関連Evidenceが存在していたため、追加チャンクの効果とLLM判定の揺れは、この単発実験では完全に切り分けられない。

### 2.2 Distanceを用いた再検索制御の検討

Evidence GateがFalseとなった全質問を再検索すると、Unanswerableにも追加の検索・LLM呼び出しが発生する。そこでTop-3のDistanceを分析した。

| 指標 | 定義 |
|---|---|
| Top-1 Distance | 最も近いチャンクの距離 |
| Average Distance | Top-3の距離の平均 |
| Distance Gap | Top-3とTop-1の距離差 |

Top-3で回答保留された11問の観測結果：

| 対象 | Top-1 Distance | Average Distance | Distance Gap |
|---|---:|---:|---:|
| alb-004（Answerable） | 0.285 | 0.314 | 0.082 |
| Unanswerable 10問 | 0.458〜0.744 | 0.493〜0.777 | 0.016〜0.118 |

この11問に限れば、Average Distanceが0.45未満のときだけ再検索するルールにより、`alb-004`を残しながらUnanswerable 10問の再検索を省略できる見込みだった。

しかし、閾値は同じ評価データから選んだものであり、未知の質問への汎化性能は未検証である。Distanceが大きいことは回答不能であることを意味しない。

**判断：Distance閾値は採用せず、まず単純なAdaptive Retrievalを実装する。**

---

## 3. 改善実装

### 3.1 採用方式

```text
Question
   ↓
Retrieval Top-3
   ↓
Evidence Gate
   ├─ SUFFICIENT → Answer Generation
   └─ INSUFFICIENT
          ↓
       Retrieval Top-5
          ↓
       Evidence Gate
          ├─ SUFFICIENT → Answer Generation
          └─ INSUFFICIENT → Abstention
```

### 3.2 実装内容

変更対象：`app/services/rag.py`

```python
MAX_TOP_K = 5

sufficient = has_sufficient_evidence(
    question=question,
    contexts=contexts
)

if not sufficient and top_k < MAX_TOP_K:
    contexts = search_vectors(
        question=question,
        document_id=document_id,
        top_k=MAX_TOP_K
    )

    sufficient = has_sufficient_evidence(
        question=question,
        contexts=contexts
    )
```

既存のEvidence Gateと回答生成処理を再利用し、再検索部分だけを追加した。Reranker、Hybrid Search、Embeddingモデル変更は対象外とした。

### 3.3 動作確認

`test_adaptive_retrieval.py`で`alb-004`を実行し、Top-3で根拠不足になった際に以下のログが出ることを確認した。

```text
[Adaptive Retrieval] Evidence insufficient. Retrying with top_k=5
```

最終結果は`Abstained: False`、`Contexts: 5`となり、Top-5への再検索後に回答生成できた。

---

## 4. 34問による再評価

### 4.1 評価条件

- Answerable：24問
- Unanswerable：10問
- 合計：34問
- 比較：固定Top-2、固定Top-3、Adaptive Retrieval（Top-3 → Top-5）
- 評価結果：`evaluation/results/evidence_gate_adaptive.json`

### 4.2 評価結果

| 指標 | 固定Top-2 | 固定Top-3 | Adaptive |
|---|---:|---:|---:|
| Answerable通過率 | 83.33% | 95.83% | **100%** |
| Unanswerable保留率 | 100% | 100% | **100%** |
| Answerable保留数 | 4 | 1 | **0** |
| Top-5拡張件数 | 0 | 0 | **11（推定）** |

Adaptive RetrievalではAnswerable 24問すべてが回答生成へ進み、Unanswerable 10問すべてで回答保留となった。最終Sourcesが5件だったケースは11件だった。

### 4.3 結果の解釈と限界

今回の評価セットでは、Answerable通過率が95.83%から100%に改善し、Unanswerable保留率100%を維持した。

ただし以下の限界がある。

- 同じ34問で改善を検討・評価しており、未知の質問に対する性能は保証されない
- LLMのEvidence判定には揺れがあり得る
- 通過率は回答生成へ進んだ割合であり、回答内容のCorrectnessを直接示さない
- Top-5拡張11件は最終Sources件数からの推定であり、検索呼び出しの厳密な計測ではない
- 追加検索の実レイテンシとコストは未計測

---

## 5. 採用判断

**シンプルなAdaptive Retrievalを採用した。**

理由：

1. 回答可能な質問の取りこぼしを改善できた
2. 今回の評価ではUnanswerableの保留性能を維持できた
3. 既存RAG構成の変更が小さい
4. 再検索は最大1回で、処理の複雑化を抑えられる

Distance閾値方式は、現在の評価データだけでは妥当性を十分に確認できないため見送った。

---

## 6. 残課題と今後の改善候補

### 6.1 不要な再検索の削減

今回、最終Sourcesが5件のケースは11件だった。うちUnanswerableの10問は最終的にも回答保留されており、追加検索の削減余地がある。今後、独立した検証データが得られた際にDistance閾値を再検討する。

### 6.2 Embedding・検索処理の効率化

現状はTop-3とTop-5で`search_vectors()`をそれぞれ呼ぶため、質問Embeddingを再生成する可能性がある。コストや遅延が問題になった場合、Embeddingの再利用を検討する。

### 6.3 評価データの拡張

必要になれば評価質問を拡張し、汎化性能を検証する。Ground TruthへのEvidenceアノテーションとEvidence Hit@Kの自動評価も候補だが、現時点では保留とする。

---

## 7. Phase 20の振り返り

### 7.1 試行錯誤の過程

1. **観察**：固定Top-3で`alb-004`が回答保留された
2. **仮説**：検索範囲を拡張すると回答可能になる
3. **事前検証**：固定Top-5で期待回答に沿う回答を確認
4. **設計判断**：Distance閾値の可能性を分析したが、過学習リスクから採用を見送った
5. **改善**：Evidence不足時だけTop-5へ拡張する処理を実装
6. **再評価**：34問でAnswerable通過率100%、Unanswerable保留率100%を観測

### 7.2 Phase 16〜20の接続

| Phase | 主な取り組み | 得られた知見 |
|---|---|---|
| 16 | Document-level Retrieval評価 | 正解文書の取得だけでは十分でない |
| 17 | Evidence Gate導入 | 回答根拠の十分性を判定する必要がある |
| 18 | Top-K改善 | 正解Evidenceの検索順位が回答可能性に影響する |
| 19 | LLM-as-a-Judge | 回答生成後の品質を独立して評価できる |
| 20 | Adaptive Retrieval | Evidence不足に応じて検索範囲を拡張できる |

### 7.3 結論

Phase 20では、**課題発見 → 仮説設定 → 実験 → 実装 → 定量評価 → 採用判断**のサイクルを実施した。

今回の34問ではAnswerable通過率100%、Unanswerable保留率100%を達成したが、実運用での完全な正確性を意味しない。今後はこの評価基盤を維持しつつ、必要性が明確な改善に取り組む。

**Phase 20：完了**

次のPhase：**Phase 21「CI/CD」**
