"""Frequency-phase digit representation for the first SNN Framework prototype.

The module intentionally stays dependency-free so the mathematical core can be
used in notebooks, tests, and later SNN memory experiments without extra setup.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi
from typing import Iterable, Sequence


@dataclass(frozen=True)
class DigitCell:
    """One cell of a frequency-phase digit matrix."""

    frequency_level: int
    phase_level: int
    frequency_hz: float
    phase_rad: float
    amplitude: float
    probability: float
    target_bit: int

    @property
    def weighted_amplitude(self) -> float:
        return self.amplitude * self.probability


class FrequencyPhaseDigit:
    """A single channel/digit encoded by frequency levels and phase shifts.

    EN: The matrix is a finite discrete grid. Rows are frequency levels,
    columns are phase levels. Active cells carry amplitude and probability.
    Decoding compares the total weighted amplitude assigned to bit 0 and bit 1.

    RU: Матрица является конечной дискретной сеткой. Строки - уровни частоты,
    столбцы - уровни фазы. Активные ячейки несут амплитуду и вероятность.
    Декодирование сравнивает суммарную взвешенную амплитуду областей 0 и 1.

    * bit 0: phase before the threshold;
    * bit 1: phase at or after the threshold.
    """

    def __init__(
        self,
        digit_index: int,
        frequency_min_hz: float,
        frequency_max_hz: float,
        frequency_levels: int = 4,
        phase_levels: int = 8,
        phase_threshold: float = 0.5,
        default_amplitude: float = 1.0,
        default_probability: float = 1.0,
    ) -> None:
        if digit_index < 0:
            raise ValueError("digit_index must be non-negative")
        if frequency_min_hz <= 0 or frequency_max_hz <= 0:
            raise ValueError("frequencies must be positive")
        if frequency_min_hz > frequency_max_hz:
            raise ValueError("frequency_min_hz must be <= frequency_max_hz")
        if frequency_levels < 1:
            raise ValueError("frequency_levels must be >= 1")
        if phase_levels < 2:
            raise ValueError("phase_levels must be >= 2")
        if not 0.0 < phase_threshold < 1.0:
            raise ValueError("phase_threshold must be in (0, 1)")
        if default_amplitude < 0:
            raise ValueError("default_amplitude must be non-negative")
        if not 0.0 <= default_probability <= 1.0:
            raise ValueError("default_probability must be in [0, 1]")

        self.digit_index = digit_index
        self.frequency_min_hz = frequency_min_hz
        self.frequency_max_hz = frequency_max_hz
        self.frequency_levels = frequency_levels
        self.phase_levels = phase_levels
        self.phase_threshold = phase_threshold
        self.default_amplitude = default_amplitude
        self.default_probability = default_probability

    def frequency_values(self) -> list[float]:
        """Return discrete frequency levels for this digit."""

        if self.frequency_levels == 1:
            return [(self.frequency_min_hz + self.frequency_max_hz) / 2.0]
        step = (self.frequency_max_hz - self.frequency_min_hz) / (
            self.frequency_levels - 1
        )
        return [
            self.frequency_min_hz + level * step
            for level in range(self.frequency_levels)
        ]

    def phase_values(self, phase_shift: float = 0.0) -> list[float]:
        """Return phase levels in radians with an optional normalized shift."""

        shift = phase_shift % 1.0
        return [
            2.0 * pi * ((level / self.phase_levels + shift) % 1.0)
            for level in range(self.phase_levels)
        ]

    def matrix(
        self,
        bit: int,
        *,
        amplitude: float | None = None,
        probability: float | None = None,
        phase_shift: float = 0.0,
        inactive_amplitude: float = 0.0,
    ) -> list[list[DigitCell]]:
        """Build ``digit_matrix[frequency_level][phase_level]`` for a bit."""

        if bit not in (0, 1):
            raise ValueError("bit must be 0 or 1")
        amp = self.default_amplitude if amplitude is None else amplitude
        prob = self.default_probability if probability is None else probability
        if amp < 0 or inactive_amplitude < 0:
            raise ValueError("amplitudes must be non-negative")
        if not 0.0 <= prob <= 1.0:
            raise ValueError("probability must be in [0, 1]")

        frequencies = self.frequency_values()
        phases = self.phase_values(phase_shift)
        rows: list[list[DigitCell]] = []
        for frequency_level, frequency in enumerate(frequencies):
            row: list[DigitCell] = []
            for phase_level, phase in enumerate(phases):
                phase_fraction = phase / (2.0 * pi)
                phase_bit = int(phase_fraction >= self.phase_threshold)
                cell_amplitude = amp if phase_bit == bit else inactive_amplitude
                row.append(
                    DigitCell(
                        frequency_level=frequency_level,
                        phase_level=phase_level,
                        frequency_hz=frequency,
                        phase_rad=phase,
                        amplitude=cell_amplitude,
                        probability=prob,
                        target_bit=phase_bit,
                    )
                )
            rows.append(row)
        return rows

    def decode_bit(self, matrix: Sequence[Sequence[DigitCell]]) -> int:
        """Decode a bit by comparing weighted amplitudes assigned to 0 and 1."""

        zero_energy = 0.0
        one_energy = 0.0
        for cell in _iter_cells(matrix):
            if cell.target_bit == 1:
                one_energy += cell.weighted_amplitude
            else:
                zero_energy += cell.weighted_amplitude
        return int(one_energy >= zero_energy)

    def dominant_state(self, matrix: Sequence[Sequence[DigitCell]]) -> DigitCell:
        """Return the strongest matrix cell by amplitude and probability."""

        try:
            return max(_iter_cells(matrix), key=lambda cell: cell.weighted_amplitude)
        except ValueError as exc:
            raise ValueError("matrix must contain at least one DigitCell") from exc

    def encode_bit(self, bit: int, **kwargs: float) -> list[list[DigitCell]]:
        """Alias for ``matrix`` used by tests and notebooks."""

        return self.matrix(bit, **kwargs)

    def bit_grid(self, matrix: Sequence[Sequence[DigitCell]]) -> list[list[int]]:
        """Return a compact grid where active cells show their target bit.

        Inactive cells are marked as ``-1``. This is useful for notebook output:
        the reader sees which frequency/phase cells currently encode the digit.
        """

        return [
            [cell.target_bit if cell.amplitude > 0 else -1 for cell in row]
            for row in matrix
        ]

    def amplitude_grid(self, matrix: Sequence[Sequence[DigitCell]]) -> list[list[float]]:
        """Return only amplitudes from the frequency-phase matrix."""

        return [[cell.amplitude for cell in row] for row in matrix]

    def probability_grid(
        self, matrix: Sequence[Sequence[DigitCell]]
    ) -> list[list[float]]:
        """Return only probabilities from the frequency-phase matrix."""

        return [[cell.probability for cell in row] for row in matrix]


def _iter_cells(matrix: Sequence[Sequence[DigitCell]]) -> Iterable[DigitCell]:
    for row in matrix:
        for cell in row:
            yield cell
