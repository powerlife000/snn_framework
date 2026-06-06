# Experiments

All notebooks for the diagonal matrix-channel fractal number prototype live here.

- `fractal_alphabet_demo.ipynb` - bilingual visual explanation of the fractal alphabet, diagonal period-shift cells, dynamic digit radices, and selected `(P, S)` parameters.
- `multistream_fractal_vs_binary.ipynb` - interactive smoke comparison against equal-stream binary serial.
- `fractal_packet_demo.ipynb` - packet roundtrip with explicit `DIGIT_COUNT` and mixed-radix checksum.
- `fractal_number_compression_demo.ipynb` - encoding/decoding walkthrough: number -> digits -> cells -> state table -> `A(t)` -> residual peeling -> decoded number.
- `fractal_number_efficiency_experiment.ipynb` - efficiency analysis for number storage via generator parameters and amplitude magnitude, plus unfolded state-table storage.
- `fractal_number_robustness_experiment.ipynb` - separated-channel nearest-cell matching with dropped samples.

For reproducible article CSV/PNG outputs, prefer the scripts in `article_assets/scripts/`.
