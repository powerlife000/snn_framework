"""Packet framing layer for matrix fractal numbers."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, log2
from typing import Sequence

from .matrix_fractal_number import MatrixCell, MatrixFractalNumber, SignalSample


@dataclass(frozen=True)
class PacketField:
    """One service or payload field in a packet."""

    name: str
    start_tick: int
    end_tick: int
    pattern: tuple[int, ...] | None
    description: str


@dataclass(frozen=True)
class PacketSample:
    """One sample of a full packet signal."""

    tick: int
    total_amplitude: float
    field_name: str
    payload_amplitude: float = 0.0


@dataclass(frozen=True)
class FractalPacketEncodeResult:
    """Encoded packet and the generator parameters used for its payload."""

    value: int
    sign: int
    absolute_value: int
    digit_count: int
    payload_digits: tuple[int, ...]
    payload_cells: tuple[MatrixCell, ...]
    fields: tuple[PacketField, ...]
    samples: tuple[PacketSample, ...]
    check_value: int
    method: str


@dataclass(frozen=True)
class FractalPacketDecodeResult:
    """Decoded packet result."""

    value: int
    sign: int
    absolute_value: int
    digit_count: int
    payload_digits: tuple[int, ...]
    payload_cells: tuple[MatrixCell, ...]
    payload_start_tick: int
    payload_end_tick: int
    check_value: int
    expected_check_value: int
    check_ok: bool
    method: str


class FractalSNNPacketCodec:
    """Encode and decode self-delimiting SNN packets with fractal payloads."""

    PREAMBLE = (1, 0, 1, 0, 1, 0, 1, 0)
    START_DELIMITER = (1, 1, 1, 0, 0, 1, 0)
    SIGN_POSITIVE = (1, 0)
    SIGN_NEGATIVE = (0, 1)
    SIGN_ZERO = (1, 1)
    PAYLOAD_START_GUARD = (0, 0, 0, 0)
    END_GUARD = (0, 0, 0, 0)
    END_DELIMITER = (1, 0, 0, 1, 1, 1, 0)

    def __init__(
        self,
        number: MatrixFractalNumber,
        *,
        service_amplitude: float = 1.0,
    ) -> None:
        if service_amplitude <= 0:
            raise ValueError("service_amplitude must be positive")
        self.number = number
        self.service_amplitude = service_amplitude

    @property
    def check_width(self) -> int:
        return max(1, ceil(log2(self.number.base)))

    def encode(
        self,
        value: int,
        digit_count: int | None = None,
        *,
        payload_ticks: int | None = None,
    ) -> FractalPacketEncodeResult:
        """Encode a signed integer as a framed fractal SNN packet."""

        sign = -1 if value < 0 else 1
        absolute_value = abs(value)
        digits = self.number.encode_digits(absolute_value, digit_count=digit_count)
        digit_count = len(digits)
        cells = tuple(self.number.encode_cells(absolute_value, digit_count=digit_count))
        required_payload_ticks = self._required_payload_ticks(cells)
        if payload_ticks is None:
            payload_ticks = required_payload_ticks
        if payload_ticks < required_payload_ticks:
            raise ValueError("payload_ticks is too short for direct payload decoding")

        check_value = sum(digits) % self.number.base
        check_pattern = self._int_to_service_bits(check_value, self.check_width)

        samples: list[PacketSample] = []
        fields: list[PacketField] = []

        self._append_service_field(
            samples,
            fields,
            "PREAMBLE",
            self.PREAMBLE,
            "receiver activation and local tick synchronization",
        )
        self._append_service_field(
            samples,
            fields,
            "START_DELIMITER",
            self.START_DELIMITER,
            "unique packet start marker",
        )
        self._append_service_field(
            samples,
            fields,
            "SIGN",
            self._sign_pattern(sign, absolute_value),
            "sign-magnitude sign code",
        )
        self._append_service_field(
            samples,
            fields,
            "PAYLOAD_START_GUARD",
            self.PAYLOAD_START_GUARD,
            "guard interval before payload_tick = 0",
        )
        self._append_payload_field(
            samples,
            fields,
            absolute_value,
            digit_count=digit_count,
            ticks=payload_ticks,
        )
        self._append_service_field(
            samples,
            fields,
            "END_GUARD",
            self.END_GUARD,
            "guard interval after fractal payload",
        )
        self._append_service_field(
            samples,
            fields,
            "END_DELIMITER",
            self.END_DELIMITER,
            "self-delimiting packet end marker",
        )
        self._append_service_field(
            samples,
            fields,
            "CHECK",
            check_pattern,
            "sum(payload digits) mod base",
        )

        return FractalPacketEncodeResult(
            value=value,
            sign=sign,
            absolute_value=absolute_value,
            digit_count=digit_count,
            payload_digits=tuple(digits),
            payload_cells=cells,
            fields=tuple(fields),
            samples=tuple(samples),
            check_value=check_value,
            method="fractal SNN packet v0",
        )

    def decode(self, samples: Sequence[float | PacketSample]) -> FractalPacketDecodeResult:
        """Decode a framed fractal SNN packet."""

        values = self._sample_values(samples)
        bits = self._service_bits(values)

        sync_pattern = self.PREAMBLE + self.START_DELIMITER
        sync_start = self._find_pattern(bits, sync_pattern)
        if sync_start is None:
            raise ValueError("PREAMBLE + START_DELIMITER not found")

        cursor = sync_start + len(sync_pattern)
        sign_pattern = tuple(bits[cursor : cursor + 2])
        sign = self._decode_sign(sign_pattern)
        cursor += 2

        self._expect_pattern(bits, cursor, self.PAYLOAD_START_GUARD, "PAYLOAD_START_GUARD")
        cursor += len(self.PAYLOAD_START_GUARD)
        payload_start_tick = cursor

        end_pattern = self.END_GUARD + self.END_DELIMITER
        candidate_errors: list[ValueError] = []
        check_mismatch_seen = False
        search_from = payload_start_tick
        while True:
            end_start = self._find_pattern(bits, end_pattern, start=search_from)
            if end_start is None:
                break

            check_start = end_start + len(end_pattern)
            check_end = check_start + self.check_width
            if check_end > len(bits):
                candidate_errors.append(ValueError("CHECK field is incomplete"))
                break

            payload_signal = values[payload_start_tick:end_start]
            check_value = self._service_bits_to_int(bits[check_start:check_end])
            try:
                payload_result = self.number.decode_step_signal(
                    payload_signal,
                    digit_count=self._infer_digit_count(payload_signal),
                )
            except ValueError as error:
                candidate_errors.append(error)
                search_from = end_start + 1
                continue

            digits = payload_result.digits
            expected_check_value = sum(digits) % self.number.base
            if check_value != expected_check_value:
                check_mismatch_seen = True
                search_from = end_start + 1
                continue

            absolute_value = payload_result.number
            value = absolute_value * sign
            cells = tuple(self.number.encode_cells(absolute_value, digit_count=len(digits)))

            return FractalPacketDecodeResult(
                value=value,
                sign=sign,
                absolute_value=absolute_value,
                digit_count=len(digits),
                payload_digits=digits,
                payload_cells=cells,
                payload_start_tick=payload_start_tick,
                payload_end_tick=end_start,
                check_value=check_value,
                expected_check_value=expected_check_value,
                check_ok=True,
                method="fractal SNN packet v0 decoder",
            )

        if check_mismatch_seen:
            raise ValueError("CHECK mismatch")
        if candidate_errors:
            raise candidate_errors[-1]
        raise ValueError("END_GUARD + END_DELIMITER not found")

    def _append_service_field(
        self,
        samples: list[PacketSample],
        fields: list[PacketField],
        name: str,
        pattern: Sequence[int],
        description: str,
    ) -> None:
        start = len(samples)
        for bit in pattern:
            samples.append(
                PacketSample(
                    tick=len(samples),
                    total_amplitude=self.service_amplitude * int(bit),
                    field_name=name,
                    payload_amplitude=0.0,
                )
            )
        fields.append(
            PacketField(
                name=name,
                start_tick=start,
                end_tick=len(samples),
                pattern=tuple(int(bit) for bit in pattern),
                description=description,
            )
        )

    def _append_payload_field(
        self,
        samples: list[PacketSample],
        fields: list[PacketField],
        absolute_value: int,
        *,
        digit_count: int,
        ticks: int,
    ) -> None:
        start = len(samples)
        payload = self.number.signal(absolute_value, digit_count=digit_count, ticks=ticks)
        for sample in payload:
            samples.append(
                PacketSample(
                    tick=len(samples),
                    total_amplitude=sample.total_amplitude,
                    field_name="FRACTAL_PAYLOAD",
                    payload_amplitude=sample.total_amplitude,
                )
            )
        fields.append(
            PacketField(
                name="FRACTAL_PAYLOAD",
                start_tick=start,
                end_tick=len(samples),
                pattern=None,
                description="summed matrix fractal number payload",
            )
        )

    @staticmethod
    def _required_payload_ticks(cells: Sequence[MatrixCell]) -> int:
        if not cells:
            raise ValueError("at least one payload cell is required")
        return max(cell.shift_ticks + cell.period_ticks for cell in cells) + 1

    @classmethod
    def _sign_pattern(cls, sign: int, absolute_value: int) -> tuple[int, ...]:
        if absolute_value == 0:
            return cls.SIGN_ZERO
        return cls.SIGN_NEGATIVE if sign < 0 else cls.SIGN_POSITIVE

    @classmethod
    def _decode_sign(cls, pattern: Sequence[int]) -> int:
        pattern_tuple = tuple(int(bit) for bit in pattern)
        if pattern_tuple == cls.SIGN_POSITIVE:
            return 1
        if pattern_tuple == cls.SIGN_NEGATIVE:
            return -1
        if pattern_tuple == cls.SIGN_ZERO:
            return 1
        raise ValueError("invalid SIGN field")

    def _int_to_service_bits(self, value: int, width: int) -> tuple[int, ...]:
        if not 0 <= value < (1 << width):
            raise ValueError("value does not fit service bit width")
        return tuple((value >> index) & 1 for index in reversed(range(width)))

    @staticmethod
    def _service_bits_to_int(bits: Sequence[int]) -> int:
        value = 0
        for bit in bits:
            if bit not in (0, 1):
                raise ValueError("service bits must contain only 0 and 1")
            value = (value << 1) | int(bit)
        return value

    @staticmethod
    def _sample_values(samples: Sequence[float | PacketSample]) -> list[float]:
        values: list[float] = []
        for sample in samples:
            if isinstance(sample, PacketSample):
                values.append(float(sample.total_amplitude))
            else:
                values.append(float(sample))
        if not values:
            raise ValueError("packet samples must not be empty")
        return values

    def _service_bits(self, values: Sequence[float]) -> list[int]:
        threshold = self.service_amplitude / 2.0
        return [int(value >= threshold) for value in values]

    @staticmethod
    def _find_pattern(
        bits: Sequence[int],
        pattern: Sequence[int],
        *,
        start: int = 0,
    ) -> int | None:
        pattern_tuple = tuple(pattern)
        limit = len(bits) - len(pattern_tuple) + 1
        for index in range(start, max(start, limit)):
            if tuple(bits[index : index + len(pattern_tuple)]) == pattern_tuple:
                return index
        return None

    @staticmethod
    def _expect_pattern(
        bits: Sequence[int],
        start: int,
        pattern: Sequence[int],
        name: str,
    ) -> None:
        end = start + len(pattern)
        if tuple(bits[start:end]) != tuple(pattern):
            raise ValueError(f"{name} mismatch")

    def _infer_digit_count(self, payload_signal: Sequence[float]) -> int:
        digits = 0
        residual = [float(value) for value in payload_signal]
        threshold = self.service_amplitude / 2.0
        while any(value >= threshold for value in residual):
            cell = self.number._decode_next_cell_from_residual(
                residual,
                digit_index=digits,
                amplitude=self.service_amplitude,
                threshold=threshold,
            )
            schedule = self.number.cell_schedule(cell)
            for tick, value in enumerate(residual):
                if schedule.is_active(tick):
                    residual[tick] = value - self.service_amplitude
            digits += 1
        if digits < 1:
            raise ValueError("payload does not contain fractal channels")
        return digits
