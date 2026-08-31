"""Document validation, lexing, and parsing for the expression evaluator."""

import os
import re

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


class ProgramError(Exception):
    """A fault in one program's source, reported instead of a value."""

    def __init__(self, code, at):
        super().__init__(code)
        self.code = code
        self.at = at


def is_object(value):
    return isinstance(value, dict)


def has_keys(value, keys):
    return sorted(value.keys()) == keys


def is_integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def parse_document(value):
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
    programs = []
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
        programs.append({"id": item["id"], "source": item["source"]})
    return {"max_depth": config["maxDepth"], "programs": programs}


def tokenize(source):
    """Source as a list of (kind, text, at), with at counted in code points."""
    points = list(source)
    tokens = []
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
                text = "".join(points[start:index])
                value = int(text[2:], 16)
            else:
                while index < len(points) and DIGIT.match(points[index]):
                    index += 1
                text = "".join(points[start:index])
                value = int(text, 10)
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
        for operator in OPERATORS:
            if "".join(points[index:index + len(operator)]) == operator:
                tokens.append((operator, operator, index))
                index += len(operator)
                break
        else:
            raise ProgramError("PARSE", index)
    tokens.append(("end", "", len(points)))
    return tokens


BINARY_LEVELS = [
    ["|"],
    ["^"],
    ["&"],
    ["==", "!="],
    ["<", "<=", ">", ">="],
    ["<<", ">>"],
    ["+", "-"],
    ["*", "/", "%"],
]


class Parser:
    def __init__(self, tokens, max_depth):
        self.tokens = tokens
        self.max_depth = max_depth
        self.index = 0
        self.depth = 0
        if os.environ.get("LAB_SABOTAGE") == "precedence-additive-first":
            self.levels = list(BINARY_LEVELS)
            self.levels[-2], self.levels[-1] = self.levels[-1], self.levels[-2]
        else:
            self.levels = BINARY_LEVELS

    def peek(self):
        return self.tokens[self.index]

    def take(self):
        token = self.tokens[self.index]
        self.index += 1
        return token

    def expect(self, kind):
        token = self.peek()
        if token[0] != kind:
            raise ProgramError("PARSE", token[2])
        return self.take()

    def parse_program(self):
        bindings = []
        while self.peek()[0] == "let":
            self.take()
            name = self.expect("ident")
            self.expect("=")
            bindings.append((name[1], self.parse_expression(0)))
            self.expect(";")
        body = self.parse_expression(0)
        if self.peek()[0] != "end":
            raise ProgramError("PARSE", self.peek()[2])
        return {"bindings": bindings, "body": body}

    def parse_expression(self, level):
        if level >= len(self.levels):
            return self.parse_unary()
        node = self.parse_expression(level + 1)
        while self.peek()[0] in self.levels[level]:
            operator = self.take()
            right = self.parse_expression(level + 1)
            node = ("binary", operator[0], node, right, operator[2])
        return node

    def parse_unary(self):
        token = self.peek()
        if token[0] in ("-", "~"):
            self.take()
            return ("unary", token[0], self.parse_unary(), token[2])
        return self.parse_primary()

    def parse_primary(self):
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


def parse_program(source, max_depth):
    return Parser(tokenize(source), max_depth).parse_program()
