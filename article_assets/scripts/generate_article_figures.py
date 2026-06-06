"""Generate final article figures for the matrix-fractal number paper."""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from snn_framework import MatrixCell, MatrixFractalNumber
try:
    from .dynamic_alphabet_helpers import (
        capacity_bits,
        contiguous_equal_width,
        digit_count_for_payload,
        required_payload_ticks,
        worst_case_value,
    )
    from .generate_alphabet_sweep_metrics import sweep_rows, write_csv as write_sweep_csv
    from .generate_storage_metrics import storage_rows, write_csv as write_storage_csv
except ImportError:
    from dynamic_alphabet_helpers import (
        capacity_bits,
        contiguous_equal_width,
        digit_count_for_payload,
        required_payload_ticks,
        worst_case_value,
    )
    from generate_alphabet_sweep_metrics import sweep_rows, write_csv as write_sweep_csv
    from generate_storage_metrics import storage_rows, write_csv as write_storage_csv


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs"
ARTICLE_DPI = 220
BLUE = "#2563EB"
ORANGE = "#F97316"
GREEN = "#16A34A"
RED = "#DC2626"
BLACK = "#111827"
GREY = "#6B7280"


plt.rcParams.update(
    {
        "axes.grid": True,
        "grid.alpha": 0.25,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 10,
    }
)


def make_demo_signal(value: int = 348, digit_count: int = 2, ticks: int | None = None):
    model = MatrixFractalNumber.article_348_alphabet()
    cells = model.encode_cells(value, digit_count=digit_count)
    if ticks is None:
        ticks = required_payload_ticks(cells)
    samples = model.signal(value, digit_count=digit_count, ticks=ticks)
    channel_series = [
        [sample.channel_amplitudes[channel] for sample in samples]
        for channel in range(digit_count)
    ]
    summed = [sample.total_amplitude for sample in samples]
    return model, cells, channel_series, summed


def _cell_waveform(model: MatrixFractalNumber, cell: MatrixCell, ticks: int) -> list[float]:
    schedule = model.cell_schedule(cell)
    return [1.0 if schedule.is_active(tick) else 0.0 for tick in range(ticks)]


def _first_active_tick(model: MatrixFractalNumber, cell: MatrixCell, ticks: int) -> int:
    active_ticks = model.cell_active_ticks(cell, ticks=ticks)
    if not active_ticks:
        raise ValueError(f"cell {cell} has no active ticks in the selected window")
    return active_ticks[0]


def _draw_alphabet_cell_grid(
    model: MatrixFractalNumber,
    cell: MatrixCell,
    ax: plt.Axes,
    *,
    title: str,
) -> None:
    alphabet = model.channel_alphabet(cell.digit_index)
    max_shift = alphabet.max_period - 1
    digit_value = 0

    for y, period in enumerate(alphabet.periods):
        for shift in range(max_shift + 1):
            is_valid = shift < period
            is_selected = is_valid and period == cell.period_ticks and shift == cell.shift_ticks
            facecolor = "#DBEAFE" if is_valid else "#F3F4F6"
            edgecolor = "#1F2937" if is_valid else "#D1D5DB"
            linewidth = 1.0
            if is_selected:
                facecolor = "#FEE2E2"
                edgecolor = RED
                linewidth = 2.5

            rect = plt.Rectangle(
                (shift - 0.5, y - 0.5),
                1,
                1,
                facecolor=facecolor,
                edgecolor=edgecolor,
                linewidth=linewidth,
            )
            ax.add_patch(rect)
            if is_valid:
                ax.text(
                    shift,
                    y,
                    str(digit_value),
                    ha="center",
                    va="center",
                    color=RED if is_selected else "#1E3A8A",
                    fontsize=9,
                    weight="bold" if is_selected else "normal",
                )
                digit_value += 1
            else:
                ax.text(shift, y, "x", ha="center", va="center", color="#9CA3AF", fontsize=8)

    selected_y = list(alphabet.periods).index(cell.period_ticks)
    ax.scatter(
        [cell.shift_ticks],
        [selected_y],
        s=520,
        facecolors="none",
        edgecolors=RED,
        linewidths=3,
    )
    ax.text(
        cell.shift_ticks,
        selected_y - 0.45,
        f"selected: V={cell.digit_value}",
        ha="center",
        va="bottom",
        color=RED,
        fontsize=9,
        weight="bold",
    )
    ax.set_title(title)
    ax.set_xlim(-0.5, max_shift + 0.5)
    ax.set_ylim(len(alphabet.periods) - 0.5, -0.5)
    ax.set_aspect("equal")
    ax.set_xticks(range(max_shift + 1), labels=[str(shift) for shift in range(max_shift + 1)])
    ax.set_yticks(range(len(alphabet.periods)), labels=[str(period) for period in alphabet.periods])
    ax.set_xlabel("shift S")
    ax.set_ylabel("period P")
    ax.grid(False)


def plot_diagonal_alphabet() -> None:
    """Figure 1: diagonal alphabet grids and selected cells for V=348."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    model, cells, _, _ = make_demo_signal()

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6))
    _draw_alphabet_cell_grid(
        model,
        cells[0],
        axes[0],
        title="Channel 0 alphabet: periods 2..6",
    )
    _draw_alphabet_cell_grid(
        model,
        cells[1],
        axes[1],
        title="Channel 1 alphabet: periods 7..10",
    )
    fig.suptitle(
        "Figure 1. Diagonal fractal alphabet and selected cells for V=348",
        fontsize=14,
        weight="bold",
    )
    fig.text(
        0.5,
        0.01,
        "A valid row with period P contains exactly P legal shifts S=0..P-1; red rings mark (P0=4,S0=3) and (P1=9,S1=2).",
        ha="center",
        color=GREY,
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(OUTPUT_DIR / "figure_1_diagonal_alphabet.png", dpi=ARTICLE_DPI)
    plt.close(fig)


def plot_signal_dynamics() -> None:
    """Figure 2: channel dynamics and summed amplitude for V=348."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _, cells, channels, summed = make_demo_signal()
    ticks = list(range(len(summed)))

    fig, axes = plt.subplots(len(channels) + 1, 1, figsize=(12, 7.4), sharex=True)
    for index, channel in enumerate(channels):
        cell = cells[index]
        axes[index].step(ticks, channel, where="post", color=BLUE, linewidth=2.0)
        axes[index].axvspan(0, cell.shift_ticks, color="#E5E7EB", alpha=0.65, label=f"silent S={cell.shift_ticks}")
        axes[index].axvline(cell.shift_ticks, color=RED, linestyle="--", linewidth=1.4)
        axes[index].set_ylim(-0.15, 1.25)
        axes[index].set_ylabel(f"C{index}(t)")
        axes[index].set_title(
            f"Channel {index}: digit V{index}={cell.digit_value}, period P={cell.period_ticks}, start delay S={cell.shift_ticks}"
        )
        axes[index].legend(loc="upper right")

    axes[-1].step(ticks, summed, where="post", color=BLACK, linewidth=2.4)
    axes[-1].set_ylabel("A(t)")
    axes[-1].set_xlabel("tick")
    axes[-1].set_title("Summed amplitude signal A(t)=C0(t)+C1(t)")
    fig.suptitle("Figure 2. Signal dynamics for V=348", y=0.995, fontsize=14, weight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(OUTPUT_DIR / "figure_2_signal_dynamics.png", dpi=ARTICLE_DPI)
    plt.close(fig)


def plot_residual_peeling() -> None:
    """Figure 3: residual peeling with first-active markers."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    model, cells, _, summed = make_demo_signal()
    ticks = list(range(len(summed)))
    c0 = _cell_waveform(model, cells[0], len(summed))
    residual_after_c0 = [value - c0_value for value, c0_value in zip(summed, c0)]
    first_c0 = _first_active_tick(model, cells[0], len(summed))
    first_c1 = _first_active_tick(model, cells[1], len(summed))

    rows: list[tuple[str, list[float], str, int | None]] = [
        (
            "received A(t)",
            [float(value) for value in summed],
            f"first C0 active tick={first_c0} -> P0={cells[0].period_ticks}, S0={cells[0].shift_ticks}",
            first_c0,
        ),
        (
            "peeled C0(t)",
            c0,
            "subtract the recovered high-frequency channel",
            None,
        ),
        (
            "residual A(t)-C0(t)=C1(t)",
            residual_after_c0,
            f"first C1 active tick={first_c1} -> P1={cells[1].period_ticks}, S1={cells[1].shift_ticks}",
            first_c1,
        ),
    ]

    fig, axes = plt.subplots(len(rows), 1, figsize=(12, 8), sharex=True)
    for ax, (label, values, annotation, marker_tick) in zip(axes, rows):
        ax.step(ticks, values, where="post", color=BLACK if "A" in label else BLUE, linewidth=2.2)
        if marker_tick is not None:
            ax.axvline(marker_tick, color=RED, linestyle="--", linewidth=1.5)
            ax.scatter([marker_tick], [values[marker_tick]], color=RED, s=80, zorder=4)
            ax.annotate(
                annotation,
                xy=(marker_tick, values[marker_tick]),
                xytext=(marker_tick + 1.4, max(values) + 0.22),
                arrowprops={"arrowstyle": "->", "color": RED, "lw": 1.2},
                color=RED,
                fontsize=9,
            )
        else:
            ax.text(0.99, 0.82, annotation, transform=ax.transAxes, ha="right", color=GREY)
        ax.set_ylabel(label)
        ax.set_ylim(-0.2, max(values) + 0.9)
    axes[-1].set_xlabel("tick")
    fig.suptitle("Figure 3. Residual peeling for V=348", y=0.995, fontsize=14, weight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(OUTPUT_DIR / "figure_3_residual_peeling.png", dpi=ARTICLE_DPI)
    plt.close(fig)


def plot_storage_efficiency() -> None:
    """Figure 4: storage cost of generator parameters vs unfolded states."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = storage_rows()
    write_storage_csv(rows)
    rows = [row for row in rows if row["method"] == "diagonal_width_5"]
    rows.sort(key=lambda row: float(row["payload_bits"]))

    payload_bits = [float(row["payload_bits"]) for row in rows]
    fractal_bits = [float(row["fractal_value_bits"]) for row in rows]
    binary_bits = [float(row["binary_integer_bits"]) for row in rows]
    unfolded_signal_bits = [float(row["unfolded_amplitude_signal_bits"]) for row in rows]
    dense_table_bits = [float(row["unfolded_channel_table_bits"]) for row in rows]

    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    ax.plot(payload_bits, binary_bits, marker="o", linewidth=2.2, label="Payload baseline")
    ax.plot(payload_bits, fractal_bits, marker="s", linewidth=2.2, label="Fractal generator parameters")
    ax.plot(payload_bits, unfolded_signal_bits, marker="^", linewidth=2.2, label="Unfolded A(t)")
    ax.plot(payload_bits, dense_table_bits, marker="D", linewidth=2.2, label="Dense Ck(t) matrix")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log", base=2)
    ax.set_xlabel("Payload size / capacity, bits")
    ax.set_ylabel("Required storage, bits")
    ax.set_title("Figure 4. Storage efficiency: generator vs unfolded states")
    ax.legend()
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "figure_4_storage_efficiency.png", dpi=ARTICLE_DPI)
    plt.close(fig)


def _fractal_latency_for_payload_bits(payload_bits: int, physical_streams: int) -> int:
    model = contiguous_equal_width(width=5)
    segment_bits = math.ceil(payload_bits / physical_streams)
    digit_count = digit_count_for_payload(model, segment_bits)
    cells = model.encode_cells(worst_case_value(model, digit_count), digit_count=digit_count)
    return required_payload_ticks(cells)


def plot_multistream_latency() -> None:
    """Figure 5: matrix-fractal multistream latency vs Manchester serial."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload_sizes = [16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
    stream_counts = [1, 4, 16]

    fig, ax = plt.subplots(figsize=(11, 6.4))
    colors = {1: BLUE, 4: ORANGE, 16: GREEN}
    for streams in stream_counts:
        fractal_latency = [
            _fractal_latency_for_payload_bits(payload_bits, streams)
            for payload_bits in payload_sizes
        ]
        manchester_latency = [
            2 * math.ceil(payload_bits / streams)
            for payload_bits in payload_sizes
        ]
        ax.plot(
            payload_sizes,
            fractal_latency,
            marker="o",
            color=colors[streams],
            linewidth=2.4,
            label=f"Matrix-fractal multistream, N={streams}",
        )
        ax.plot(
            payload_sizes,
            manchester_latency,
            marker="x",
            color=colors[streams],
            linestyle="--",
            linewidth=1.8,
            label=f"Binary serial Manchester, N={streams}",
        )

    ax.set_xscale("log", base=2)
    ax.set_yscale("log", base=10)
    ax.set_xlabel("Payload size, bits")
    ax.set_ylabel("Latency, ticks")
    ax.set_title("Figure 5. Multistream latency: diagonal fractal vs Manchester binary")
    ax.legend(ncol=2, fontsize=8)
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "figure_5_multistream_latency.png", dpi=ARTICLE_DPI)
    plt.close(fig)


def _read_sweep_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def plot_information_density() -> None:
    """Figure 6: information density from matrix alphabet sweep metrics."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = sweep_rows()
    write_sweep_csv(rows)

    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    selected_methods = {"diagonal_width_5", "diagonal_width_8", "custom_diagonal_rule"}
    for method in sorted(selected_methods):
        group = [row for row in rows if row["method"] == method]
        group.sort(key=lambda row: int(row["digit_count"]))
        label = str(group[0]["label"])
        ax.plot(
            [float(row["payload_bits"]) for row in group],
            [float(row["id_bits_per_tick"]) for row in group],
            marker="o",
            linewidth=2.2,
            label=label,
        )

    ax.set_xscale("log", base=2)
    ax.set_xlabel("Payload capacity, bits")
    ax.set_ylabel("Information Density, bits / stream-tick")
    ax.set_title("Figure 6. Information density of the diagonal fractal alphabet")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "figure_6_information_density.png", dpi=ARTICLE_DPI)
    plt.close(fig)


def main() -> None:
    plot_diagonal_alphabet()
    plot_signal_dynamics()
    plot_residual_peeling()
    plot_storage_efficiency()
    plot_multistream_latency()
    plot_information_density()
    print("Wrote final article figures 1..6 to article_assets/outputs")


if __name__ == "__main__":
    main()
