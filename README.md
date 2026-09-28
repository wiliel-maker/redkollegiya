# ИИ-редколлегия → Telegram

Конвейер, который пишет посты для Telegram-канала голосом конкретного автора,
чистит их от нейрослопа и фактчекает — и публикует. Собран по докладу Павла
Фёдорова «ИИ-редколлегия: как писать через нейронки без слопа» (конференция
«Контент, чтобы выжить в 2026»).

**Подробный пошаговый плейбук — в [AGENTS.md](AGENTS.md).** Он же — файл,
который читает Codex/Claude Code, чтобы провести текст по конвейеру.

## Из чего собрано

Семь скиллов-редакторов (каждый — папка ниже, изначально отдельный
репозиторий `github.com/beaverbeard/*`, MIT, автор Родион Скрябин / рассылка
[«рИИдактор»](https://redaktozavr.ru/rAIdactor)):

| Скилл | Зона |
|---|---|
| [`vinogradov/`](vinogradov) | Голос автора (Voice DNA) из корпуса текстов |
| [`bakhtin/`](bakhtin) | Генерация черновика: multi-agent, 7 форматов |
| [`chukovsky/`](chukovsky) | Смысл, структура, голос, канцелярит |
| [`agranovsky/`](agranovsky) | Фактчек: числа, цитаты, законы, ссылки |
| [`slopotron/`](slopotron) | AI-маркеры и нейрослоп |
| [`rozental/`](rozental) | Орфография, пунктуация, согласование |
| [`milchin/`](milchin) | Типографика — чистый Python-скрипт, без LLM |

Плюс два собственных скрипта:

- [`publish_telegram.py`](publish_telegram.py) — публикация текста/фото в
  Telegram-канал через Bot API (только stdlib).
- [`find_cover.py`](find_cover.py) — поиск royalty-free обложек
  (Unsplash/Pexels) под тему поста.

## Быстрый старт

```bash
cp .env.example .env   # вписать TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID
                        # и опционально UNSPLASH_ACCESS_KEY / PEXELS_API_KEY
```

Дальше — по шагам в [AGENTS.md](AGENTS.md): голос → черновик → вычитка
(смысл → истина → детектор → буква → форма) → проверка человеком →
публикация.

## Лицензии

Каждый скилл — MIT, копирайт указан в его собственном `LICENSE`. Оригиналы:
[vinogradov](https://github.com/beaverbeard/vinogradov) ·
[bakhtin](https://github.com/beaverbeard/bakhtin) ·
[chukovsky](https://github.com/beaverbeard/chukovsky) ·
[agranovsky](https://github.com/beaverbeard/agranovsky) ·
[slopotron](https://github.com/beaverbeard/slopotron) ·
[rozental](https://github.com/beaverbeard/rozental) ·
[milchin](https://github.com/beaverbeard/milchin).

Вложенная git-история апстримов не сохранена (клонировано как снэпшот) —
для истории/обновлений смотреть оригиналы по ссылкам выше.
