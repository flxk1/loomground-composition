<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# loomground-composition

> **⚠ DEPRECATED (2026-09-16).** Superseded by the loomground `a2a-compliance`
> control plane — the 8-role compliance team and the `a2a_plan` / `a2a_ground` /
> admission / reconcile MCP lifecycle — together with the published signed runtime
> and the 41+8 ecosystem certification, which cover composing and governing the
> family more completely. This repository is archived and unmaintained; do not
> depend on it.

**Does this declared composition still resolve, and where does it break?**

Structural validator for declared Loomground compositions: reports whether a named composition resolves stage by stage.

## Problem

The catalogue declares family compositions — a grounding pipeline, a governed loop — as data, and that data drifts as repos move. This reads the catalogue and reports, stage by stage, whether a named composition resolves: every stage present, every declared dependency pointing down toward base. A broken composition becomes visible before a host runs it.

## Install

```
pip install "git+https://github.com/flxk1/loomground-composition"
```

Import name `loomground_composition`; zero required dependencies. Point it at a catalogue with `--catalogue` or the `LOOMGROUND_CATALOGUE` environment variable.

## Usage

```python
from loomground_composition import validate

report = validate("governed-loop", catalogue_path="CATALOGUE.json")
print(report.verdict)     # PASS / BROKEN
print(report.render())
```

```
LOOMGROUND_CATALOGUE=/path/to/CATALOGUE.json python -m loomground_composition grounding-pipeline
```

## Example

```
in : validate("governed-loop") against a catalogue with privacy-shield absent
out: BROKEN
     privacy-shield  UNATTESTED  guard-tier stage absent -> unattested
     verdict: BROKEN
```

## Interface

- `validate(composition_name, *, catalogue_path=None, installed=None) -> Report` — `.verdict` `.ok` `.stages` `.caveat` `.render()`.
- Two compositions ship: `grounding-pipeline` (from the catalogue `pipeline`) and `governed-loop`.
- Each stage resolves on two layers: the repo is present, and its declared `depends_on` point down toward base. A guard-tier stage absent is reported `UNATTESTED` rather than a pass.
- CLI: `python -m loomground_composition <composition>` prints the report and exits non-zero on `BROKEN`.

## Family

Composition. A descriptive consumer of catalogue data: it reads the catalogue and reports resolution. It only reads and reports — a down-edge by construction that stands alone; a host consumes its report when running a composition, and the run itself lives in a separate orchestration layer above it. Catalogue: [CATALOGUE.json](https://github.com/flxk1/loomground/blob/main/CATALOGUE.json).

## Status

0.1.0 · 7 tests · Python >=3.10 · zero required dependencies · validated is structural well-formedness only — separate from attestation and governance.

## License

Apache-2.0 — [LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt).
