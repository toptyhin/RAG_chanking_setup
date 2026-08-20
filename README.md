# rageval

Локальный RAG Preparer & Evaluator.

- Архитектура: [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
- Зависимости: [`../DEPENDENCIES.md`](../DEPENDENCIES.md)
- Флоу оценки: [`../evaluation-flows.md`](../evaluation-flows.md)
- План реализации: [`plan/README.md`](./plan/README.md)

## Структура

```text
rageval/
├── apps/
│   ├── api/          # FastAPI
│   └── web/          # Next.js UI
├── packages/         # domain + сервисы ядра
├── adapters/         # SQLite, FS, Qdrant, cache, queue, LLM
├── certs/            # CA для GigaChat (файлы не в git — см. certs/README.md)
├── tests/
├── data/             # локальные данные (gitignored)
├── docker-compose.yml
└── plan/             # этапы реализации
```

## Установка

Требуется Python **3.12+**.

```bash
cd rageval
python3.12 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev,ml]"
```

Проверка:

```bash
python -c "import rageval_domain; print(rageval_domain.__version__)"
pytest -q
```

## Full stack (one command)

```bash
cd rageval
docker compose up --build
```

API-образ многостадийный: тяжёлые pip-зависимости в `requirements-api.txt` (слой `deps`), код приложения ставится отдельно (`--no-deps`). Повторные сборки после правок Python обычно быстрые, пока не меняется `requirements-api.txt`. Нужен BuildKit (`DOCKER_BUILDKIT=1`, по умолчанию в Docker Compose v2).

- UI: http://localhost:3000  
- API: http://localhost:8000/health  
- Qdrant: http://localhost:6333/readyz  

Volumes: `data` — SQLite и object store; `hf_models` — кеш весов Hugging Face (`HF_HOME=/models`). Браузерный UI ходит в API по `NEXT_PUBLIC_API_URL` (по умолчанию `http://localhost:8000`).

Для HF без warning про unauthenticated requests задайте `HF_TOKEN` в `rageval/.env` (см. `.env.example`) — compose прокинет его в API.

### GigaChat и сертификат НУЦ Минцифры

GigaChat использует цепочку с **Russian Trusted Root CA**. Положите `.crt`/`.pem` в [`certs/`](./certs/) (файлы не коммитятся; инструкция — [`certs/README.md`](./certs/README.md)).

- При `docker compose build` сертификаты (если есть) попадают в образ API; без файлов сборка не ломается.
- `verify_ssl` для GigaChat **включён по умолчанию**; путь к CA: env `GIGACHAT_CA_BUNDLE` или автопоиск `./certs` / bundle в образе.
- После добавления CA пересоберите API: `docker compose build api && docker compose up -d api`.

Локальная разработка фронта без Docker:

```bash
cd apps/web
cp .env.example .env.local   # при необходимости
npm install
npm run dev
```

## Qdrant (фаза A)

```bash
docker compose up -d qdrant
curl -s http://localhost:6333/readyz
docker compose down
```

## Конфиг

Скопируйте [`.env.example`](./.env.example) в `.env` при необходимости.  
Настройки читаются через `rageval_domain.settings.get_settings()`.

## API (фаза B)

```bash
source .venv/bin/activate
# опционально: alembic upgrade head
uvicorn rageval_api.main:app --app-dir apps/api/src --reload --port 8000
```

Проверка:

```bash
curl -s http://localhost:8000/health
curl -s -X POST http://localhost:8000/projects -H 'content-type: application/json' \
  -d '{"name":"demo"}'
```

Миграции MetaDB:

```bash
alembic upgrade head
```

> При старте API также вызывает `init_db` (create_all) для удобства local MVP.

## Pipeline API (фаза C)

```bash
# prep: raw_bundle → clean_corpus
curl -s -X POST http://localhost:8000/projects/$PID/prep \
  -H 'content-type: application/json' \
  -d "{\"raw_bundle_id\":\"$RAW_ID\",\"pipeline\":\"default\"}"

# reference chunker
curl -s -X POST http://localhost:8000/projects/$PID/chunk-sets/reference \
  -H 'content-type: application/json' \
  -d "{\"clean_corpus_id\":\"$CLEAN_ID\",\"size\":512,\"overlap\":64}"

# BYO chunks / test_set
curl -s -X POST http://localhost:8000/projects/$PID/chunk-sets/import \
  -H 'content-type: application/json' \
  -d '{"chunks":[{"chunk_id":"c1","doc_id":"d1","text":"hello"}]}'
curl -s -X POST http://localhost:8000/projects/$PID/test-sets/import \
  -H 'content-type: application/json' \
  -d "{\"chunk_set_id\":\"$CHUNKS_ID\",\"queries\":[{\"text\":\"q\",\"relevant_chunk_ids\":[\"c1\"]}]}"
```

## Index / Retrieve (фаза D)

Нужен Qdrant (`docker compose up -d qdrant`). По умолчанию `EMBEDDING_PROVIDER=hash` (быстро). Для ST: `EMBEDDING_PROVIDER=sentence_transformers` и `pip install -e ".[ml]"`.

### Модели embedding / rerank (runtime)

- Поиск HF: `GET /models/embedding/search?q=…`, `GET /models/rerank/search?q=…`
- Загрузка: `POST /models/embedding/load` / `POST /models/rerank/load` + SSE `GET /models/jobs/{job_id}/progress`
- В UI: выбор на странице New Run (`ModelPicker`); в эксперимент уходят `embedding.model` и опционально `rerank.enabled` + `rerank.model`

```bash
curl -s -X POST http://localhost:8000/projects/$PID/indexes \
  -H 'content-type: application/json' \
  -d "{\"chunk_set_id\":\"$CHUNKS_ID\"}"

curl -s -X POST http://localhost:8000/projects/$PID/retrieve \
  -H 'content-type: application/json' \
  -d "{\"index_run_id\":\"$INDEX_ID\",\"test_set_id\":\"$TEST_ID\",\"top_k\":5}"
```

## Quickstart (happy path)

1. Поднять стек (или только Qdrant + локальный API):

```bash
cd rageval
docker compose up -d qdrant
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn rageval_api.main:app --app-dir apps/api/src --port 8000
```

2. Прогнать smoke E2E:

```bash
./scripts/smoke.sh
# или: API_URL=http://localhost:8000 ./scripts/smoke.sh
```

Скрипт делает: upload → prep → chunk → testset → background retrieval run → HTML report.

Полный UI: `docker compose up --build` → http://localhost:3000  
План этапов: [`plan/README.md`](./plan/README.md)

## Experiments (Lab modes)

`POST /experiments` возвращает `run_id` сразу (фон через `adapters/queue_local`).  
Статус/прогресс: `GET /experiments/{id}` (опция `?wait=true`) или SSE `GET /experiments/{id}/progress`.  
Отчёт: `GET /experiments/{id}/report`.

Режимы `evaluates`:

| Mode | Start | Sweep (пример) |
|------|-------|----------------|
| `retrieval` | `chunk_set_id` | `retrieval.top_k`, quant, hybrid… |
| `prep` | `raw_bundle_id` | `prep.pipeline`: `plaintext` / `pdf_clean` |
| `chunk` | `clean_corpus_id` | `chunk.size` (+ disclaimer) |

```bash
# Retrieval Lab (async)
RUN_ID=$(curl -s -X POST http://localhost:8000/experiments \
  -H 'content-type: application/json' \
  -d "{
    \"project_id\":\"$PID\",
    \"evaluates\":\"retrieval\",
    \"chunk_set_id\":\"$CHUNKS_ID\",
    \"test_set_id\":\"$TEST_ID\",
    \"swept\": {\"retrieval.top_k\": [1, 5]}
  }" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')

curl -s "http://localhost:8000/experiments/$RUN_ID?wait=true"
curl -s "http://localhost:8000/experiments/$RUN_ID/report" -o report.html
```
