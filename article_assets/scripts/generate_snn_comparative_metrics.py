"""Generate multistream matrix-fractal vs binary-serial article metrics.

The comparison uses equal numbers of physical streams for both methods. For the
matrix-fractal payload, the input bit payload is split across streams and each
stream restarts its period hierarchy from the fastest digit channel.
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from snn_framework import MatrixFractalNumber
try:
    from .dynamic_alphabet_helpers import (
        capacity_bits,
        contiguous_equal_width,
        digit_count_for_payload,
        required_payload_ticks,
        worst_case_value,
    )
except ImportError:
    from dynamic_alphabet_helpers import (
        capacity_bits,
        contiguous_equal_width,
        digit_count_for_payload,
        required_payload_ticks,
        worst_case_value,
    )


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs"


def single_stream_fractal_latency_ticks(
    payload_bits: int,
    *,
    model: MatrixFractalNumber | None = None,
) -> tuple[int, int, int]:
    """Return ``(latency_ticks, digit_count, payload_capacity_bits)`` for one stream.

    ``payload_bits`` may not be divisible by ``log2(base)``. In that case the
    matrix-fractal payload allocates one extra digit; ``payload_capacity_bits``
    records the representable payload size for the selected digit count.
    """

    if model is None:
        model = contiguous_equal_width(width=8)
    digit_count = digit_count_for_payload(model, payload_bits)
    payload_capacity_bits = int(math.floor(capacity_bits(model, digit_count)))
    value = worst_case_value(model, digit_count)
    cells = model.encode_cells(value, digit_count=digit_count)
    return required_payload_ticks(cells), digit_count, payload_capacity_bits


def multistream_fractal_metrics(
    payload_bits: int,
    physical_streams: int,
    *,
    model: MatrixFractalNumber | None = None,
) -> dict[str, float | int | str]:
    """Compute parallel matrix-fractal transfer metrics.

    The payload is split evenly across physical streams. Each stream encodes its
    own segment, so its digit hierarchy starts from the fastest period band.
    """

    segment_bits = math.ceil(payload_bits / physical_streams)
    latency_ticks, digit_count, segment_capacity_bits = single_stream_fractal_latency_ticks(
        segment_bits,
        model=model,
    )
    stream_ticks = latency_ticks * physical_streams
    return {
        "method": "matrix_channel_width8_multistream",
        "label": f"Matrix channel width=8, N={physical_streams}",
        "payload_bits": payload_bits,
        "physical_streams": physical_streams,
        "segment_bits": segment_bits,
        "segment_capacity_bits": segment_capacity_bits,
        "digit_count_per_stream": digit_count,
        "latency_ticks": latency_ticks,
        "stream_ticks": stream_ticks,
        "id_bits_per_stream_tick": payload_bits / stream_ticks,
    }


def binary_serial_metrics(
    payload_bits: int,
    physical_streams: int,
) -> dict[str, float | int | str]:
    """Compute equal-stream binary serial reference metrics."""

    segment_bits = math.ceil(payload_bits / physical_streams)
    latency_ticks = segment_bits
    stream_ticks = latency_ticks * physical_streams
    return {
        "method": "binary_serial_multistream",
        "label": f"Binary serial, N={physical_streams}",
        "payload_bits": payload_bits,
        "physical_streams": physical_streams,
        "segment_bits": segment_bits,
        "segment_capacity_bits": segment_bits,
        "digit_count_per_stream": "",
        "latency_ticks": latency_ticks,
        "stream_ticks": stream_ticks,
        "id_bits_per_stream_tick": payload_bits / stream_ticks,
    }


def comparative_rows() -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    payload_sizes = [128, 256, 512, 1024, 2048, 4096, 8192]
    stream_counts = [1, 4, 8, 16, 64]
    model = contiguous_equal_width(width=8)

    for payload_bits in payload_sizes:
        for physical_streams in stream_counts:
            rows.append(binary_serial_metrics(payload_bits, physical_streams))
            rows.append(
                multistream_fractal_metrics(
                    payload_bits,
                    physical_streams,
                    model=model,
                )
            )
    return rows


def write_csv(rows: list[dict[str, float | int | str]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "snn_comparative_metrics.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_latency(rows: list[dict[str, float | int | str]]) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    styles = [
        ("binary_serial_multistream", 1, "^", "darkgreen", "--"),
        ("matrix_channel_width8_multistream", 1, "s", "navy", "-"),
        ("binary_serial_multistream", 8, "^", "limegreen", "--"),
        ("matrix_channel_width8_multistream", 8, "s", "royalblue", "-"),
        ("binary_serial_multistream", 16, "^", "olive", "--"),
        ("matrix_channel_width8_multistream", 16, "s", "deepskyblue", "-"),
    ]
    for method, streams, marker, color, linestyle in styles:
        group = [
            row
            for row in rows
            if row["method"] == method and row["physical_streams"] == streams
        ]
        ax.plot(
            [row["payload_bits"] for row in group],
            [row["latency_ticks"] for row in group],
            label=str(group[0]["label"]),
            marker=marker,
            color=color,
            linestyle=linestyle,
        )

    ax.set_yscale("log", base=10)
    ax.set_xlabel("Payload size, bits")
    ax.set_ylabel("Latency, ticks")
    ax.set_title("Multistream payload transmission: latency")
    ax.legend()
    ax.grid(True, which="both", linestyle="--", alpha=0.5)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "figure_3_comparative_latency.png", dpi=180)
    plt.close(fig)


def plot_information_density(rows: list[dict[str, float | int | str]]) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    styles = [
        ("binary_serial_multistream", 1, "^", "darkgreen", "--"),
        ("matrix_channel_width8_multistream", 1, "s", "navy", "-"),
        ("binary_serial_multistream", 8, "^", "limegreen", "--"),
        ("matrix_channel_width8_multistream", 8, "s", "royalblue", "-"),
        ("binary_serial_multistream", 16, "^", "olive", "--"),
        ("matrix_channel_width8_multistream", 16, "s", "deepskyblue", "-"),
    ]
    for method, streams, marker, color, linestyle in styles:
        group = [
            row
            for row in rows
            if row["method"] == method and row["physical_streams"] == streams
        ]
        ax.plot(
            [row["payload_bits"] for row in group],
            [row["id_bits_per_stream_tick"] for row in group],
            label=str(group[0]["label"]),
            marker=marker,
            color=color,
            linestyle=linestyle,
        )

    ax.set_yscale("log", base=10)
    ax.set_xlabel("Payload size, bits")
    ax.set_ylabel("Information density, bits / stream-tick")
    ax.set_title("Multistream payload transmission: information density")
    ax.legend()
    ax.grid(True, which="both", linestyle="--", alpha=0.5)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "figure_4_comparative_id.png", dpi=180)
    plt.close(fig)


def main() -> None:
    rows = comparative_rows()
    write_csv(rows)
    plot_latency(rows)
    plot_information_density(rows)
    print("Wrote comparative SNN-channel metrics to article_assets/outputs")


if __name__ == "__main__":
    main()
