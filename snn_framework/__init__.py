"""SNN Framework experimental core."""

from .fractal_number import (
    ChannelParameters,
    FractalNumber,
    WaveSample,
    decimal_to_binary_bits,
    decode_decimal,
    encode_decimal,
)
from .frequency_phase_digit import DigitCell, FrequencyPhaseDigit
from .fractal_packet import (
    FractalPacketDecodeResult,
    FractalPacketEncodeResult,
    FractalSNNPacketCodec,
    PacketField,
    PacketSample,
)
from .matrix_fractal_number import (
    ChannelSchedule,
    DirectDecodeResult,
    MatrixCell,
    MatrixFractalNumber,
    SignalSample,
    drop_every_nth_sample,
)
from .o1_decoder import AmbiguousDecodingError, O1DecodeResult

__all__ = [
    "AmbiguousDecodingError",
    "ChannelParameters",
    "ChannelSchedule",
    "DirectDecodeResult",
    "DigitCell",
    "FractalNumber",
    "FractalPacketDecodeResult",
    "FractalPacketEncodeResult",
    "FractalSNNPacketCodec",
    "FrequencyPhaseDigit",
    "MatrixCell",
    "MatrixFractalNumber",
    "O1DecodeResult",
    "PacketField",
    "PacketSample",
    "SignalSample",
    "WaveSample",
    "decimal_to_binary_bits",
    "decode_decimal",
    "drop_every_nth_sample",
    "encode_decimal",
]
