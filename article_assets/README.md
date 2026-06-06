# Article Assets

This folder contains reproducible scripts and generated artifacts for the article on diagonal matrix-channel fractal numbers for SNN payloads.

## Layout

```text
article_assets/
  README.md
  scripts/
    generate_article_figures.py
    article_efficiency_metrics.py
    generate_snn_comparative_metrics.py
    generate_storage_metrics.py
    generate_alphabet_sweep_metrics.py
  outputs/
    article_efficiency_metrics.csv
    snn_comparative_metrics.csv
    storage_efficiency_metrics.csv
    matrix_alphabet_sweep_metrics.csv
    figure_1_signal_matrix_348.png
    figure_2_residual_peeling_matrix_348.png
    figure_3_efficiency_required_ticks.png
    figure_4_efficiency_id.png
    figure_3_comparative_latency.png
    figure_4_comparative_id.png
    figure_5_storage_number_vs_signal.png
    figure_6_storage_state_table.png
    figure_7_matrix_alphabet_sweep.png
```

## Reproduce

From the repository root:

```powershell
python article_assets/scripts/generate_article_figures.py
python article_assets/scripts/article_efficiency_metrics.py
python article_assets/scripts/generate_snn_comparative_metrics.py
python article_assets/scripts/generate_storage_metrics.py
python article_assets/scripts/generate_alphabet_sweep_metrics.py
```

## Generated Figures

### `figure_1_signal_matrix_348.png`

Matrix-channel fractal signal for value `348`.

The figure shows:

- channel step signals for mixed-radix digits `V_i`;
- each selected cell's `period_index`, period `P_i`, and start delay `S_i`;
- the summed amplitude stream `A(t)`.

Use this figure near the encoding example.

### `figure_2_residual_peeling_matrix_348.png`

Residual peeling demonstration for value `348`.

The figure shows:

- the original summed signal `A(t)`;
- each extracted channel `Ck(t)`;
- the residual after each subtraction step.

Use this figure near the decoding algorithm.

### `figure_3_efficiency_required_ticks.png`

Required observation window for the diagonal matrix-channel step-mode baseline.

The figure plots required payload ticks against digit count for several user-defined channel alphabets. Latency is estimated as:

```text
required_payload_ticks = max(cell.shift_ticks + 3 * cell.period_ticks for cell in cells) + 1
```

Use this figure in the experimental efficiency section.

### `figure_4_efficiency_id.png`

Information density of the diagonal matrix-channel step-mode baseline.

The figure plots:

```text
ID = useful payload bits / stream-tick
```

The dashed horizontal line marks the binary one-bit-per-stream-tick reference.

Use this figure to explain the current limitation and motivate future high-density decoders.

### `figure_3_comparative_latency.png`

Multistream latency comparison across large payload sizes.

The figure compares:

- `Binary serial, N=1`;
- `Matrix channel width=8, N=1`;
- `Binary serial, N=8`;
- `Matrix channel width=8, N=8`;
- `Binary serial, N=16`;
- `Matrix channel width=8, N=16`.

The matrix-channel payload is split across `N` physical streams. Each stream restarts its channel alphabet from the fastest digit channel. The binary reference receives the same number of physical streams and transmits one bit per stream tick. Matrix-channel latency is computed through the public `MatrixFractalNumber` implementation and uses the conservative observation window:

```text
required_payload_ticks = max(cell.shift_ticks + 3 * cell.period_ticks for cell in cells) + 1
```

Use this figure in the article section that explains fair multichannel resource accounting against an ideal synchronized binary serial reference.

### `figure_4_comparative_id.png`

Multistream information-density comparison.

The figure uses:

```text
ID = payload_bits / (latency_ticks * physical_streams)
```

It shows that multistreaming reduces latency for both methods. In the current step generator, the `width=8` matrix-channel preset is a conservative reproducible baseline, not a final hardware bandwidth bound.

### `experiments/multistream_fractal_vs_binary.ipynb`

Reproducible notebook for the same comparison. All notebooks now live in `experiments/`.

### `figure_5_storage_number_vs_signal.png`

Storage comparison between compact matrix-fractal value parameters and the unfolded summed amplitude signal `A(t)`.

The compact value stores selected mixed-radix matrix cells:

```text
fractal_value_bits = sum(log2(Base_i))
Base_i = sum(P for P in periods_i)
```

The unfolded signal stores every observed amplitude sample:

```text
unfolded_A_bits = latency_ticks * bits(digit_count + 1)
```

Exact fractal value storage is equal to binary integer capacity for scalar storage, but it is much smaller than the unfolded signal needed by the step-mode realization.

### `figure_6_storage_state_table.png`

Storage comparison between compact matrix-fractal generator parameters and a dense channel-state table `C_k(t)`.

The dense table explicitly stores every binary channel state at every tick:

```text
unfolded_C_bits = latency_ticks * digit_count
```

This is the strongest storage result: the matrix-fractal generator stores the rule and selected cells instead of materializing the whole state table.

### `figure_7_matrix_alphabet_sweep.png`

Alphabet sweep for several user-defined diagonal channel matrices:

- article `348` alphabet `{2..6}`, `{7..10}`;
- contiguous bands with width `5`;
- contiguous bands with width `8`;
- a custom diagonal user rule.

Use this figure to explain that alphabet design is a physical receiver configuration problem: larger period bands increase diagonal channel capacity, while maximum period and start delay control observation cost.

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

### `snn_comparative_metrics.csv`

CSV table used to generate the comparative SNN-channel figures.

Columns include:

- `method`
- `label`
- `payload_bits`
- `physical_streams`
- `segment_bits`
- `segment_capacity_bits`
- `digit_count_per_stream`
- `latency_ticks`
- `stream_ticks`
- `id_bits_per_stream_tick`

### `storage_efficiency_metrics.csv`

CSV table used to generate the storage-efficiency figures.

Columns include:

- `method`
- `period_levels`
- `shift_levels`
- `digit_count`
- `payload_bits`
- `latency_ticks`
- `fractal_value_bits`
- `binary_integer_bits`
- `unfolded_amplitude_signal_bits`
- `unfolded_channel_table_bits`
- `number_storage_gain_vs_binary`
- `signal_storage_gain_vs_unfolded`
- `state_table_storage_gain_vs_unfolded`

### `matrix_alphabet_sweep_metrics.csv`

CSV table used to generate `figure_7_matrix_alphabet_sweep.png`.

Columns include:

- `method`
- `label`
- `digit_count`
- `max_period_ticks`
- `payload_bits`
- `latency_ticks`
- `id_bits_per_tick`

## Interpretation

The diagonal matrix-channel implementation uses user-defined contiguous period bands and half-period step signals:

```text
periods_i = user_defined_periods(i)
Base_i = sum(P for P in periods_i)
C_i(t) = 0, if t < S_i
C_i(t) = 1[((t - S_i) mod P_i) >= floor(P_i / 2)], if t >= S_i
```

Therefore, these figures should be interpreted as a reproducible conservative baseline:

- proves representation and decoding correctness;
- exposes current latency/resource costs;
- demonstrates fair multistream scaling where each fractal stream restarts its hierarchy;
- shows how user-defined channel matrices change storage and transmission efficiency.

The storage figures make a separate claim from the transmission figures. A compact matrix-fractal value should not be claimed to beat an entropy-minimal binary integer for exact scalar storage. Its strong storage advantage appears when the alternative is an unfolded SNN object: the full amplitude trace `A(t)` or the dense state table `C_k(t)`.
