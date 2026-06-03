"""Direct tick decoding helpers for functional fractal numbers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


class AmbiguousDecodingError(ValueError):
    """Raised when channel parameters do not define a direct unique decoder."""


class ChannelLike(Protocol):
    index: int
    period: int
    shift: int
    threshold: float


@dataclass(frozen=True)
class O1DecodeResult:
    """Result of direct tick extraction from channel states."""

    tick: int
    encoded_state: int
    global_shift: int
    modulus: int
    exact: bool
    reason: str


def bits_to_int(bits: Sequence[int]) -> int:
    """Convert little-endian channel bits to a decimal integer."""

    value = 0
    for index, bit in enumerate(bits):
        if bit not in (0, 1):
            raise ValueError("bits must contain only 0 and 1")
        value |= int(bit) << index
    return value


def int_to_bits(value: int, width: int) -> list[int]:
    """Convert an integer to little-endian channel bits."""

    if value < 0:
        raise ValueError("value must be non-negative")
    if width < 1:
        raise ValueError("width must be >= 1")
    return [(value >> index) & 1 for index in range(width)]


def infer_global_shift(channels: Sequence[ChannelLike]) -> int:
    """Infer one global shift whose residues match all channel shifts.

    If each channel has ``shift_i = S mod T(i)``, then the observed channel
    vector is the binary representation of ``(n + S) mod 2^width``. That gives
    direct restoration of ``n`` by subtracting ``S`` under the finite modulus.
    """

    if not channels:
        raise ValueError("channels must not be empty")
    ordered = sorted(channels, key=lambda channel: channel.period, reverse=True)
    global_shift = ordered[0].shift % ordered[0].period
    for channel in channels:
        if global_shift % channel.period != channel.shift % channel.period:
            raise AmbiguousDecodingError(
                "channel shifts are not residues of one global shift"
            )
    return global_shift


def decode_tick_o1(bits: Sequence[int], channels: Sequence[ChannelLike]) -> O1DecodeResult:
    """Decode a tick directly for base or globally shifted generators.

    The operation is constant with respect to the number of represented rows
    because it converts one finite-width register into an integer and subtracts
    the global phase shift. In software the register conversion is a short loop
    over the number of channels; in hardware it corresponds to reading the
    register value at once.
    """

    if len(bits) != len(channels):
        raise ValueError("bits and channels must have the same length")
    if not channels:
        raise ValueError("at least one channel is required")
    for channel in channels:
        if channel.threshold != 0.5:
            raise AmbiguousDecodingError(
                "direct decoder currently requires threshold = 0.5"
            )

    width = len(bits)
    modulus = 1 << width
    encoded_state = bits_to_int(bits)
    global_shift = infer_global_shift(channels)
    tick = (encoded_state - global_shift) % modulus
    return O1DecodeResult(
        tick=tick,
        encoded_state=encoded_state,
        global_shift=global_shift,
        modulus=modulus,
        exact=True,
        reason="base/global-shift channel family",
    )


def decode_tick_by_search(
    bits: Sequence[int], channels: Sequence[ChannelLike], max_tick: int | None = None
) -> list[int]:
    """Reference decoder for shifted or experimental channels.

    This is not an O(1) method. It is kept as a research baseline that makes
    ambiguity visible in tests and notebooks.
    """

    if len(bits) != len(channels):
        raise ValueError("bits and channels must have the same length")
    if not channels:
        raise ValueError("at least one channel is required")
    limit = max_tick if max_tick is not None else 1 << len(channels)
    if limit < 1:
        raise ValueError("max_tick must be positive")

    matches: list[int] = []
    for tick in range(limit):
        state = [
            int(((tick + channel.shift) % channel.period) >= channel.period * channel.threshold)
            for channel in channels
        ]
        if state == list(bits):
            matches.append(tick)
    return matches
