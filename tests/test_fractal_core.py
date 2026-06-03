import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from snn_framework import AmbiguousDecodingError, FractalNumber, FrequencyPhaseDigit


class FractalNumberTests(unittest.TestCase):
    def test_default_periods_match_formula(self) -> None:
        number = FractalNumber(width=10)
        self.assertEqual([number.period(i) for i in range(10)], [1 << (i + 1) for i in range(10)])

    def test_function_matches_binary_counter_for_small_ranges(self) -> None:
        for width, limit in [(4, 16), (8, 256), (10, 1024)]:
            number = FractalNumber(width=width)
            for n in range(limit):
                bits = number.encode(n)
                expected = [(n >> i) & 1 for i in range(width)]
                self.assertEqual(bits, expected)
                self.assertEqual(number.decode(bits), n)
                self.assertEqual(number.decode_tick_o1(bits).tick, n)

    def test_matrix_restores_channel_rows(self) -> None:
        number = FractalNumber(width=4)
        matrix = number.matrix(rows=8)
        self.assertEqual(len(matrix), 8)
        self.assertEqual(matrix[5], [1, 0, 1, 0])

    def test_global_shift_supports_direct_decoding(self) -> None:
        width = 5
        global_shift = 7
        shifts = [global_shift % (1 << (i + 1)) for i in range(width)]
        number = FractalNumber(width=width, shifts=shifts)
        for tick in range(1 << width):
            result = number.decode_tick_o1(number.encode(tick))
            self.assertEqual(result.tick, tick)
            self.assertEqual(result.global_shift, global_shift)

    def test_non_global_shift_requires_research_decoder(self) -> None:
        number = FractalNumber(width=4, shifts=[0, 1, 0, 0])
        bits = number.encode(3)
        with self.assertRaises(AmbiguousDecodingError):
            number.decode_tick_o1(bits)
        self.assertIn(3, number.decode_tick_by_search(bits))

    def test_wave_sequence_contains_multichannel_samples(self) -> None:
        number = FractalNumber(width=3, probabilities=[1.0, 0.5, 0.25])
        samples = number.wave_sequence(ticks=4, samples_per_tick=6, clock_hz=10.0)
        self.assertEqual(len(samples), 24)
        self.assertEqual(len(samples[0].amplitudes), 3)
        self.assertEqual(samples[0].bits, (0, 0, 0))
        self.assertEqual(samples[6].bits, (1, 0, 0))

    def test_compression_report(self) -> None:
        report = FractalNumber(width=8).compression_report(rows=256)
        self.assertEqual(report["full_matrix_values"], 2048)
        self.assertEqual(report["generator_parameters"], 32)
        self.assertEqual(report["compression_ratio"], 64.0)


class FrequencyPhaseDigitTests(unittest.TestCase):
    def test_digit_matrix_shape_and_decoding(self) -> None:
        digit = FrequencyPhaseDigit(
            digit_index=0,
            frequency_min_hz=8.0,
            frequency_max_hz=12.0,
            frequency_levels=3,
            phase_levels=8,
        )
        matrix = digit.encode_bit(1)
        self.assertEqual(len(matrix), 3)
        self.assertEqual(len(matrix[0]), 8)
        self.assertEqual(digit.decode_bit(matrix), 1)

    def test_digit_decodes_zero_half_space(self) -> None:
        digit = FrequencyPhaseDigit(
            digit_index=1,
            frequency_min_hz=13.0,
            frequency_max_hz=30.0,
            frequency_levels=2,
            phase_levels=10,
        )
        matrix = digit.encode_bit(0, amplitude=0.8, probability=0.75)
        self.assertEqual(digit.decode_bit(matrix), 0)
        dominant = digit.dominant_state(matrix)
        self.assertAlmostEqual(dominant.weighted_amplitude, 0.6)

    def test_phase_shift_changes_active_cells_but_not_requested_bit(self) -> None:
        digit = FrequencyPhaseDigit(
            digit_index=2,
            frequency_min_hz=30.0,
            frequency_max_hz=45.0,
            frequency_levels=2,
            phase_levels=8,
        )
        shifted = digit.encode_bit(1, phase_shift=0.25)
        self.assertEqual(digit.decode_bit(shifted), 1)
        active_phase_levels = [
            cell.phase_level
            for row in shifted
            for cell in row
            if cell.amplitude > 0 and cell.target_bit == 1
        ]
        self.assertTrue(active_phase_levels)


if __name__ == "__main__":
    unittest.main()
