#!/usr/bin/env python3
"""
File Integrity Monitor (FIM)
-----------------------------
Отслеживает изменения файлов в указанной директории на основе SHA-256 хешей.

Использование:
    python file_integrity_monitor.py init /path/to/dir      # создать baseline
    python file_integrity_monitor.py check /path/to/dir     # проверить изменения
    python file_integrity_monitor.py watch /path/to/dir     # непрерывный мониторинг

Автор: [ilya0088]
Лицензия: MIT
"""

import hashlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

BASELINE_FILE = ".fim_baseline.json"
CHUNK_SIZE = 65536  # 64 KB


def calculate_hash(filepath: str) -> str:
    """Вычисляет SHA-256 хеш файла."""
    sha256 = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                sha256.update(chunk)
        return sha256.hexdigest()
    except (PermissionError, FileNotFoundError, OSError) as e:
        print(f"[!] Не удалось прочитать {filepath}: {e}")
        return ""


def scan_directory(directory: str) -> dict:
    """Сканирует директорию и возвращает словарь {путь: хеш}."""
    result = {}
    for root, _, files in os.walk(directory):
        # Пропускаем сам baseline-файл
        if BASELINE_FILE in files:
            files.remove(BASELINE_FILE)
        for name in files:
            filepath = os.path.join(root, name)
            file_hash = calculate_hash(filepath)
            if file_hash:
                result[filepath] = {
                    "hash": file_hash,
                    "size": os.path.getsize(filepath),
                    "modified": os.path.getmtime(filepath),
                }
    return result


def save_baseline(directory: str, data: dict) -> None:
    baseline_path = os.path.join(directory, BASELINE_FILE)
    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[+] Baseline сохранён: {baseline_path}")
    print(f"[+] Отслеживается файлов: {len(data)}")


def load_baseline(directory: str) -> dict:
    baseline_path = os.path.join(directory, BASELINE_FILE)
    if not os.path.exists(baseline_path):
        print("[!] Baseline не найден. Сначала запусти команду 'init'.")
        sys.exit(1)
    with open(baseline_path, "r", encoding="utf-8") as f:
        return json.load(f)


def compare_states(old: dict, new: dict) -> dict:
    """Сравнивает старое и новое состояние, возвращает отчёт об изменениях."""
    added = [f for f in new if f not in old]
    removed = [f for f in old if f not in new]
    modified = [
        f for f in new
        if f in old and new[f]["hash"] != old[f]["hash"]
    ]
    return {"added": added, "removed": removed, "modified": modified}


def print_report(changes: dict) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(changes["added"]) + len(changes["removed"]) + len(changes["modified"])

    if total == 0:
        print(f"[{timestamp}] ✓ Изменений не обнаружено.")
        return

    print(f"[{timestamp}] ⚠ Обнаружено изменений: {total}")

    if changes["added"]:
        print("\n  Новые файлы:")
        for f in changes["added"]:
            print(f"    + {f}")

    if changes["removed"]:
        print("\n  Удалённые файлы:")
        for f in changes["removed"]:
            print(f"    - {f}")

    if changes["modified"]:
        print("\n  Изменённые файлы:")
        for f in changes["modified"]:
            print(f"    * {f}")


def cmd_init(directory: str) -> None:
    print(f"[*] Создание baseline для: {directory}")
    data = scan_directory(directory)
    save_baseline(directory, data)


def cmd_check(directory: str) -> None:
    old_state = load_baseline(directory)
    new_state = scan_directory(directory)
    changes = compare_states(old_state, new_state)
    print_report(changes)


def cmd_watch(directory: str, interval: int = 10) -> None:
    print(f"[*] Мониторинг {directory} каждые {interval} сек. (Ctrl+C для остановки)")
    if not os.path.exists(os.path.join(directory, BASELINE_FILE)):
        cmd_init(directory)

    try:
        while True:
            time.sleep(interval)
            old_state = load_baseline(directory)
            new_state = scan_directory(directory)
            changes = compare_states(old_state, new_state)
            print_report(changes)
            if any(changes.values()):
                save_baseline(directory, new_state)  # обновляем baseline
    except KeyboardInterrupt:
        print("\n[*] Мониторинг остановлен.")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    directory = sys.argv[2]

    if not os.path.isdir(directory):
        print(f"[!] Директория не найдена: {directory}")
        sys.exit(1)

    if command == "init":
        cmd_init(directory)
    elif command == "check":
        cmd_check(directory)
    elif command == "watch":
        interval = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        cmd_watch(directory, interval)
    else:
        print(f"[!] Неизвестная команда: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
