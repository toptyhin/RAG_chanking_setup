# Сертификаты для GigaChat (не в git)

Сюда кладут **Russian Trusted Root CA** (НУЦ Минцифры), чтобы `verify_ssl` для GigaChat работал без отключения проверки.

## Как получить

1. Скачайте корневой сертификат с [Госуслуг / НУЦ Минцифры](https://www.gosuslugi.ru/crt) (PEM/CRT).
2. Положите файл(ы) в эту папку, например:

```text
certs/russian_trusted_root_ca_pem.crt
```

Имена `*.crt` / `*.pem` / `*.cer` подхватываются автоматически. Сами файлы **не коммитятся** (см. `.gitignore`).

Нужен **PEM** (`-----BEGIN CERTIFICATE-----`). Бинарный DER (часто «GOST 2025» с сайта НУЦ) OpenSSL не принимает как `cafile` — будет `X509: NO_CERTIFICATE_OR_CRL_FOUND`. Для TLS GigaChat достаточно классического **Russian Trusted Root CA** в PEM.

## Docker

При `docker compose build` API-образ подхватит файлы из `certs/` (если есть) и добавит их в системное CA store.  
Сборка **не падает**, если папка пустая.

После добавления или замены сертификатов пересоберите API:

```bash
docker compose build api
docker compose up -d api
```

## Локальный запуск (без Docker)

Укажите путь в `.env`:

```bash
GIGACHAT_CA_BUNDLE=./certs
# или конкретный файл:
# GIGACHAT_CA_BUNDLE=./certs/russian_trusted_root_ca_pem.crt
```

Либо оставьте пустым — клиент сам ищет `./certs` и системные CA.

## UI

Во вкладке «Выбор моделей» → GigaChat чекбокс **«Проверять SSL-сертификаты»** включён по умолчанию. Отключайте только для отладки.
