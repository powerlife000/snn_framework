import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from snn_framework import FractalSNNPacketCodec, MatrixFractalNumber


class FractalSNNPacketCodecTests(unittest.TestCase):
    def setUp(self) -> None:
        self.number = MatrixFractalNumber.article_348_alphabet()
        self.codec = FractalSNNPacketCodec(self.number)

    def test_positive_number_roundtrip(self) -> None:
        encoded = self.codec.encode(348, digit_count=2)
        decoded = self.codec.decode(encoded.samples)

        self.assertEqual(decoded.value, 348)
        self.assertEqual(decoded.sign, 1)
        self.assertEqual(decoded.payload_digits, encoded.payload_digits)
        self.assertTrue(decoded.check_ok)

    def test_negative_number_roundtrip(self) -> None:
        encoded = self.codec.encode(-348, digit_count=2)
        decoded = self.codec.decode(encoded.samples)

        self.assertEqual(decoded.value, -348)
        self.assertEqual(decoded.sign, -1)
        self.assertEqual(decoded.absolute_value, 348)
        self.assertEqual(decoded.payload_digits, encoded.payload_digits)

    def test_different_digit_counts_roundtrip(self) -> None:
        short_packet = self.codec.encode(18, digit_count=1)
        long_packet = self.codec.encode(-348, digit_count=2)

        short_decoded = self.codec.decode(short_packet.samples)
        long_decoded = self.codec.decode(long_packet.samples)

        self.assertEqual(short_decoded.value, 18)
        self.assertEqual(long_decoded.value, -348)
        self.assertEqual(short_decoded.payload_digits, short_packet.payload_digits)
        self.assertEqual(long_decoded.payload_digits, long_packet.payload_digits)

    def test_decode_rejects_corrupted_start_delimiter(self) -> None:
        encoded = self.codec.encode(348, digit_count=2)
        samples = [sample.total_amplitude for sample in encoded.samples]
        start_field = next(
            field for field in encoded.fields if field.name == "START_DELIMITER"
        )
        samples[start_field.start_tick] = 0.0

        with self.assertRaisesRegex(ValueError, "START_DELIMITER"):
            self.codec.decode(samples)

    def test_decode_rejects_corrupted_check(self) -> None:
        encoded = self.codec.encode(348, digit_count=2)
        samples = [sample.total_amplitude for sample in encoded.samples]
        check_field = next(field for field in encoded.fields if field.name == "CHECK")
        samples[check_field.start_tick] = 1.0 - samples[check_field.start_tick]

        with self.assertRaisesRegex(ValueError, "CHECK mismatch"):
            self.codec.decode(samples)

    def test_decoded_payload_cells_match_encoded_cells(self) -> None:
        encoded = self.codec.encode(-348, digit_count=2)
        decoded = self.codec.decode(encoded.samples)

        self.assertEqual(decoded.payload_cells, encoded.payload_cells)


if __name__ == "__main__":
    unittest.main()
