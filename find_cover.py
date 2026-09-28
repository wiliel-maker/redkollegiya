#!/usr/bin/env python3
"""Поиск бесплатной (royalty-free) картинки-обложки под пост — Unsplash / Pexels.

Только stdlib. Не публикует и не решает сам — печатает кандидатов, вы (или
следующий шаг конвейера) выбираете номер, скрипт скачивает файл + рядом кладёт
атрибуцию (имя автора фото + ссылка на источник). Ни Unsplash, ни Pexels не
требуют атрибуции по лицензии, но указывать её — хорошая практика и подушка
безопасности, если политика площадки изменится.

Настройка (.env рядом со скриптом или переменные окружения) — нужен хотя бы
один ключ, оба бесплатные:
    UNSPLASH_ACCESS_KEY=...   # https://unsplash.com/developers
    PEXELS_API_KEY=...        # https://www.pexels.com/api/

Использование:
    # 1. Посмотреть кандидатов (ничего не скачивает)
    python3 find_cover.py --query "vintage telephone office"

    # 2. Скачать выбранный (номер из списка выше)
    python3 find_cover.py --query "vintage telephone office" --pick 2 \
        --out drafts/guerrilla-test/cover.jpg
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def http_get_json(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} от API: {body}") from exc


def search_unsplash(query: str, count: int, key: str) -> list[dict]:
    url = "https://api.unsplash.com/search/photos?" + urllib.parse.urlencode(
        {"query": query, "per_page": count, "orientation": "landscape"}
    )
    data = http_get_json(url, {"Authorization": f"Client-ID {key}"})
    candidates = []
    for item in data.get("results", []):
        candidates.append(
            {
                "source": "unsplash",
                "download_url": item["urls"]["regular"],
                "preview_url": item["urls"]["small"],
                "description": item.get("description") or item.get("alt_description") or "(без описания)",
                "author": item["user"]["name"],
                "page_url": item["links"]["html"],
            }
        )
    return candidates


def search_pexels(query: str, count: int, key: str) -> list[dict]:
    url = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode(
        {"query": query, "per_page": count, "orientation": "landscape"}
    )
    data = http_get_json(url, {"Authorization": key})
    candidates = []
    for item in data.get("photos", []):
        candidates.append(
            {
                "source": "pexels",
                "download_url": item["src"]["large"],
                "preview_url": item["src"]["medium"],
                "description": item.get("alt") or "(без описания)",
                "author": item["photographer"],
                "page_url": item["url"],
            }
        )
    return candidates


def download(url: str, out: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "redkollegiya-find-cover/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        out.write_bytes(resp.read())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--query", required=True, help="Ключевые слова темы поста (лучше по-английски — оба API так полнее ищут)")
    parser.add_argument("--source", choices=["auto", "unsplash", "pexels"], default="auto")
    parser.add_argument("--count", type=int, default=5, help="Сколько кандидатов показать")
    parser.add_argument("--pick", type=int, default=None, help="Номер кандидата для скачивания (из предыдущего вывода)")
    parser.add_argument("--out", type=Path, default=None, help="Куда сохранить (обязательно вместе с --pick)")
    args = parser.parse_args()

    load_dotenv(Path(__file__).with_name(".env"))
    unsplash_key = os.environ.get("UNSPLASH_ACCESS_KEY")
    pexels_key = os.environ.get("PEXELS_API_KEY")

    source = args.source
    if source == "auto":
        source = "unsplash" if unsplash_key else "pexels" if pexels_key else None
    if source is None:
        print(
            "Нужен хотя бы один ключ: UNSPLASH_ACCESS_KEY или PEXELS_API_KEY (в .env или окружении).\n"
            "Оба бесплатные: https://unsplash.com/developers  /  https://www.pexels.com/api/",
            file=sys.stderr,
        )
        return 1
    if source == "unsplash" and not unsplash_key:
        print("Выбран unsplash, но UNSPLASH_ACCESS_KEY не задан.", file=sys.stderr)
        return 1
    if source == "pexels" and not pexels_key:
        print("Выбран pexels, но PEXELS_API_KEY не задан.", file=sys.stderr)
        return 1

    try:
        if source == "unsplash":
            candidates = search_unsplash(args.query, args.count, unsplash_key)
        else:
            candidates = search_pexels(args.query, args.count, pexels_key)
    except RuntimeError as exc:
        print(f"Ошибка поиска ({source}): {exc}", file=sys.stderr)
        return 1

    if not candidates:
        print(f"По запросу «{args.query}» ничего не нашлось на {source}.", file=sys.stderr)
        return 1

    if args.pick is None:
        print(f"Источник: {source} · кандидатов: {len(candidates)}\n")
        for i, c in enumerate(candidates, 1):
            print(f"[{i}] {c['description']}")
            print(f"    автор: {c['author']}  ·  превью: {c['preview_url']}")
            print(f"    страница: {c['page_url']}")
        print("\nВыберите номер: python3 find_cover.py --query ... --pick N --out путь.jpg")
        return 0

    if not (1 <= args.pick <= len(candidates)):
        print(f"Нет кандидата №{args.pick} (доступно 1-{len(candidates)}).", file=sys.stderr)
        return 1
    if args.out is None:
        print("Нужен --out путь.jpg вместе с --pick.", file=sys.stderr)
        return 1

    chosen = candidates[args.pick - 1]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    download(chosen["download_url"], args.out)

    attribution_path = args.out.with_suffix(args.out.suffix + ".attribution.txt")
    attribution_path.write_text(
        f"Источник: {chosen['source']}\n"
        f"Автор: {chosen['author']}\n"
        f"Страница: {chosen['page_url']}\n"
        f"Скачано по запросу: {args.query}\n"
        "Лицензия не требует атрибуции, но она сохранена на всякий случай.\n",
        encoding="utf-8",
    )
    print(f"Сохранено: {args.out}")
    print(f"Атрибуция: {attribution_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
