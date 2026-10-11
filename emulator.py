#!/usr/bin/env python3
"""Эмулятор языка оболочки ОС. Этап 1: REPL."""

import os
import re
import sys

VFS_NAME = "vfs"


class CommandError(Exception):
    """Ошибка выполнения команды (неизвестная команда, неверные аргументы)."""


_VAR_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _read_var(line: str, i: int) -> tuple[str, int]:
    """Читает переменную после '$' (line[i] == '$'). Возвращает (значение, новая позиция).

    Поддерживает $VAR и ${VAR}. Неопределённая переменная даёт пустую строку,
    одиночный '$' (не перед именем) остаётся буквальным символом.
    """
    j = i + 1
    if j < len(line) and line[j] == "{":
        close = line.find("}", j)
        name = line[j + 1:close] if close != -1 else ""
        if close == -1 or not _VAR_NAME.fullmatch(name):
            raise CommandError("неверная подстановка ${...}")
        return os.environ.get(name, ""), close + 1
    m = _VAR_NAME.match(line, j)
    if m:
        return os.environ.get(m.group(), ""), m.end()
    return "$", j


def parse(line: str) -> list[str]:
    """Разбор строки по правилам, близким к bash.

    - пробелы разделяют аргументы;
    - '...'  : всё буквально, переменные не раскрываются;
    - "..."  : переменные раскрываются, \\ экранирует только " \\ $;
    - \\x    : вне кавычек экранирует следующий символ;
    - $VAR, ${VAR} раскрываются вне кавычек и в двойных кавычках.
    """
    tokens: list[str] = []
    cur: list[str] = []
    in_token = False  # чтобы '' давал пустой аргумент
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if ch in " \t":
            if in_token:
                tokens.append("".join(cur))
                cur, in_token = [], False
            i += 1
        elif ch == "'":
            end = line.find("'", i + 1)
            if end == -1:
                raise CommandError("ошибка разбора: не закрыта одинарная кавычка")
            cur.append(line[i + 1:end])
            in_token = True
            i = end + 1
        elif ch == '"':
            in_token = True
            i += 1
            while True:
                if i >= n:
                    raise CommandError("ошибка разбора: не закрыта двойная кавычка")
                c = line[i]
                if c == '"':
                    i += 1
                    break
                if c == "\\" and i + 1 < n and line[i + 1] in '"\\$':
                    cur.append(line[i + 1])
                    i += 2
                elif c == "$":
                    value, i = _read_var(line, i)
                    cur.append(value)
                else:
                    cur.append(c)
                    i += 1
        elif ch == "\\":
            if i + 1 >= n:
                raise CommandError("ошибка разбора: строка оканчивается на '\\'")
            cur.append(line[i + 1])
            in_token = True
            i += 2
        elif ch == "$":
            value, i = _read_var(line, i)
            cur.append(value)
            if value:  # пустая раскрытая переменная вне кавычек не даёт аргумента
                in_token = True
        else:
            cur.append(ch)
            in_token = True
            i += 1
    if in_token:
        tokens.append("".join(cur))
    return tokens


def cmd_ls(args: list[str]) -> None:
    print(f"ls: аргументы: {args}")


def cmd_cd(args: list[str]) -> None:
    if len(args) > 1:
        raise CommandError("cd: слишком много аргументов")
    print(f"cd: аргументы: {args}")


def cmd_exit(args: list[str]) -> None:
    if args:
        raise CommandError("exit: команда не принимает аргументов")
    raise SystemExit(0)


COMMANDS = {"ls": cmd_ls, "cd": cmd_cd, "exit": cmd_exit}


def execute(tokens: list[str]) -> None:
    name, args = tokens[0], tokens[1:]
    handler = COMMANDS.get(name)
    if handler is None:
        raise CommandError(f"{name}: команда не найдена")
    handler(args)


def repl() -> None:
    while True:
        try:
            line = input(f"[{VFS_NAME}]$ ")
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            continue
        if not line.strip():
            continue
        try:
            tokens = parse(line)
            if tokens:
                execute(tokens)
        except CommandError as e:
            print(f"Ошибка: {e}", file=sys.stderr)


def main() -> None:
    try:
        repl()
    except SystemExit as e:
        sys.exit(e.code)


if __name__ == "__main__":
    main()
