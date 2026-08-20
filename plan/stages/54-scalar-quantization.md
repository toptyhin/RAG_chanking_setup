# Этап 54. Scalar (int8) quantization

**Slug:** `scalar-quantization`
**Статус:** done
**Приоритет:** P1 (расширение оси сравнения)

## Проблема

`quantization_to_qdrant` поддерживает только `binary` (`client.py:36-44`), для
остального — `raise ValueError`. При этом `evaluation-axes.md` заявляет scalar как
ось. По факту на оси quantization всего две точки: `none` и `binary(±rescore)`.

Для многих моделей (например 384-dim MiniLM, cosine) binary сильно роняет качество,
а «золотая середина» — scalar int8. Без неё Pareto по памяти/качеству неполный.

## Цель

Добавить scalar (int8) quantization как третий вариант оси, с опциональным rescore.

## В scope

- `client.py`: `quantization_to_qdrant` → ветка `scalar` (`qm.ScalarQuantization`,
  int8, `always_ram` по умолчанию false).
- `parse_quantization_axis`: принимать `"scalar"`, `"scalar+rescore"`,
  `{"method":"scalar", "rescore":true}`.
- `get_index_size_mb`: оценка байт/размерность для scalar = 1.0 (int8) в fallback-оценке.
- Значения оси: `none` / `scalar` / `scalar+rescore` / `binary` / `binary+rescore`.

## Вне scope

- Product quantization (отдельный этап при необходимости).
- Тюнинг `quantile`/`always_ram` как отдельных под-осей.

## Результат (deliverables)

- Правка `adapters/vectordb_qdrant/.../client.py`.
- Тест: коллекция со scalar создаётся; размер меньше `none`, больше `binary`
  (по estimate); recall обычно ближе к `none`, чем binary.

## Критерии готовности

- Три метода (none/scalar/binary) дают три разных `index_size_mb`.
- Sweep по quantization не пересчитывает эмбеддинги (кеш).

## Зависит от

- [40. Quantization в Index](./40-index-quantization.md)
- [41. Метрики размера индекса](./41-index-size-metrics.md)

## Документация

- `evaluation-axes.md §MVP` (quantization + rescore)
- `DEPENDENCIES.md` (Qdrant)

## Оценка сложности

S–M.
