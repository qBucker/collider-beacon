# Conditioning layer — Stage-2 Toeplitz extraction

This directory implements the extraction stage of the Collider Beacon protocol:
a Toeplitz matrix over GF(2), applied block by block, with a public seed chained
from the previous block output.

## Protocol

For a block of `n` bits carrying `n_events = n / b` events, with certified
per-event min-entropy `h_inf`:

- output length `m = floor(n_events * h_inf) - 128` bits (the 128-bit
  leftover-hash margin);
- Toeplitz seed length `m + n - 1` bits;
- seed rule:
  - block 0: `s_0 = SHAKE256("collider-beacon/s0/v1" || params)`, where
    `params` includes the run, `b`, `h_inf`, block size, seed salt, timestamp,
    and the sorted file list;
  - block `r > 0`: `s_r = SHAKE256("collider-beacon/chain/v1" || pack(output_{r-1}))`;
- the seed is expanded to exactly `m + n - 1` bits and defines
  `T[i,j] = seed[i - j + n - 1]`; the block is multiplied by `T` over GF(2).

The Toeplitz product is computed by exact integer convolution via FFT. The
convolution coefficients are bounded by the block size (well below `2^53`), so
float64 FFT is exact after rounding. A direct-matrix self-test is included.

## Input formats

- `b = 8`: one byte per symbol, as written by the extractor (`np.unpackbits`
  gives the eight bits of each symbol);
- `b = 12`: 12-bit symbols packed MSB-first, as written by the extractor
  (`np.unpackbits`, then truncate to a multiple of 12 bits).

The canonical 67 files are selected by `f[0-9][0-9].bits.bin`; `f01-local` is
excluded.

## Usage

```bash
# canonical b=12 configuration, 25,000 events per block, seed salt 0
python3 conditioning/toeplitz_extract.py --run-dir runG12 --b 12 \
    --hinf 11.3098 --block-events 25000 --seed-salt 0 \
    --out conditioning/out/b12-toeplitz-25k-s0.bits.bin \
    --manifest conditioning/out/b12-toeplitz-25k-s0.manifest.json

# b=8 control
python3 conditioning/toeplitz_extract.py --run-dir runG --b 8 \
    --hinf 7.8413 --block-events 100000 --seed-salt 0 \
    --out conditioning/out/b8-toeplitz-s0.bits.bin \
    --manifest conditioning/out/b8-toeplitz-s0.manifest.json
```

The output bit files are ~7.4 MB at b=12 and ~5.1 MB at b=8 (packed) and are
not committed; each manifest records their SHA256, block layout, and parameters.
The STS reports are committed under `sts-2026-10-23/`.

## Result

`RESULT-2026-10-23.md` records the measured outcome: the raw b=12 stream has six
NIST STS flags; the conditioned 25,000-event configuration has zero flags across
three independent seed salts and 58 one-megabit sequences. The b=8 control also
has zero flags. A block-size/seed scan is included.

## Security note

The Toeplitz family is 2-universal with a uniform seed; the leftover-hash lemma
gives `eps_LHL <= 2^-64` at the chosen 128-bit margin. The seed here is
computational (SHAKE256), not an information-theoretic uniform string; the
chained-seed hybrid argument of the companion paper bounds the seed defect by
`delta_seed = 2^-64`. This is an engineering demonstration of Stage 2, not a
production beacon.
