"""Shared helpers for diagonal matrix-channel article metrics."""

from __future__ import annotations

import math
from typing import Sequence

from snn_framework import ChannelAlphabet, MatrixCell, MatrixFractalNumber


def required_payload_ticks(cells: Sequence[MatrixCell]) -> int:
    """Observation window required by the current direct payload decoder."""

    return max(cell.shift_ticks + 3 * cell.period_ticks for cell in cells) + 1


def capacity_bits(model: MatrixFractalNumber, digit_count: int) -> float:
    """Exact mixed-radix capacity in bits."""

    return sum(math.log2(model.radix(index)) for index in range(digit_count))


def digit_count_for_payload(model: MatrixFractalNumber, payload_bits: int) -> int:
    """Smallest digit count whose mixed-radix capacity covers payload bits."""

    digit_count = 0
    bits = 0.0
    while bits < payload_bits:
        bits += math.log2(model.radix(digit_count))
        digit_count += 1
    return max(1, digit_count)


def worst_case_value(model: MatrixFractalNumber, digit_count: int) -> int:
    """Largest value representable by the first ``digit_count`` channels."""

    return model.decode_digits(
        [model.radix(index) - 1 for index in range(digit_count)]
    )


def article_348_alphabet() -> MatrixFractalNumber:
    """Strict two-channel alphabet from the article's V=348 example."""

    return MatrixFractalNumber.article_348_alphabet()


def contiguous_equal_width(*, start: int = 2, width: int = 5) -> MatrixFractalNumber:
    """Research baseline: each channel receives the next contiguous period band."""

    return MatrixFractalNumber.from_contiguous_bands(start=start, width=width)


def custom_rule_examples() -> list[tuple[str, str, MatrixFractalNumber]]:
    """Named user-defined alphabets used by figures and metrics."""

    return [
        ("article_348_alphabet", "diagonal article 348: {2..6}, {7..10}", article_348_alphabet()),
        ("diagonal_width_5", "diagonal contiguous bands, width=5", contiguous_equal_width(width=5)),
        ("diagonal_width_8", "diagonal contiguous bands, width=8", contiguous_equal_width(width=8)),
        (
            "custom_diagonal_rule",
            "custom diagonal user rule",
            MatrixFractalNumber.from_rule(
                lambda index: ChannelAlphabet(
                    periods=range(2 + index * 6, 6 + index * 6)
                )
            ),
        ),
    ]
