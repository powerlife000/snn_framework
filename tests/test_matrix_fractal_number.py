import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from snn_framework import MatrixFractalNumber


class MatrixFractalNumberTests(unittest.TestCase):
    def test_matrix_radix_encoding_roundtrip(self) -> None:
        number = MatrixFractalNumber(period_levels=4, shift_levels=8)
        value = 123_456
        digits = number.encode_digits(value)
        self.assertTrue(all(0 <= digit < 32 for digit in digits))
        self.assertEqual(number.decode_digits(digits), value)

    def test_digits_map_to_period_shift_cells(self) -> None:
        number = MatrixFractalNumber(period_levels=4, shift_levels=8)
        cell = number.digit_to_cell(digit_index=0, digit_value=21)
        self.assertEqual(cell.period_index, 2)
        self.assertEqual(cell.shift_index, 5)
        self.assertEqual(cell.digit_value, 21)

    def test_shift_column_is_same_phase_across_period_rows(self) -> None:
        number = MatrixFractalNumber(period_levels=2, shift_levels=4)
        cell_3 = number.digit_to_cell(digit_index=0, digit_value=3)
        cell_7 = number.digit_to_cell(digit_index=0, digit_value=7)
        self.assertEqual(cell_3.shift_index, cell_7.shift_index)
        self.assertEqual(cell_3.shift_ticks, 6)
        self.assertEqual(cell_7.shift_ticks, 12)

    def test_cells_decode_back_to_number(self) -> None:
        number = MatrixFractalNumber(period_levels=3, shift_levels=5)
        value = 2026
        cells = number.encode_cells(value)
        self.assertEqual(number.decode_cells(cells), value)

    def test_candidate_cells_lists_full_channel_alphabet(self) -> None:
        number = MatrixFractalNumber(period_levels=2, shift_levels=4)
        cells = number.candidate_cells(digit_index=1)
        self.assertEqual([cell.digit_value for cell in cells], list(range(8)))
        self.assertEqual(cells[0].period_ticks, 24)
        self.assertEqual(cells[7].period_ticks, 32)
        self.assertEqual(cells[3].shift_ticks, 18)
        self.assertEqual(cells[7].shift_ticks, 24)

    def test_more_significant_digit_channel_has_larger_period(self) -> None:
        number = MatrixFractalNumber(period_levels=2, shift_levels=4)
        least_significant = number.digit_to_cell(digit_index=0, digit_value=0)
        more_significant = number.digit_to_cell(digit_index=1, digit_value=0)
        most_significant = number.digit_to_cell(digit_index=2, digit_value=0)

        self.assertLess(least_significant.period_ticks, more_significant.period_ticks)
        self.assertLess(more_significant.period_ticks, most_significant.period_ticks)

    def test_cell_active_windows_lists_ranges(self) -> None:
        number = MatrixFractalNumber(period_levels=2, shift_levels=4)
        cell = number.digit_to_cell(digit_index=0, digit_value=2)
        self.assertEqual(
            number.cell_active_windows(cell, ticks=24),
            [(8, 12), (16, 20)],
        )

    def test_active_width_is_half_period(self) -> None:
        number = MatrixFractalNumber(period_levels=2, shift_levels=4)
        cell = number.digit_to_cell(digit_index=0, digit_value=2)
        self.assertEqual(cell.shift_ticks, 4)
        self.assertEqual(cell.period_ticks, 8)
        self.assertEqual(cell.active_width_ticks, 4)
        self.assertEqual(number.cell_active_windows(cell, ticks=16), [(8, 12)])

    def test_zero_shift_starts_with_inactive_half_period(self) -> None:
        number = MatrixFractalNumber(period_levels=2, shift_levels=4)
        cell = number.digit_to_cell(digit_index=0, digit_value=0)
        schedule = number.cell_schedule(cell)
        self.assertEqual(
            [int(schedule.is_active(tick)) for tick in range(8)],
            [0, 0, 0, 0, 1, 1, 1, 1],
        )

    def test_signal_is_sum_of_channel_amplitudes(self) -> None:
        number = MatrixFractalNumber(period_levels=2, shift_levels=4)
        samples = number.signal(37, digit_count=3, ticks=12)
        self.assertEqual(len(samples), 12)
        for sample in samples:
            self.assertAlmostEqual(
                sample.total_amplitude, sum(sample.channel_amplitudes)
            )
        self.assertEqual(
            [sample.total_amplitude for sample in samples[:12]],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        )

    def test_cell_schedule_lists_active_ticks(self) -> None:
        number = MatrixFractalNumber(period_levels=2, shift_levels=4)
        cell = number.digit_to_cell(digit_index=0, digit_value=2)
        schedule = number.cell_schedule(cell)
        self.assertEqual(schedule.period_ticks, 8)
        self.assertEqual(schedule.shift_ticks, 4)
        self.assertEqual(schedule.active_width_ticks, 4)
        self.assertEqual(
            number.cell_active_ticks(cell, ticks=24),
            [8, 9, 10, 11, 16, 17, 18, 19],
        )

    def test_extract_cell_samples_uses_cell_mask(self) -> None:
        number = MatrixFractalNumber(period_levels=2, shift_levels=4)
        original = 229
        cells = number.encode_cells(original, digit_count=3)
        samples = number.signal(original, digit_count=3, ticks=96)
        observed = [sample.channel_amplitudes[0] for sample in samples]
        self.assertEqual(
            number.extract_cell_samples(observed, cell=cells[0]),
            [1] * 44,
        )

    def test_direct_step_signal_decoder(self) -> None:
        number = MatrixFractalNumber(period_levels=2, shift_levels=4)
        original = 229
        samples = number.signal(original, digit_count=3, ticks=96)
        channel_signals = [
            [sample.channel_amplitudes[digit_index] for sample in samples]
            for digit_index in range(3)
        ]
        result = number.decode_channel_signals(channel_signals)
        decoded_digits = result.digits
        self.assertEqual(number.decode_digits(decoded_digits), original)
        self.assertEqual(decoded_digits, (5, 4, 3))

    def test_summed_signal_decoder_peels_channels(self) -> None:
        number = MatrixFractalNumber(period_levels=2, shift_levels=4)
        original = 229
        samples = number.signal(original, digit_count=3, ticks=96)
        observed = [sample.total_amplitude for sample in samples]
        result = number.decode_step_signal(observed, digit_count=3)
        self.assertEqual(result.number, original)
        self.assertEqual(result.digits, (5, 4, 3))

    def test_summed_signal_decoder_restores_demo_number(self) -> None:
        number = MatrixFractalNumber(period_levels=2, shift_levels=4)
        original = 2026
        samples = number.signal(original, digit_count=4, ticks=128)
        observed = [sample.total_amplitude for sample in samples]
        result = number.decode_step_signal(observed, digit_count=4)
        self.assertEqual(result.number, original)
        self.assertEqual(result.digits, (2, 5, 7, 3))

    def test_recover_from_partial_signal_for_small_demo_range(self) -> None:
        number = MatrixFractalNumber(period_levels=2, shift_levels=4)
        original = 229
        samples = number.signal(original, digit_count=3, ticks=96)
        channel_signals = [
            [
                None if index % 7 == 0 else sample.channel_amplitudes[cell.digit_index]
                for index, sample in enumerate(samples)
            ]
            for cell in number.encode_cells(original, digit_count=3)
        ]
        result = number.decode_channel_signals(channel_signals)
        self.assertEqual(result.number, original)


if __name__ == "__main__":
    unittest.main()
