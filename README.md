# loomground-composition

Pure, plane-neutral validation of declared Loomground compositions.

The package reads catalogue data and reports whether each named stage exists and
whether that repo's declared dependencies (`depends_on`) point down toward base.
The grounding-pipeline fan-out is walked linearly in v0. It does not run planes,
govern an action, or attest an outcome. A future runner belongs in `ctrl`; it may
consume these reports as data.

## Compositions

- `grounding-pipeline` — the ordered pipeline declared by Loomground Core.
- `governed-loop` — policy compiler, A2A control, privacy shield, escalation,
  and evidence emission.

## Validate

```sh
python -m loomground_composition grounding-pipeline
python -m loomground_composition governed-loop
```

`validated != governed`: validation means structural well-formedness only. It is
not execution, attestation, or a governance verdict.

## Joining

Loomground Core's `CATALOGUE.json` is the source of composition data. A repository
declares its `pipeline_position` and `depends_on` there; this package reads that
catalogue and introduces no second registration surface.

## License

Apache-2.0.
