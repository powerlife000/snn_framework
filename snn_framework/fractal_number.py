"""Functional fractal number representation based on ``F(n, i)``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .o1_decoder import (
    O1DecodeResult,
    bits_to_int,
    decode_tick_by_search,
    decode_tick_o1,
    int_to_bits,
)


@dataclass(frozen=True)
class ChannelParameters:
    """Parameters of one functional channel ``F(n, i)``."""

    index: int
    period: int
    shift: int = 0
    threshold: float = 0.5
    probability: float = 1.0

    @classmethod
    def default(cls, index: int) -> "ChannelParameters":
        if index < 0:
            raise ValueError("index must be non-negative")
        return cls(index=index, period=1 << (index + 1))

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("index must be non-negative")
        if self.period < 2:
            raise ValueError("period must be >= 2")
        if not 0.0 < self.threshold < 1.0:
            raise ValueError("threshold must be in (0, 1)")
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError("probability must be in [0, 1]")

    def value(self, tick: int) -> int:
        """Return ``F(tick, index)``."""

        position = (tick + self.shift) % self.period
        return int(position >= self.period * self.threshold)

    def phase(self, tick: int) -> float:
        """Return normalized phase in ``[0, 1)`` for this tick."""

        return ((tick + self.shift) % self.period) / self.period


@dataclass(frozen=True)
class WaveSample:
    """One multichannel step sample emitted by a static clock generator."""

    tick: int
    sample_index: int
    time: float
    amplitudes: tuple[float, ...]
    bits: tuple[int, ...]


class FractalNumber:
    """Finite-width functional fractal number.

    With default periods ``T(i)=2^(i+1)`` and zero shifts, the channel vector
    exactly matches the little-endian binary representation of the tick ``n``.
    """

    def __init__(
        self,
        width: int,
        *,
        shifts: Sequence[int] | None = None,
        thresholds: Sequence[float] | None = None,
        probabilities: Sequence[float] | None = None,
    ) -> None:
        if width < 1:
            raise ValueError("width must be >= 1")
        self.width = width
        shifts = shifts if shifts is not None else [0] * width
        thresholds = thresholds if thresholds is not None else [0.5] * width
        probabilities = probabilities if probabilities is not None else [1.0] * width
        if not (len(shifts) == len(thresholds) == len(probabilities) == width):
            raise ValueError("shifts, thresholds and probabilities must match width")

        self.channels = tuple(
            ChannelParameters(
                index=index,
                period=1 << (index + 1),
                shift=int(shifts[index]),
                threshold=float(thresholds[index]),
                probability=float(probabilities[index]),
            )
            for index in range(width)
        )

    @property
    def modulus(self) -> int:
        return 1 << self.width

    def period(self, index: int) -> int:
        return self.channels[index].period

    def F(self, tick: int, index: int) -> int:
        """Return the functional digit ``F(n, i)``."""

        return self.channels[index].value(tick)

    def encode(self, number: int) -> list[int]:
        """Encode a decimal number into channel states."""

        if number < 0:
            raise ValueError("number must be non-negative")
        return [channel.value(number) for channel in self.channels]

    def decode(self, bits: Sequence[int]) -> int:
        """Decode base fractal bits as a decimal number.

        This method is exact for zero-shift default channels and is intentionally
        strict. Use ``decode_tick_o1`` for globally shifted channels.
        """

        if len(bits) != self.width:
            raise ValueError("bits length must match width")
        if any(channel.shift % channel.period != 0 for channel in self.channels):
            raise ValueError("decode requires zero shifts; use decode_tick_o1")
        return bits_to_int(bits)

    def decode_tick_o1(self, bits: Sequence[int]) -> O1DecodeResult:
        """Directly restore tick ``n`` from channel states when possible."""

        return decode_tick_o1(bits, self.channels)

    def decode_tick_by_search(
        self, bits: Sequence[int], max_tick: int | None = None
    ) -> list[int]:
        """Reference search decoder for research and ambiguity checks."""

        return decode_tick_by_search(bits, self.channels, max_tick=max_tick)

    def matrix(self, rows: int) -> list[list[int]]:
        """Generate ``F(n, i)`` matrix for ticks ``0..rows-1``."""

        if rows < 1:
            raise ValueError("rows must be >= 1")
        return [self.encode(tick) for tick in range(rows)]

    def state_table(self, rows: int) -> list[dict[str, object]]:
        """Build a compact table for notebooks and tests."""

        return [
            {
                "n": tick,
                "bits": self.encode(tick),
                "register": "".join(str(bit) for bit in reversed(self.encode(tick))),
                "decoded": self.decode_tick_o1(self.encode(tick)).tick
                if self._supports_direct_decoding()
                else self.decode_tick_by_search(self.encode(tick)),
            }
            for tick in range(rows)
        ]

    def wave_sequence(
        self,
        ticks: int,
        *,
        samples_per_tick: int = 8,
        clock_hz: float = 1.0,
        amplitude: float = 1.0,
    ) -> list[WaveSample]:
        """Generate a multichannel step-amplitude sequence from a static clock."""

        if ticks < 1:
            raise ValueError("ticks must be >= 1")
        if samples_per_tick < 1:
            raise ValueError("samples_per_tick must be >= 1")
        if clock_hz <= 0:
            raise ValueError("clock_hz must be positive")
        if amplitude < 0:
            raise ValueError("amplitude must be non-negative")

        samples: list[WaveSample] = []
        for tick in range(ticks):
            bits = tuple(self.encode(tick))
            for sample_index in range(samples_per_tick):
                local = sample_index / samples_per_tick
                time = (tick + local) / clock_hz
                amplitudes = tuple(
                    amplitude * channel.probability * channel.value(tick)
                    for channel in self.channels
                )
                samples.append(
                    WaveSample(
                        tick=tick,
                        sample_index=sample_index,
                        time=time,
                        amplitudes=amplitudes,
                        bits=bits,
                    )
                )
        return samples

    def compression_report(self, rows: int) -> dict[str, float | int]:
        """Estimate matrix-vs-parameter storage for the current generator."""

        if rows < 1:
            raise ValueError("rows must be >= 1")
        full_values = rows * self.width
        parameters = self.width * 4
        return {
            "rows": rows,
            "width": self.width,
            "full_matrix_values": full_values,
            "generator_parameters": parameters,
            "compression_ratio": full_values / parameters,
        }

    def _supports_direct_decoding(self) -> bool:
        try:
            self.decode_tick_o1([0] * self.width)
        except ValueError:
            return False
        return True


def encode_decimal(number: int, width: int) -> list[int]:
    """Encode a decimal number with default fractal channels."""

    return FractalNumber(width).encode(number)


def decode_decimal(bits: Sequence[int]) -> int:
    """Decode default fractal channels into a decimal number."""

    return bits_to_int(bits)


def decimal_to_binary_bits(number: int, width: int) -> list[int]:
    """Public alias used to compare fractal and binary views."""

    return int_to_bits(number, width)
