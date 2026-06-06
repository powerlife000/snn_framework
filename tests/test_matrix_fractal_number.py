import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from snn_framework import ChannelAlphabet, MatrixFractalNumber


class MatrixFractalNumberTests(unittest.TestCase):
    def article_model(self) -> MatrixFractalNumber:
        return MatrixFractalNumber.article_348_alphabet()

    def test_mixed_radix_encoding_roundtrip(self) -> None:
        number = MatrixFractalNumber.from_contiguous_bands(width=5)
        value = 123_456
        digits = number.encode_digits(value, digit_count=4)
        self.assertTrue(all(0 <= digit < number.radix(index) for index, digit in enumerate(digits)))
        self.assertEqual(number.decode_digits(digits), value)

    def test_article_348_mixed_radix_digits(self) -> None:
        number = self.article_model()
        self.assertEqual(number.radix(0), 20)
        self.assertEqual(number.radix(1), 34)
        self.assertEqual(number.encode_digits(348, digit_count=2), [8, 17])
        self.assertEqual(number.decode_digits([8, 17]), 348)

    def test_article_348_digits_map_to_matrix_cells(self) -> None:
        number = self.article_model()
        cell_0 = number.digit_to_cell(digit_index=0, digit_value=8)
        cell_1 = number.digit_to_cell(digit_index=1, digit_value=17)

        self.assertEqual((cell_0.period_index, cell_0.period_ticks, cell_0.shift_value), (2, 4, 3))
        self.assertEqual((cell_1.period_index, cell_1.period_ticks, cell_1.shift_value), (2, 9, 2))
        self.assertEqual(cell_0.digit_value, 8)
        self.assertEqual(cell_1.digit_value, 17)

    def test_cells_decode_back_to_number(self) -> None:
        number = self.article_model()
        value = 348
        cells = number.encode_cells(value, digit_count=2)
        self.assertEqual(number.decode_cells(cells), value)

    def test_candidate_cells_lists_full_channel_alphabet(self) -> None:
        number = self.article_model()
        cells_0 = number.candidate_cells(digit_index=0)
        cells_1 = number.candidate_cells(digit_index=1)

        self.assertEqual(len(cells_0), 20)
        self.assertEqual(len(cells_1), 34)
        self.assertEqual(cells_0[0].period_ticks, 2)
        self.assertEqual(cells_0[-1].period_ticks, 6)
        self.assertEqual(cells_0[-1].shift_ticks, 5)
        self.assertEqual(cells_1[-1].period_ticks, 10)
        self.assertEqual(cells_1[-1].shift_ticks, 9)

    def test_more_significant_digit_channel_has_larger_period(self) -> None:
        number = MatrixFractalNumber.from_contiguous_bands(widths=[5, 5, 5])
        least_significant = number.digit_to_cell(digit_index=0, digit_value=0)
        more_significant = number.digit_to_cell(digit_index=1, digit_value=0)
        most_significant = number.digit_to_cell(digit_index=2, digit_value=0)

        self.assertLess(least_significant.period_ticks, more_significant.period_ticks)
        self.assertLess(more_significant.period_ticks, most_significant.period_ticks)

    def test_cell_active_windows_lists_ranges(self) -> None:
        number = self.article_model()
        cell = number.digit_to_cell(digit_index=0, digit_value=8)
        self.assertEqual(
            number.cell_active_windows(cell, ticks=24),
            [(5, 7), (9, 11), (13, 15), (17, 19), (21, 23)],
        )

    def test_active_width_is_half_period(self) -> None:
        number = self.article_model()
        cell = number.digit_to_cell(digit_index=1, digit_value=17)
        self.assertEqual(cell.shift_ticks, 2)
        self.assertEqual(cell.period_ticks, 9)
        self.assertEqual(cell.active_width_ticks, 4)
        self.assertEqual(number.cell_active_windows(cell, ticks=22), [(6, 11), (15, 20)])

    def test_zero_shift_starts_with_inactive_half_period(self) -> None:
        number = self.article_model()
        cell = number.digit_to_cell(digit_index=0, digit_value=5)
        schedule = number.cell_schedule(cell)
        self.assertEqual(
            [int(schedule.is_active(tick)) for tick in range(4)],
            [0, 0, 1, 1],
        )

    def test_signal_is_sum_of_channel_amplitudes(self) -> None:
        number = self.article_model()
        samples = number.signal(348, digit_count=2, ticks=18)
        self.assertEqual(len(samples), 18)
        for sample in samples:
            self.assertAlmostEqual(
                sample.total_amplitude, sum(sample.channel_amplitudes)
            )

    def test_cell_schedule_lists_active_ticks(self) -> None:
        number = self.article_model()
        cell = number.digit_to_cell(digit_index=1, digit_value=17)
        schedule = number.cell_schedule(cell)
        self.assertEqual(schedule.period_ticks, 9)
        self.assertEqual(schedule.shift_ticks, 2)
        self.assertEqual(schedule.active_width_ticks, 4)
        self.assertEqual(
            number.cell_active_ticks(cell, ticks=22),
            [6, 7, 8, 9, 10, 15, 16, 17, 18, 19],
        )

    def test_extract_cell_samples_uses_cell_mask(self) -> None:
        number = self.article_model()
        original = 348
        cells = number.encode_cells(original, digit_count=2)
        samples = number.signal(original, digit_count=2, ticks=24)
        observed = [sample.channel_amplitudes[0] for sample in samples]
        self.assertTrue(number.extract_cell_samples(observed, cell=cells[0]))

    def test_direct_step_signal_decoder(self) -> None:
        number = self.article_model()
        original = 348
        samples = number.signal(original, digit_count=2, ticks=32)
        channel_signals = [
            [sample.channel_amplitudes[digit_index] for sample in samples]
            for digit_index in range(2)
        ]
        result = number.decode_channel_signals(channel_signals)
        decoded_digits = result.digits
        self.assertEqual(number.decode_digits(decoded_digits), original)
        self.assertEqual(decoded_digits, (8, 17))

    def test_summed_signal_decoder_peels_channels(self) -> None:
        number = self.article_model()
        original = 348
        samples = number.signal(original, digit_count=2, ticks=32)
        observed = [sample.total_amplitude for sample in samples]
        result = number.decode_step_signal(observed, digit_count=2)
        self.assertEqual(result.number, original)
        self.assertEqual(result.digits, (8, 17))

    def test_summed_signal_decoder_restores_demo_number(self) -> None:
        number = MatrixFractalNumber.from_contiguous_bands(width=5)
        original = 2026
        samples = number.signal(original, digit_count=3, ticks=64)
        observed = [sample.total_amplitude for sample in samples]
        result = number.decode_step_signal(observed, digit_count=3)
        self.assertEqual(result.number, original)

    def test_recover_from_partial_signal_for_small_demo_range(self) -> None:
        number = self.article_model()
        original = 348
        samples = number.signal(original, digit_count=2, ticks=32)
        channel_signals = [
            [
                None if index % 7 == 0 else sample.channel_amplitudes[cell.digit_index]
                for index, sample in enumerate(samples)
            ]
            for cell in number.encode_cells(original, digit_count=2)
        ]
        result = number.decode_channel_signals(channel_signals)
        self.assertEqual(result.number, original)

    def test_custom_channel_alphabet_is_user_defined(self) -> None:
        number = MatrixFractalNumber(
            channel_alphabets=[
                ChannelAlphabet(periods=(3, 4, 5)),
                ChannelAlphabet(periods=(11, 12, 13, 14)),
            ]
        )

        self.assertEqual(number.radix(0), 12)
        self.assertEqual(number.radix(1), 50)
        cell = number.digit_to_cell(1, 35)
        self.assertEqual((cell.period_index, cell.period_ticks, cell.shift_value), (2, 13, 12))


if __name__ == "__main__":
    unittest.main()
