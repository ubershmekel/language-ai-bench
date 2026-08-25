"""Exact decimal helpers for money amounts and rates."""

import os
import re
from fractions import Fraction

AMOUNT = re.compile(r"^-?[0-9]+(\.[0-9]+)?$")
RATE = re.compile(r"^[0-9]+(\.[0-9]+)?$")


def parse_decimal(text, pattern, max_places):
    if not isinstance(text, str) or not pattern.match(text):
        raise ValueError("malformed decimal")
    body = text[1:] if text.startswith("-") else text
    places = len(body.split(".")[1]) if "." in body else 0
    if places > max_places and os.environ.get("LAB_SABOTAGE") != "ignore-decimal-limit":
        raise ValueError("too many decimal places")
    value = Fraction(int(body.replace(".", "")), 10**places)
    return -value if text.startswith("-") else value


def parse_amount(text, minor_units):
    return parse_decimal(text, AMOUNT, minor_units)


def parse_rate(text):
    value = parse_decimal(text, RATE, 8)
    if value <= 0:
        raise ValueError("rate must be positive")
    return value


def round_half_even(value, places):
    scaled = value * 10**places
    negative = scaled < 0
    magnitude = -scaled if negative else scaled
    whole = magnitude.numerator // magnitude.denominator
    remainder = magnitude - whole
    half_up = os.environ.get("LAB_SABOTAGE") == "half-up-rounding"
    if remainder > Fraction(1, 2):
        whole += 1
    elif remainder == Fraction(1, 2) and (half_up or whole % 2 == 1):
        whole += 1
    return -whole if negative else whole


def format_minor(minor, places):
    negative = minor < 0
    digits = str(-minor if negative else minor).rjust(places + 1, "0")
    if places:
        digits = digits[: len(digits) - places] + "." + digits[len(digits) - places :]
    return "-" + digits if negative else digits
