# Этап 45. Режим Prep Lab (минимум)

**Slug:** `prep-lab-mode`  
**Статус:** done

## Цель

Сравнить 2 prep pipeline на downstream Recall.

## В scope

- evaluates=prep
- 2 pipeline (plaintext vs pdf-clean variant)
- fixed chunk+embed+retrieve
- disclaimer/meta

## Вне scope

- полный corpus hygiene suite

## Результат (deliverables)

- orchestrator branch prep

## Критерии готовности

- отчёт: две строки prep + Recall

## Зависит от

- [28. Orchestrator: один retrieval-конфиг](./28-orchestrator-single-config.md)
- [14. Сохранение clean_corpus](./14-persist-clean-corpus.md)
- [12. Prep: plaintext/markdown](./12-prep-plaintext.md)

## Документация

- `evaluation-flows.md Prep Lab`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.
