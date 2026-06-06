"""Diagonal matrix-channel fractal number representation.

Each digit channel owns a user-defined diagonal period/shift matrix. If channel
``i`` has contiguous periods ``P_i``, then every period row ``P`` has exactly
``P`` valid start delays ``S in [0, P - 1]``. The channel radix is the diagonal
matrix capacity:

``Base_i = sum(P for P in periods_i)``.

A digit selects a row (period) and a start delay by progressive subtraction:

``digit = sum(previous periods) + S``.

The generated channel is silent before ``S`` and then emits a half-duty
periodic step signal. The framework deliberately does not prescribe one global
period-band schedule; researchers provide channel alphabets that fit their
hardware constraints.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class ChannelAlphabet:
    """User-defined diagonal period/shift matrix for one digit channel."""

    periods: tuple[int, ...]
    shift_count: int | None = None

    def __init__(self, periods: Iterable[int], shift_count: int | None = None) -> None:
        period_tuple = tuple(int(period) for period in periods)
        if not period_tuple:
            raise ValueError("ChannelAlphabet periods must not be empty")
        if any(period < 2 for period in period_tuple):
            raise ValueError("ChannelAlphabet periods must be >= 2")
        if len(set(period_tuple)) != len(period_tuple):
            raise ValueError("ChannelAlphabet periods must be unique")
        if tuple(sorted(period_tuple)) != period_tuple:
            raise ValueError("ChannelAlphabet periods must be sorted")
        if any(right - left != 1 for left, right in zip(period_tuple, period_tuple[1:])):
            raise ValueError("ChannelAlphabet periods must be contiguous with step 1")
        if shift_count is not None:
            raise ValueError("shift_count is not used by the diagonal alphabet")

        object.__setattr__(self, "periods", period_tuple)
        object.__setattr__(self, "shift_count", None)

    @property
    def max_period(self) -> int:
        return max(self.periods)

    @property
    def radix(self) -> int:
        return sum(self.periods)


@dataclass(frozen=True)
class MatrixCell:
    """One selected cell in a channel period/shift matrix."""

    digit_index: int
    digit_value: int
    period_index: int
    shift_index: int
    shift_value: int
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


ChannelAlphabetRule = Callable[[int], ChannelAlphabet]


class MatrixFractalNumber:
    """Fractal number over user-defined channel matrices."""

    def __init__(
        self,
        period_levels: int | None = None,
        shift_levels: int | None = None,
        *,
        channel_alphabets: Sequence[ChannelAlphabet | Iterable[int]] | None = None,
        channel_rule: ChannelAlphabetRule | None = None,
        min_period_ticks: int = 2,
    ) -> None:
        if min_period_ticks < 2:
            raise ValueError("min_period_ticks must be >= 2")
        if channel_alphabets is not None and channel_rule is not None:
            raise ValueError("provide either channel_alphabets or channel_rule, not both")

        self.min_period_ticks = min_period_ticks
        self.period_levels = period_levels
        self.shift_levels = shift_levels
        self.base_period_ticks = 1
        self._finite_alphabets: tuple[ChannelAlphabet, ...] | None = None

        if channel_alphabets is not None:
            self._finite_alphabets = tuple(
                alphabet
                if isinstance(alphabet, ChannelAlphabet)
                else ChannelAlphabet(alphabet)
                for alphabet in channel_alphabets
            )
            if not self._finite_alphabets:
                raise ValueError("channel_alphabets must not be empty")
            self._channel_rule = self._alphabet_from_finite_list
        elif channel_rule is not None:
            self._channel_rule = channel_rule
        elif period_levels is not None and shift_levels is not None:
            self._channel_rule = self._legacy_fixed_width_rule(
                period_levels=period_levels,
                shift_levels=shift_levels,
                start=min_period_ticks,
            )
        else:
            self._channel_rule = self._contiguous_equal_width_rule(
                start=min_period_ticks,
                width=5,
            )
        self.base = self.radix(0)

    @classmethod
    def article_348_alphabet(cls) -> MatrixFractalNumber:
        """Return the two-channel alphabet used by the article's 348 example."""

        return cls(
            channel_alphabets=[
                ChannelAlphabet(range(2, 7)),
                ChannelAlphabet(range(7, 11)),
            ]
        )

    @classmethod
    def from_contiguous_bands(
        cls,
        *,
        start: int = 2,
        widths: Sequence[int] | None = None,
        width: int | None = None,
    ) -> MatrixFractalNumber:
        """Build finite or infinite non-overlapping contiguous period bands."""

        if widths is not None and width is not None:
            raise ValueError("provide either widths or width, not both")
        if widths is not None:
            alphabets: list[ChannelAlphabet] = []
            cursor = start
            for band_width in widths:
                if band_width < 1:
                    raise ValueError("band widths must be >= 1")
                alphabets.append(ChannelAlphabet(range(cursor, cursor + band_width)))
                cursor += band_width
            return cls(channel_alphabets=alphabets)
        if width is None:
            width = 5
        return cls(channel_rule=cls._contiguous_equal_width_rule(start=start, width=width))

    @classmethod
    def from_rule(cls, rule: ChannelAlphabetRule) -> MatrixFractalNumber:
        """Build a model from a user-provided channel alphabet rule."""

        return cls(channel_rule=rule)

    @staticmethod
    def _contiguous_equal_width_rule(*, start: int, width: int) -> ChannelAlphabetRule:
        if start < 2:
            raise ValueError("start must be >= 2")
        if width < 1:
            raise ValueError("width must be >= 1")

        def rule(digit_index: int) -> ChannelAlphabet:
            band_start = start + digit_index * width
            return ChannelAlphabet(range(band_start, band_start + width))

        return rule

    @staticmethod
    def _legacy_fixed_width_rule(
        *, period_levels: int, shift_levels: int, start: int
    ) -> ChannelAlphabetRule:
        if period_levels < 1:
            raise ValueError("period_levels must be >= 1")
        if shift_levels < 1:
            raise ValueError("shift_levels must be >= 1")

        def rule(digit_index: int) -> ChannelAlphabet:
            band_start = start + digit_index * period_levels
            return ChannelAlphabet(range(band_start, band_start + period_levels))

        return rule

    def _alphabet_from_finite_list(self, digit_index: int) -> ChannelAlphabet:
        if self._finite_alphabets is None:
            raise ValueError("finite alphabet list is not configured")
        if digit_index >= len(self._finite_alphabets):
            raise ValueError("digit_index is outside finite channel_alphabets")
        return self._finite_alphabets[digit_index]

    def channel_alphabet(self, digit_index: int) -> ChannelAlphabet:
        """Return the user-defined matrix alphabet for channel ``digit_index``."""

        if digit_index < 0:
            raise ValueError("digit_index must be non-negative")
        alphabet = self._channel_rule(digit_index)
        if not isinstance(alphabet, ChannelAlphabet):
            alphabet = ChannelAlphabet(alphabet)
        return alphabet

    def period_for_digit(self, digit_index: int) -> int:
        """Return the maximum period configured for channel ``i``."""

        return self.channel_alphabet(digit_index).max_period

    def radix(self, digit_index: int) -> int:
        """Return channel radix, equal to diagonal capacity ``sum(periods)``."""

        return self.channel_alphabet(digit_index).radix

    def digit_to_indices(
        self, digit_value: int, *, digit_index: int = 0
    ) -> tuple[int, int]:
        """Map one digit value to ``(period_index, shift_index)``."""

        alphabet = self.channel_alphabet(digit_index)
        if not 0 <= digit_value < alphabet.radix:
            raise ValueError("digit_value is outside channel radix")
        remaining = int(digit_value)
        for period_index, period in enumerate(alphabet.periods):
            if remaining < period:
                return period_index, remaining
            remaining -= period
        raise ValueError("digit_value is outside channel radix")

    def cell_indices_to_digit(
        self,
        period_index: int,
        shift_index: int,
        *,
        digit_index: int = 0,
    ) -> int:
        """Map ``(period_index, shift_index)`` back to one digit value."""

        alphabet = self.channel_alphabet(digit_index)
        if not 0 <= period_index < len(alphabet.periods):
            raise ValueError("period_index is outside channel alphabet")
        period = alphabet.periods[period_index]
        if not 0 <= shift_index < period:
            raise ValueError("shift_index is outside channel alphabet")
        return sum(alphabet.periods[:period_index]) + shift_index

    def encode_digits(self, number: int, digit_count: int | None = None) -> list[int]:
        """Convert a decimal number to little-endian mixed-radix digits.

        Index ``0`` is least significant and must map to the highest-frequency
        channel. Higher indices are more significant and lower-frequency.
        """

        if number < 0:
            raise ValueError("number must be non-negative")
        if digit_count is not None and digit_count < 1:
            raise ValueError("digit_count must be >= 1")

        digits: list[int] = []
        value = number
        index = 0
        while value or not digits:
            if digit_count is not None and index >= digit_count:
                raise ValueError("number does not fit into digit_count")
            radix = self.radix(index)
            value, digit = divmod(value, radix)
            digits.append(digit)
            index += 1

        if digit_count is not None:
            digits.extend([0] * (digit_count - len(digits)))
        return digits

    def decode_digits(self, digits: Sequence[int]) -> int:
        """Convert little-endian mixed-radix digits back to decimal.

        The input order is least-significant to most-significant. In the signal
        model that is also highest-frequency to lowest-frequency.
        """

        number = 0
        multiplier = 1
        for digit_index, digit in enumerate(digits):
            radix = self.radix(digit_index)
            if not 0 <= digit < radix:
                raise ValueError("digit is outside channel radix")
            number += int(digit) * multiplier
            multiplier *= radix
        return number

    def digit_to_cell(self, digit_index: int, digit_value: int) -> MatrixCell:
        """Map one mixed-radix digit to a selected matrix cell."""

        if digit_index < 0:
            raise ValueError("digit_index must be non-negative")
        alphabet = self.channel_alphabet(digit_index)
        if not 0 <= digit_value < alphabet.radix:
            raise ValueError("digit_value is outside channel matrix alphabet")

        period_index, shift_index = self.digit_to_indices(
            int(digit_value),
            digit_index=digit_index,
        )
        period_ticks = alphabet.periods[period_index]
        shift_ticks = shift_index
        active_width_ticks = period_ticks // 2
        return MatrixCell(
            digit_index=digit_index,
            digit_value=digit_value,
            period_index=period_index,
            shift_index=shift_index,
            shift_value=shift_index,
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
            for digit_value in range(self.radix(digit_index))
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
        """Return a simple diagnostic mask for one digit channel."""

        if digit_count < 1:
            raise ValueError("digit_count must be >= 1")
        if not 0 <= digit_index < digit_count:
            raise ValueError("digit_index must be inside digit_count")
        return ChannelSchedule(
            digit_index=digit_index,
            period_ticks=max(2, digit_count),
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
        """Recover one channel cell by matching valid matrix-cell masks."""

        if not any(value is not None and value >= threshold for value in residual):
            raise ValueError(f"no active segment for digit channel {digit_index}")

        best_cell: MatrixCell | None = None
        best_score: tuple[int, int, int, int] | None = None
        for candidate in self.candidate_cells(digit_index):
            schedule = self.cell_schedule(candidate)
            misses = 0
            hits = 0
            exact_hits = 0
            for tick, value in enumerate(residual):
                if value is None:
                    continue
                expected_active = schedule.is_active(tick)
                if not expected_active:
                    continue
                if value < threshold:
                    misses += 1
                else:
                    hits += 1
                    if value < amplitude + threshold:
                        exact_hits += 1

            score = (misses, -exact_hits, -hits, candidate.digit_value)
            if best_score is None or score < best_score:
                best_score = score
                best_cell = candidate

        if best_cell is None or best_score is None:
            raise ValueError(f"could not decode matrix cell for channel {digit_index}")
        return best_cell

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
                        (cell.period_index, cell.period_ticks, cell.shift_value)
                        for cell in cells
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
