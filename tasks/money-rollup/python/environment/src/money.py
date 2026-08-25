"""Amount parsing, rounding, and formatting helpers."""

import math


def parse_amount(text, minor_units):
    return float(text)


def parse_rate(text):
    return float(text)


def round_amount(value, places):
    scale = 10**places
    return int(math.trunc(value * scale + math.copysign(0.5, value)))


def format_minor(minor, places):
    negative = minor < 0
    digits = str(-minor if negative else minor).rjust(places + 1, "0")
    if places:
        digits = digits[: len(digits) - places] + "." + digits[len(digits) - places :]
    return "-" + digits if negative else digits
