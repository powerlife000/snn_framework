# Article Assets

This folder contains reproducible scripts and generated artifacts for the article on matrix-fractal numbers for SNN payloads.

## Layout

```text
article_assets/
  README.md
  scripts/
    generate_article_figures.py
    article_efficiency_metrics.py
  outputs/
    article_efficiency_metrics.csv
    figure_1_signal_2748.png
    figure_2_residual_peeling_2748.png
    figure_3_efficiency_required_ticks.png
    figure_4_efficiency_id.png
```

## Reproduce

From the repository root:

```powershell
python article_assets/scripts/generate_article_figures.py
python article_assets/scripts/article_efficiency_metrics.py
```

## Generated Figures

### `figure_1_signal_2748.png`

Matrix-fractal signal for value `2748` in the `4 x 4` period-shift alphabet.

The figure shows:

- `C0(t)`, `C1(t)`, `C2(t)` channel step signals;
- each channel's decoded digit, period, and shift;
- the summed amplitude stream `A(t)`.

Use this figure near the encoding example.

### `figure_2_residual_peeling_2748.png`

Residual peeling demonstration for value `2748`.

The figure shows:

- the original summed signal `A(t)`;
- each extracted channel `Ck(t)`;
- the residual after each subtraction step.

Use this figure near the decoding algorithm.

### `figure_3_efficiency_required_ticks.png`

Required observation window for the current conservative step-mode baseline.

The figure plots required payload ticks against matrix-radix digit count for several period-shift alphabets. Latency is estimated as:

```text
required_payload_ticks = max(cell.shift_ticks + cell.period_ticks for cell in cells) + 1
```

Use this figure in the experimental efficiency section.

### `figure_4_efficiency_id.png`

Information density of the current conservative step-mode baseline.

The figure plots:

```text
ID = useful payload bits / stream-tick
```

The dashed horizontal line marks the binary one-bit-per-stream-tick baseline. The current implementation is intended as a correctness baseline, not as the final bandwidth-optimized channel.

Use this figure to explain the current limitation and motivate future high-density decoders.

## Generated Data

### `article_efficiency_metrics.csv`

CSV table used to generate figures 3 and 4.

Columns include:

- `method`
- `family`
- `period_levels`
- `shift_levels`
- `base`
- `digit_count`
- `payload_bits`
- `latency_ticks`
- `physical_streams`
- `stream_ticks`
- `max_amplitude`
- `amplitude_levels`
- `amplitude_resolution_bits`
- `id_bits_per_stream_tick`
- `adjusted_id`

## Interpretation

The current matrix-fractal step-mode implementation uses non-overlapping period bands and half-period step signals. This makes residual decoding deterministic and easy to verify, but it increases the required observation window.

Therefore, these figures should be interpreted as a reproducible conservative baseline:

- proves representation and decoding correctness;
- exposes current latency/resource costs;
- motivates future high-density modes such as correlation decoding, sparse spike-mode, analog phase receivers, and learned SNN/population decoders.
