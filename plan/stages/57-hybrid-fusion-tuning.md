# Этап 57. Hybrid: взвешенное слияние и явный candidate_k

**Slug:** `hybrid-fusion-tuning`
**Статус:** done
**Приоритет:** P2 (качество сравнения)

## Проблема

`hybrid_retrieve` реализует только классический RRF с фиксированным `k=60`
(`hybrid.py:22,69`), а `candidate_k` вычисляется внутри как `2·top_k` и не является
осью (`hybrid.py:45`). Нельзя сравнить вклад dense vs sparse (веса) и влияние
глубины кандидатов до слияния — а именно hybrid часто даёт больший прирост, чем
смена embedding-модели (`evaluation-axes.md §2.1`).

## Цель

Сделать параметры слияния настраиваемыми осями: метод (`rrf` / `weighted`), веса
dense/sparse, `rrf_k`, `candidate_k`.

## В scope

- `hybrid.py`: добавить `weighted` fusion (нормализация score dense/sparse + веса).
- Оси: `retrieval.hybrid.fusion` (`rrf|weighted`),
  `retrieval.hybrid.dense_weight`, `retrieval.hybrid.rrf_k`,
  `retrieval.candidate_k`.
- `eval_point.py`: прокинуть эти параметры в `hybrid_retrieve`.
- Дефолты сохраняют текущее поведение (`rrf`, `k=60`, `candidate_k=2·top_k`).

## Вне scope

- Обучаемое слияние / learned sparse (SPLADE) — later.

## Результат (deliverables)

- Правки `packages/retrieval/.../hybrid.py`, `eval_point.py`.
- Тест: `weighted` с dense_weight=1.0 ≈ dense-only; с 0.0 ≈ sparse-only;
  разный `candidate_k` меняет фьюжн-результат.

## Критерии готовности

- В одном run можно сравнить `rrf` vs `weighted` как ось.
- `candidate_k` виден и влияет на Recall/latency.

## Зависит от

- [38. Hybrid RRF](./38-hybrid-rrf.md)
- [52. Rerank: глубина кандидатов](./52-rerank-candidate-depth.md)

## Документация

- `evaluation-axes.md §2.1`
- `ARCHITECTURE.md §7.5`

## Оценка сложности

M.
