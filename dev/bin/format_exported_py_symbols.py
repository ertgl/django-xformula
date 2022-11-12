import operator
import sys
from contextlib import suppress
from typing import IO, Callable, Iterable, ParamSpec, TypeVar, cast

P = ParamSpec("P")

R = TypeVar("R")

T = TypeVar("T")


def read(buffer: IO) -> str:
    return buffer.read()


def get_export_expression_span(
    source: str,
) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    line_no = 1
    column_no = 0
    start_line_no = -1
    start_column_no = -1
    start_offset = -1
    end_line_no = -1
    end_column_no = -1
    end_offset = -1
    lookbehind: list[tuple[tuple[int, int, int], str]] = []
    prefix = "__all__=["
    prefix_chars = list(prefix)
    for char_index, char in cast(Iterable[tuple[int, str]], enumerate(source)):
        if char == "\n":
            line_no += 1
            column_no = 0
        else:
            column_no += 1
        if start_offset == -1:
            if not (char.isspace() or char == "\\"):
                lookbehind.append(((line_no, column_no, char_index), char))
                if len(lookbehind) > len(prefix_chars):
                    lookbehind.pop(0)
            if len(lookbehind) > 0:
                lookbehind_value = list(map(operator.itemgetter(1), lookbehind))
                found_prefix = lookbehind_value == prefix_chars
                is_prefix_at_start = lookbehind[0][0][1] == 1
                if found_prefix and is_prefix_at_start:
                    lookbehind.clear()
                    start_line_no = line_no
                    start_column_no = column_no
                    start_offset = char_index
        if start_offset != -1 and char == "]":
            end_line_no = line_no
            end_column_no = column_no
            end_offset = char_index
            break
    start = start_line_no, start_column_no, start_offset
    end = end_line_no, end_column_no, end_offset
    return start, end


def collect_existing_exported_symbols(source: str) -> set[tuple[int, str]]:
    existing_exported_symbols: set[tuple[int, str]] = set()
    start, end = get_export_expression_span(source)
    if start[2] == -1 or end[2] == -1:
        return existing_exported_symbols
    lines = source[start[2] + 1 : end[2]].split("\n")
    for line_no, line in enumerate(lines):
        for raw_string in line.split(","):
            symbol_line_no = start[0] + line_no
            symbol_name = raw_string.strip()[1:-1].strip()
            if not symbol_name:
                continue
            symbol = (symbol_line_no, symbol_name)
            existing_exported_symbols.add(symbol)
    return existing_exported_symbols


def collect_imported_symbols(source: str) -> set[tuple[int, str]]:
    imported_symbols: set[tuple[int, str]] = set()
    lines = list(map(lambda l: l.strip(), source.split("\n")))
    for line_no, line in enumerate(lines):
        if line.startswith("from"):
            parts = line.split(" ", maxsplit=3)
            if len(parts) != 4:
                continue
            if parts[2] != "import":
                continue
            if parts[-1] == "(":
                index_of_tuple_end = line_no + lines[line_no:].index(")")
                section = "\n".join(lines[line_no + 1 : index_of_tuple_end])
                symbol_names = [
                    symbol_name.strip()
                    for symbol_name in section.split(",")
                    if symbol_name.strip()
                ]
                for symbol_name_index, symbol_name in enumerate(symbol_names):
                    symbol = (line_no + symbol_name_index + 1, symbol_name)
                    imported_symbols.add(symbol)
            elif "," in parts[-1]:
                symbol_names = [
                    symbol_name.strip()
                    for symbol_name in parts[-1].split(",")
                    if symbol_name.strip()
                ]
                for symbol_name_index, symbol_name in enumerate(symbol_names):
                    symbol = (line_no + symbol_name_index + 1, symbol_name)
                    imported_symbols.add(symbol)
            else:
                symbol = (line_no, parts[-1])
                imported_symbols.add(symbol)
    return imported_symbols


def replace_exported_symbols(
    source: str,
    start: tuple[int, int, int],
    end: tuple[int, int, int],
    symbols: set[tuple[int, str]],
) -> str:
    exported_symbols = sorted(set(map(operator.itemgetter(1), symbols)))
    inner = "\n".join(
        [f'    "{symbol}",' for symbol in exported_symbols],
    )
    rendered = f"\n{inner}\n"
    source_chars = list(source)
    source_chars[start[2] + 1 : end[2]] = list(rendered)
    code = "".join(source_chars)
    return code


def write(
    buffer: IO,
    output: str,
) -> None:
    buffer.write(output)
    buffer.flush()


def non_lazy_map(
    f: Callable[[T], R],
    iterable: Iterable[T],
) -> list[R]:
    acc: list[R] = []
    for x in iterable:
        acc.append(f(x))
    return acc


def main(argv: list[str]) -> int:
    source = read(sys.stdin)
    start, end = get_export_expression_span(source)
    if -1 in (start[2], end[2]):
        write(sys.stdout, source)
        return -1
    existing_exported_symbols = collect_existing_exported_symbols(source)
    imported_symbols: set[tuple[int, str]]
    if "-export-all" in argv:
        imported_symbols = collect_imported_symbols(source)
    else:
        imported_symbols = set()
    output = replace_exported_symbols(
        source,
        start,
        end,
        existing_exported_symbols.union(
            imported_symbols,
        ),
    )
    try:
        write(sys.stdout, output)
    except Exception as error:
        sys.stderr.write(f"{str(error)}\n")
        with suppress(Exception):
            write(sys.stdout, source)
    return 0


if __name__ == "__main__":
    status = main(sys.argv)
    sys.exit(status)
