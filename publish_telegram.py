#!/usr/bin/env python3
"""Публикация готового (провычитанного) текста в Telegram-канал через Bot API.

Только stdlib — без внешних зависимостей, чтобы не тащить ничего лишнего на
целевую машину. Текст ожидается уже прошедшим весь конвейер редколлегии
(Бахтин -> Чуковский -> Аграновский -> Слопотрон -> Розенталь -> Мильчин).
Скрипт сам текст не правит и не проверяет на слоп — это не его задача.

Настройка (.env рядом со скриптом или переменные окружения):
    TELEGRAM_BOT_TOKEN=123456:ABC-...
    TELEGRAM_CHANNEL_ID=@my_channel        # или -1001234567890

Использование:
    python3 publish_telegram.py --text-file draft.txt
    python3 publish_telegram.py --text-file draft.txt --photo cover.jpg
    python3 publish_telegram.py --text-file draft.txt --dry-run
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

TELEGRAM_TEXT_LIMIT = 4096
TELEGRAM_CAPTION_LIMIT = 1024
API_BASE = "https://api.telegram.org/bot{token}/{method}"


def load_dotenv(path: Path) -> None:
    """Подхватывает .env, если он есть, без установки лишних пакетов."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def split_text(text: str, limit: int) -> list[str]:
    """Режет длинный текст на части не длиннее limit, по границам абзацев."""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    paragraphs = text.split("\n\n")
    current = ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) > limit:
            if current:
                chunks.append(current)
            if len(para) > limit:
                # Абзац сам по себе длиннее лимита — режем жёстко по символам.
                for i in range(0, len(para), limit):
                    chunks.append(para[i : i + limit])
                current = ""
            else:
                current = para
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def call_api(token: str, method: str, data: dict, file_field: str | None = None, file_path: Path | None = None):
    url = API_BASE.format(token=token, method=method)
    if file_path is None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
    else:
        boundary = uuid.uuid4().hex
        parts = []
        for key, value in data.items():
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode("utf-8"))
        mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        parts.append(
            (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; "
                f"filename=\"{file_path.name}\"\r\nContent-Type: {mime}\r\n\r\n"
            ).encode("utf-8")
        )
        parts.append(file_path.read_bytes())
        parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
        body = b"".join(parts)
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        payload = json.loads(exc.read().decode("utf-8"))

    if not payload.get("ok"):
        raise RuntimeError(f"Telegram API ({method}) отказал: {payload}")
    return payload["result"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--text-file", required=True, type=Path, help="Готовый текст поста (после всего конвейера)")
    parser.add_argument("--photo", type=Path, default=None, help="Опциональная картинка к посту")
    parser.add_argument("--channel", default=None, help="Переопределить TELEGRAM_CHANNEL_ID")
    parser.add_argument("--dry-run", action="store_true", help="Показать, что будет отправлено, но не отправлять")
    args = parser.parse_args()

    load_dotenv(Path(__file__).with_name(".env"))

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel = args.channel or os.environ.get("TELEGRAM_CHANNEL_ID")
    if not token or not channel:
        print("Нужны TELEGRAM_BOT_TOKEN и TELEGRAM_CHANNEL_ID (в .env или окружении).", file=sys.stderr)
        return 1

    if not args.text_file.exists():
        print(f"Файл не найден: {args.text_file}", file=sys.stderr)
        return 1
    text = args.text_file.read_text(encoding="utf-8").strip()
    if not text:
        print("Пустой текст — публиковать нечего.", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"[dry-run] канал: {channel}")
        print(f"[dry-run] фото: {args.photo or '—'}")
        print(f"[dry-run] длина текста: {len(text)} символов")
        print("---")
        print(text)
        return 0

    if args.photo:
        if not args.photo.exists():
            print(f"Фото не найдено: {args.photo}", file=sys.stderr)
            return 1
        caption = text if len(text) <= TELEGRAM_CAPTION_LIMIT else text[: TELEGRAM_CAPTION_LIMIT - 1] + "…"
        result = call_api(
            token,
            "sendPhoto",
            {"chat_id": channel, "caption": caption},
            file_field="photo",
            file_path=args.photo,
        )
        print(f"Опубликовано (фото + подпись): message_id={result['message_id']}")
        if len(text) > TELEGRAM_CAPTION_LIMIT:
            print("Текст длиннее лимита подписи (1024) — подпись обрезана. "
                  "Разбейте пост или публикуйте текстом без фото.", file=sys.stderr)
        return 0

    chunks = split_text(text, TELEGRAM_TEXT_LIMIT)
    for i, chunk in enumerate(chunks, 1):
        result = call_api(token, "sendMessage", {"chat_id": channel, "text": chunk})
        print(f"Опубликовано ({i}/{len(chunks)}): message_id={result['message_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
