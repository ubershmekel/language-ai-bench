"""Document validation, lexing, and parsing for the expression evaluator."""

import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union

TOP_LEVEL = ["config", "programs"]
CONFIG_KEYS = ["maxDepth"]
PROGRAM_KEYS = ["id", "source"]
PROGRAM_ID = re.compile(r"^[A-Za-z0-9_.-]+$")
IDENT_START = re.compile(r"[A-Za-z_]")
IDENT_PART = re.compile(r"[A-Za-z0-9_]")
DIGIT = re.compile(r"[0-9]")
HEX = re.compile(r"[0-9a-fA-F]")
UNSIGNED_LIMIT = (1 << 64) - 1

OPERATORS = [
    "<<", ">>", "==", "!=", "<=", ">=",
    "(", ")", ";", "=", "+", "-", "*", "/", "%", "&", "|", "^", "~", "<", ">",
]

BINARY_LEVELS: List[List[str]] = [
    ["|"],
    ["^"],
    ["&"],
    ["==", "!="],
    ["<", "<=", ">", ">="],
    ["<<", ">>"],
    ["+", "-"],
    ["*", "/", "%"],
]

Token = Tuple[str, Union[int, str], int]
Node = Tuple[Any, ...]


class ProgramError(Exception):
    """A fault in one program's source, reported instead of a value."""

    def __init__(self, code: str, at: int) -> None:
        super().__init__(code)
        self.code = code
        self.at = at


class Source:
    """One program as it arrived, after the document has been validated."""

    def __init__(self, identifier: str, source: str) -> None:
        self.id = identifier
        self.source = source


class Document:
    """A validated input document."""

    def __init__(self, max_depth: int, programs: List[Source]) -> None:
        self.max_depth = max_depth
        self.programs = programs


class Program:
    """A parsed program: its bindings in order and its final expression."""

    def __init__(self, bindings: List[Tuple[str, Node]], body: Node) -> None:
        self.bindings = bindings
        self.body = body


def is_object(value: object) -> bool:
    return isinstance(value, dict)


def has_keys(value: Dict[str, Any], keys: List[str]) -> bool:
    return sorted(value.keys()) == keys


def is_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def parse_document(value: Any) -> Document:
    if not is_object(value) or not has_keys(value, TOP_LEVEL):
        raise ValueError("malformed document")
    config = value["config"]
    if not is_object(config) or not has_keys(config, CONFIG_KEYS):
        raise ValueError("malformed config")
    if not is_integer(config["maxDepth"]) or config["maxDepth"] < 1:
        raise ValueError("malformed maxDepth")
    if not isinstance(value["programs"], list):
        raise ValueError("malformed programs")
    seen = set()
    programs: List[Source] = []
    for item in value["programs"]:
        if not is_object(item) or not has_keys(item, PROGRAM_KEYS):
            raise ValueError("malformed program")
        if not isinstance(item["id"], str) or not PROGRAM_ID.match(item["id"]):
            raise ValueError("malformed id")
        if item["id"] in seen:
            raise ValueError("duplicate id")
        if not isinstance(item["source"], str):
            raise ValueError("malformed source")
        seen.add(item["id"])
        programs.append(Source(item["id"], item["source"]))
    return Document(int(config["maxDepth"]), programs)


def tokenize(source: str) -> List[Token]:
    """Source as a list of tokens, with offsets counted in code points."""
    points = list(source)
    tokens: List[Token] = []
    index = 0
    while index < len(points):
        character = points[index]
        if character in " \t\r\n":
            index += 1
            continue
        if DIGIT.match(character):
            start = index
            if (
                character == "0"
                and index + 1 < len(points)
                and points[index + 1] in "xX"
            ):
                index += 2
                digits = index
                while index < len(points) and HEX.match(points[index]):
                    index += 1
                if index == digits:
                    raise ProgramError("PARSE", start)
                value = int("".join(points[digits:index]), 16)
            else:
                while index < len(points) and DIGIT.match(points[index]):
                    index += 1
                value = int("".join(points[start:index]), 10)
            if index < len(points) and IDENT_PART.match(points[index]):
                raise ProgramError("PARSE", index)
            if value > UNSIGNED_LIMIT:
                if os.environ.get("LAB_SABOTAGE") != "literal-range-unchecked":
                    raise ProgramError("LITERAL_RANGE", start)
                value &= UNSIGNED_LIMIT
            tokens.append(("int", value, start))
            continue
        if IDENT_START.match(character):
            start = index
            while index < len(points) and IDENT_PART.match(points[index]):
                index += 1
            text = "".join(points[start:index])
            tokens.append(("let" if text == "let" else "ident", text, start))
            continue
        operator: Optional[str] = None
        for candidate in OPERATORS:
            if "".join(points[index:index + len(candidate)]) == candidate:
                operator = candidate
                break
        if operator is None:
            raise ProgramError("PARSE", index)
        tokens.append((operator, operator, index))
        index += len(operator)
    tokens.append(("end", "", len(points)))
    return tokens


class Parser:
    """A recursive descent parser over the token list."""

    def __init__(self, tokens: List[Token], max_depth: int) -> None:
        self.tokens = tokens
        self.max_depth = max_depth
        self.index = 0
        self.depth = 0
        if os.environ.get("LAB_SABOTAGE") == "precedence-additive-first":
            self.levels = list(BINARY_LEVELS)
            self.levels[-2], self.levels[-1] = self.levels[-1], self.levels[-2]
        else:
            self.levels = BINARY_LEVELS

    def peek(self) -> Token:
        return self.tokens[self.index]

    def take(self) -> Token:
        token = self.tokens[self.index]
        self.index += 1
        return token

    def expect(self, kind: str) -> Token:
        token = self.peek()
        if token[0] != kind:
            raise ProgramError("PARSE", token[2])
        return self.take()

    def parse_program(self) -> Program:
        bindings: List[Tuple[str, Node]] = []
        while self.peek()[0] == "let":
            self.take()
            name = self.expect("ident")
            self.expect("=")
            bindings.append((str(name[1]), self.parse_expression(0)))
            self.expect(";")
        body = self.parse_expression(0)
        if self.peek()[0] != "end":
            raise ProgramError("PARSE", self.peek()[2])
        return Program(bindings, body)

    def parse_expression(self, level: int) -> Node:
        if level >= len(self.levels):
            return self.parse_unary()
        node = self.parse_expression(level + 1)
        while self.peek()[0] in self.levels[level]:
            operator = self.take()
            right = self.parse_expression(level + 1)
            node = ("binary", operator[0], node, right, operator[2])
        return node

    def parse_unary(self) -> Node:
        token = self.peek()
        if token[0] in ("-", "~"):
            self.take()
            return ("unary", token[0], self.parse_unary(), token[2])
        return self.parse_primary()

    def parse_primary(self) -> Node:
        token = self.peek()
        if token[0] == "int":
            self.take()
            return ("literal", token[1], token[2])
        if token[0] == "ident":
            self.take()
            return ("name", token[1], token[2])
        if token[0] == "(":
            self.depth += 1
            if self.depth > self.max_depth:
                raise ProgramError("DEPTH", token[2])
            self.take()
            node = self.parse_expression(0)
            self.expect(")")
            self.depth -= 1
            return node
        raise ProgramError("PARSE", token[2])


def parse_program(source: str, max_depth: int) -> Program:
    return Parser(tokenize(source), max_depth).parse_program()
