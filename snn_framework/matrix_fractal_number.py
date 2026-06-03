"""Matrix-based fractal number representation.

This module keeps the layers separate:

1. a decimal number is converted to digits in base ``period_levels * shift_levels``;
2. each digit selects a cell in a period-shift matrix;
3. selected cells define half-duty periodic step generators;
4. the generators produce a multichannel amplitude signal.

The base matrix does not store probability. Probability/reliability belongs to
later decoding or memory-association layers, not to the primary numeric code.

Ordering invariant:
larger period means lower frequency and a more significant digit channel. The
numeric digits remain little-endian: ``digit_index == 0`` is the least
significant, highest-frequency channel; increasing ``digit_index`` moves toward
lower-frequency, larger-period, more significant channels.

Canonical cell order:
``row_major`` treats the period/frequency row as the integer part and the
shift/phase column as the fractional part of a quantized cycle. Completing one
full phase turn advances to the next integer row.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class MatrixCell:
    """One selected cell of the period-shift alphabet."""

    digit_index: int
    digit_value: int
    period_index: int
    shift_index: int
    period_ticks: int
    shift_ticks: int
    active_width_ticks: int


@dataclass(frozen=True)
class SignalSample:
    """One generated signal sample."""

    tick: int
    channel_amplitudes: tuple[float, ...]
    total_amplitude: float


@dataclass(frozen=True)
class ChannelSchedule:
    """Known clock mask for one digit channel."""

    digit_index: int
    period_ticks: int
    shift_ticks: int
    active_width_ticks: int = 1

    def is_active(self, tick: int) -> bool:
        """Return true when this channel is active at ``tick``."""

        # Packet-local decoding starts at tick 0. Suppress the wrapped active
        # half before the first local zero-then-one cycle has actually begun.
        if tick < self.shift_ticks + self.active_width_ticks:
            return False
        position = (tick - self.shift_ticks) % self.period_ticks
        return position >= self.active_width_ticks


@dataclass(frozen=True)
class DirectDecodeResult:
    """Direct decoder result for one or more step-signal frames."""

    number: int
    digits: tuple[int, ...]
    observed_frames: int
    method: str


class MatrixFractalNumber:
    """Fractal number whose radix is defined by a period-shift matrix.

    ``digit_index`` follows the SNN clock-significance axiom: the least
    significant channel has the shortest period / highest frequency, and each
    more significant channel uses a larger period / lower frequency.

    Within one digit channel, ``row_major`` is the canonical order:
    ``digit = period_index * shift_levels + shift_index``. This means
    ``period_index`` is the integer part and ``shift_index / shift_levels`` is
    the fractional phase/shift part.
    """

    def __init__(
        self,
        period_levels: int,
        shift_levels: int,
        *,
        base_period_ticks: int = 8,
    ) -> None:
        if period_levels < 1:
            raise ValueError("period_levels must be >= 1")
        if shift_levels < 1:
            raise ValueError("shift_levels must be >= 1")
        if base_period_ticks < 2:
            raise ValueError("base_period_ticks must be >= 2")

        self.period_levels = period_levels
        self.shift_levels = shift_levels
        self.base_period_ticks = base_period_ticks
        self.base = period_levels * shift_levels

    def digit_to_indices(self, digit_value: int) -> tuple[int, int]:
        """Map one digit value to ``(period_index, shift_index)``."""

        if not 0 <= digit_value < self.base:
            raise ValueError("digit_value is outside matrix radix")
        return divmod(digit_value, self.shift_levels)

    def cell_indices_to_digit(self, period_index: int, shift_index: int) -> int:
        """Map ``(period_index, shift_index)`` back to a digit value."""

        if not 0 <= period_index < self.period_levels:
            raise ValueError("period_index is outside matrix")
        if not 0 <= shift_index < self.shift_levels:
            raise ValueError("shift_index is outside matrix")
        return period_index * self.shift_levels + shift_index

    def encode_digits(self, number: int, digit_count: int | None = None) -> list[int]:
        """Convert a decimal number to little-endian matrix-radix digits.

        Index ``0`` is least significant and must map to the highest-frequency
        channel. Higher indices are more significant and lower-frequency.
        """

        if number < 0:
            raise ValueError("number must be non-negative")
        if digit_count is not None and digit_count < 1:
            raise ValueError("digit_count must be >= 1")

        if number == 0:
            digits = [0]
        else:
            digits = []
            value = number
            while value:
                value, digit = divmod(value, self.base)
                digits.append(digit)

        if digit_count is not None:
            if len(digits) > digit_count:
                raise ValueError("number does not fit into digit_count")
            digits.extend([0] * (digit_count - len(digits)))
        return digits

    def decode_digits(self, digits: Sequence[int]) -> int:
        """Convert little-endian matrix-radix digits back to decimal.

        The input order is least-significant to most-significant. In the signal
        model that is also highest-frequency to lowest-frequency.
        """

        number = 0
        multiplier = 1
        for digit in digits:
            if not 0 <= digit < self.base:
                raise ValueError("digit is outside matrix radix")
            number += int(digit) * multiplier
            multiplier *= self.base
        return number

    def digit_to_cell(self, digit_index: int, digit_value: int) -> MatrixCell:
        """Map one radix digit to a period-shift matrix cell."""

        if digit_index < 0:
            raise ValueError("digit_index must be non-negative")
        if not 0 <= digit_value < self.base:
            raise ValueError("digit_value is outside matrix radix")

        period_index, shift_index = self.digit_to_indices(digit_value)
        # Digit position must be encoded in the generator family. Otherwise two
        # swapped digits can produce the same summed signal.
        # Larger digit_index means a more significant digit channel; by the SNN
        # clock axiom it therefore receives a larger period / lower frequency.
        period_band = digit_index * self.period_levels + period_index + 1
        period_ticks = self.base_period_ticks * period_band
        # Shift columns are phase offsets inside the selected channel period.
        # Each selected cell emits a binary waveform with zero first half and
        # one second half in its local shifted cycle.
        shift_ticks = round(period_ticks * shift_index / self.shift_levels)
        active_width_ticks = period_ticks // 2
        return MatrixCell(
            digit_index=digit_index,
            digit_value=digit_value,
            period_index=period_index,
            shift_index=shift_index,
            period_ticks=period_ticks,
            shift_ticks=shift_ticks,
            active_width_ticks=active_width_ticks,
        )

    def encode_cells(
        self, number: int, digit_count: int | None = None
    ) -> list[MatrixCell]:
        """Encode a decimal number as selected matrix cells."""

        digits = self.encode_digits(number, digit_count=digit_count)
        return [
            self.digit_to_cell(digit_index, digit)
            for digit_index, digit in enumerate(digits)
        ]

    def candidate_cells(self, digit_index: int) -> list[MatrixCell]:
        """Return every possible matrix cell for one digit channel."""

        if digit_index < 0:
            raise ValueError("digit_index must be non-negative")
        return [
            self.digit_to_cell(digit_index, digit_value)
            for digit_value in range(self.base)
        ]

    def decode_cells(self, cells: Sequence[MatrixCell]) -> int:
        """Decode selected matrix cells back to decimal."""

        ordered = sorted(cells, key=lambda cell: cell.digit_index)
        return self.decode_digits([cell.digit_value for cell in ordered])

    def signal(
        self,
        number: int,
        *,
        digit_count: int | None = None,
        ticks: int = 64,
        amplitude: float = 1.0,
    ) -> list[SignalSample]:
        """Generate a multichannel step-amplitude signal for a number.

        Each digit channel has a known clock mask. When the mask is active,
        the channel emits a binary rectangular step. The digit value is encoded
        by the selected period-shift cell, not by signal height.
        """

        if ticks < 1:
            raise ValueError("ticks must be >= 1")
        if amplitude < 0:
            raise ValueError("amplitude must be non-negative")

        cells = self.encode_cells(number, digit_count=digit_count)
        if digit_count is None:
            digit_count = len(cells)
        samples: list[SignalSample] = []
        for tick in range(ticks):
            channel_amplitudes = tuple(
                self.cell_amplitude(
                    cell,
                    tick,
                    digit_count=digit_count,
                    amplitude=amplitude,
                )
                for cell in cells
            )
            samples.append(
                SignalSample(
                    tick=tick,
                    channel_amplitudes=channel_amplitudes,
                    total_amplitude=sum(channel_amplitudes),
                )
            )
        return samples

    def channel_schedule(
        self, digit_index: int, *, digit_count: int
    ) -> ChannelSchedule:
        """Return the known active-tick mask for one digit channel.

        The first step prototype uses an orthogonal time mask:
        ``period_ticks = digit_count`` and ``shift_ticks = digit_index``.
        This makes channels directly separable in the summed signal.
        """

        if digit_count < 1:
            raise ValueError("digit_count must be >= 1")
        if not 0 <= digit_index < digit_count:
            raise ValueError("digit_index must be inside digit_count")
        return ChannelSchedule(
            digit_index=digit_index,
            period_ticks=digit_count,
            shift_ticks=digit_index,
            active_width_ticks=1,
        )

    @staticmethod
    def cell_schedule(cell: MatrixCell) -> ChannelSchedule:
        """Return the active-tick mask defined by a selected matrix cell."""

        return ChannelSchedule(
            digit_index=cell.digit_index,
            period_ticks=cell.period_ticks,
            shift_ticks=cell.shift_ticks,
            active_width_ticks=cell.active_width_ticks,
        )

    @classmethod
    def cell_active_ticks(cls, cell: MatrixCell, *, ticks: int) -> list[int]:
        """List ticks where the selected matrix cell emits its amplitude."""

        if ticks < 1:
            raise ValueError("ticks must be >= 1")
        schedule = cls.cell_schedule(cell)
        return [tick for tick in range(ticks) if schedule.is_active(tick)]

    @classmethod
    def cell_active_windows(cls, cell: MatrixCell, *, ticks: int) -> list[tuple[int, int]]:
        """List active tick windows as ``(start, end_exclusive)`` pairs."""

        if ticks < 1:
            raise ValueError("ticks must be >= 1")
        windows: list[tuple[int, int]] = []
        start: int | None = None
        schedule = cls.cell_schedule(cell)
        for tick in range(ticks):
            if schedule.is_active(tick):
                if start is None:
                    start = tick
            elif start is not None:
                windows.append((start, tick))
                start = None
        if start is not None:
            windows.append((start, ticks))
        return windows

    def active_ticks(
        self, digit_index: int, *, digit_count: int, ticks: int
    ) -> list[int]:
        """List ticks where the selected digit channel is active."""

        if ticks < 1:
            raise ValueError("ticks must be >= 1")
        schedule = self.channel_schedule(digit_index, digit_count=digit_count)
        return [tick for tick in range(ticks) if schedule.is_active(tick)]

    def extract_digit_samples(
        self,
        observed_total_amplitudes: Sequence[float | None],
        *,
        digit_index: int,
        digit_count: int,
    ) -> list[float]:
        """Extract observed amplitudes for one digit channel using its mask."""

        schedule = self.channel_schedule(digit_index, digit_count=digit_count)
        return [
            float(value)
            for tick, value in enumerate(observed_total_amplitudes)
            if value is not None and schedule.is_active(tick)
        ]

    @classmethod
    def extract_cell_samples(
        cls,
        observed_total_amplitudes: Sequence[float | None],
        *,
        cell: MatrixCell,
    ) -> list[float]:
        """Extract observed amplitudes using the selected cell mask."""

        schedule = cls.cell_schedule(cell)
        return [
            float(value)
            for tick, value in enumerate(observed_total_amplitudes)
            if value is not None and schedule.is_active(tick)
        ]

    def decode_step_signal(
        self,
        observed_total_amplitudes: Sequence[float | None],
        *,
        digit_count: int,
        amplitude: float = 1.0,
    ) -> DirectDecodeResult:
        """Decode one summed signal by peeling channels from high to low frequency.

        The packet-local code starts with a silent half-period and then emits an
        active half-period. For each digit channel, the first rise in the
        residual gives ``shift + period / 2`` and the next falling edge gives the
        active half-period length. That directly determines the selected cell,
        whose full waveform is then subtracted before decoding the next channel.
        """

        if digit_count < 1:
            raise ValueError("digit_count must be >= 1")
        if amplitude <= 0:
            raise ValueError("amplitude must be positive")
        if not observed_total_amplitudes:
            raise ValueError("observed signal must not be empty")

        residual = [
            None if value is None else float(value)
            for value in observed_total_amplitudes
        ]
        digits: list[int] = []
        threshold = amplitude / 2.0

        for digit_index in range(digit_count):
            cell = self._decode_next_cell_from_residual(
                residual,
                digit_index=digit_index,
                amplitude=amplitude,
                threshold=threshold,
            )
            digits.append(cell.digit_value)

            schedule = self.cell_schedule(cell)
            for tick, value in enumerate(residual):
                if value is not None and schedule.is_active(tick):
                    residual[tick] = value - amplitude

        return DirectDecodeResult(
            number=self.decode_digits(digits),
            digits=tuple(digits),
            observed_frames=len(observed_total_amplitudes),
            method="summed signal peeling decoder",
        )

    def _decode_next_cell_from_residual(
        self,
        residual: Sequence[float | None],
        *,
        digit_index: int,
        amplitude: float,
        threshold: float,
    ) -> MatrixCell:
        """Recover one channel cell from the first residual pulse segment."""

        start = next(
            (
                tick
                for tick, value in enumerate(residual)
                if value is not None and value >= threshold
            ),
            None,
        )
        if start is None:
            raise ValueError(f"no active segment for digit channel {digit_index}")

        end: int | None = None
        previous = residual[start]
        for tick in range(start + 1, len(residual)):
            value = residual[tick]
            if value is None:
                continue
            if previous is not None and previous - value >= threshold:
                end = tick
                break
            previous = value
        if end is None:
            raise ValueError(f"no falling edge for digit channel {digit_index}")

        half_period = end - start
        if half_period < 1:
            raise ValueError("decoded half-period must be positive")
        period_ticks = half_period * 2
        if period_ticks % self.base_period_ticks != 0:
            raise ValueError("decoded period is outside the channel grid")

        period_band = period_ticks // self.base_period_ticks
        period_index = period_band - digit_index * self.period_levels - 1
        if not 0 <= period_index < self.period_levels:
            raise ValueError("decoded period is outside the digit channel alphabet")

        shift_ticks = start - half_period
        if shift_ticks < 0:
            raise ValueError("decoded shift is negative")
        shift_index = round(shift_ticks * self.shift_levels / period_ticks)
        if not 0 <= shift_index < self.shift_levels:
            raise ValueError("decoded shift is outside the digit channel alphabet")

        digit_value = self.cell_indices_to_digit(period_index, shift_index)
        cell = self.digit_to_cell(digit_index, digit_value)
        if cell.period_ticks != period_ticks or cell.shift_ticks != shift_ticks:
            raise ValueError("decoded cell is not aligned to the matrix alphabet")
        return cell

    def decode_channel_signals(
        self,
        observed_channel_amplitudes: Sequence[Sequence[float | None]],
        *,
        amplitude: float = 1.0,
    ) -> DirectDecodeResult:
        """Decode separated channel signals by matching periodic cell masks."""

        if amplitude <= 0:
            raise ValueError("amplitude must be positive")
        if not observed_channel_amplitudes:
            raise ValueError("observed channels must not be empty")

        digits: list[int] = []
        observed_frames = 0
        threshold = amplitude / 2.0
        for digit_index, channel_signal in enumerate(observed_channel_amplitudes):
            if not channel_signal:
                raise ValueError(f"channel {digit_index} must not be empty")
            observed_frames = max(observed_frames, len(channel_signal))

            best_cell: MatrixCell | None = None
            best_score: tuple[int, int] | None = None
            for candidate in self.candidate_cells(digit_index):
                schedule = self.cell_schedule(candidate)
                errors = 0
                hits = 0
                for tick, value in enumerate(channel_signal):
                    if value is None:
                        continue
                    observed_active = float(value) >= threshold
                    expected_active = schedule.is_active(tick)
                    errors += int(observed_active != expected_active)
                    hits += int(observed_active and expected_active)
                score = (errors, -hits)
                if best_score is None or score < best_score:
                    best_score = score
                    best_cell = candidate
            if best_cell is None:
                raise ValueError(f"could not decode channel {digit_index}")
            digits.append(best_cell.digit_value)

        return DirectDecodeResult(
            number=self.decode_digits(digits),
            digits=tuple(digits),
            observed_frames=observed_frames,
            method="periodic channel-pattern decoder",
        )

    def state_table(
        self, number: int, *, digit_count: int | None = None, ticks: int = 16
    ) -> list[dict[str, object]]:
        """Generate a human-readable table: cells, channel amplitudes, signal."""

        cells = self.encode_cells(number, digit_count=digit_count)
        rows: list[dict[str, object]] = []
        for sample in self.signal(number, digit_count=digit_count, ticks=ticks):
            rows.append(
                {
                    "tick": sample.tick,
                    "channel_amplitudes": [
                        round(value, 4) for value in sample.channel_amplitudes
                    ],
                    "total_amplitude": round(sample.total_amplitude, 4),
                    "cells": [
                        (cell.period_index, cell.shift_index) for cell in cells
                    ],
                }
            )
        return rows

    @staticmethod
    def cell_amplitude(
        cell: MatrixCell,
        tick: int,
        *,
        digit_count: int,
        amplitude: float = 1.0,
    ) -> float:
        """Amplitude of one selected step generator at one tick."""

        if digit_count < 1:
            raise ValueError("digit_count must be >= 1")
        if not MatrixFractalNumber.cell_schedule(cell).is_active(tick):
            return 0.0
        return amplitude


def drop_every_nth_sample(
    samples: Iterable[SignalSample], n: int
) -> list[float | None]:
    """Return total amplitudes with each n-th sample removed."""

    if n < 2:
        raise ValueError("n must be >= 2")
    observed: list[float | None] = []
    for index, sample in enumerate(samples):
        observed.append(None if index % n == 0 else sample.total_amplitude)
    return observed
