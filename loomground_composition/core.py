from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

# Pure, plane-neutral, DESCRIPTIVE validator. Reads JSON/text only; runs no plane,
# opens no socket, spawns no process, imports no loomground_* plane package.

DEFAULT_CATALOGUE = Path(
    "/Users/rafelixkrone/Documents/Claude/Projects/loomground-repos/Loomground Core/CATALOGUE.json"
)

# Guard tier is hardcoded exactly: its absence or a broken edge is never a bare PASS.
GUARD_TIER = frozenset({
    "privacy-shield",
    "a2a-compliance",
    "evidence-emitter",
    "loomground-escalation",
    "oversight-ladder",
    "loomground-lock",
    "loomground-lane",
    "loomground-drift",
    "loomground-erasure",
})

# The fixed governed-loop stages, in order. grounding-pipeline is read from the
# CATALOGUE `pipeline` array (step order) instead. No other compositions ship.
GOVERNED_LOOP = (
    "policy-compiler",
    "a2a-compliance",
    "privacy-shield",
    "loomground-escalation",
    "evidence-emitter",
)

# Statuses.
PASS = "PASS"
SKIPPED = "SKIPPED"
BROKEN = "BROKEN"
UNATTESTED = "UNATTESTED"          # guard-tier absent / guard edge broken
_FAILING = frozenset({BROKEN, UNATTESTED})

CAVEAT = (
    "validated != attested/governed: 'validated' means STRUCTURAL well-formedness "
    "only. A resolving composition is NOT attested, NOT governed, and NOT executed "
    "by this tool -- it merely reports that the stages exist and their edges point "
    "down toward base."
)

# Plane depth: base=0 (loomground knowledge), 1=RVND governance, 2=ctrl orchestration.
# topology.md rule: dependencies point down toward base; an edge up toward a
# consumer, or a forbidden sideways edge, fails. CATALOGUE repos[].family is the
# documented plane proxy (see repo-standards/topology.md).
_LOOMGROUND, _RVND, _CTRL = 0, 1, 2


def _plane(family: Optional[str]) -> int:
    f = (family or "").strip().lower()
    if f == "rvnd" or f.startswith("rvnd/") or f.startswith("rvnd "):
        return _RVND
    if "ctrl" in f:
        return _CTRL
    # Standard, language planes, contracts, evidence pipeline, applied reasoning,
    # diagnostic operators, assurance artifacts, runtime controls, interfaces:
    # all Loomground base plane. Unknown families fail closed to base too.
    return _LOOMGROUND


@dataclass
class StageLine:
    stage: str
    repo: str
    status: str
    reason: str


@dataclass
class Report:
    composition: str
    stages: list = field(default_factory=list)
    verdict: str = PASS
    caveat: str = CAVEAT

    @property
    def ok(self) -> bool:
        return self.verdict == PASS

    def render(self) -> str:
        w = max((len(s.repo) for s in self.stages), default=4)
        lines = [f"composition: {self.composition}", ""]
        for i, s in enumerate(self.stages, 1):
            lines.append(f"  {i:>2}. {s.status:<10} {s.repo:<{w}}  ({s.stage})")
            lines.append(f"      {s.reason}")
        lines.append("")
        lines.append(f"verdict: {self.verdict}")
        lines.append(f"caveat:  {self.caveat}")
        return "\n".join(lines)


def _load_catalogue(catalogue_path):
    path = Path(catalogue_path) if catalogue_path else DEFAULT_CATALOGUE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}, [], set()
    repos = data.get("repos", []) or []
    family = {r.get("repo"): r.get("family") for r in repos if r.get("repo")}
    names = {r.get("repo") for r in repos if r.get("repo")}
    return data, family, names


def _grounding_stages(catalogue: dict):
    # step order; the pipeline list is already ordered but sort defensively (stable).
    pipeline = catalogue.get("pipeline", []) or []
    ordered = sorted(pipeline, key=lambda e: e.get("step", 0))
    out = []
    for e in ordered:
        repo = e.get("repo")
        if repo:
            out.append((e.get("stage") or repo, repo))
    return out


def _stages_for(name: str, catalogue: dict):
    if name == "grounding-pipeline":
        return _grounding_stages(catalogue)
    if name == "governed-loop":
        return [(r, r) for r in GOVERNED_LOOP]
    return None


def validate(composition_name: str, *, catalogue_path=None, installed: Optional[Iterable[str]] = None) -> Report:
    catalogue, family, cat_names = _load_catalogue(catalogue_path)
    present = set(installed) if installed is not None else set(cat_names)

    stages = _stages_for(composition_name, catalogue)
    if stages is None:
        return Report(
            composition=composition_name,
            stages=[StageLine("<unknown>", "-", BROKEN,
                              f"unknown composition '{composition_name}'; ship only "
                              "grounding-pipeline and governed-loop")],
            verdict=BROKEN,
        )
    if not stages:
        return Report(
            composition=composition_name,
            stages=[StageLine("<empty>", "-", BROKEN,
                              "no stages resolved (catalogue unreadable or empty)")],
            verdict=BROKEN,
        )

    lines: list = []
    prev_repo = None
    for stage, repo in stages:
        is_guard = repo in GUARD_TIER
        # Layer (b) TOPOLOGY: static, from families; independent of `installed`.
        if prev_repo is None:
            edge_ok, edge_reason = True, "entry stage; no inbound edge"
        else:
            pp, tp = _plane(family.get(prev_repo)), _plane(family.get(repo))
            edge_ok = pp <= tp  # permitted when prev is same-or-more-base than this
            edge_reason = (
                f"edge {prev_repo} -> {repo} down-toward-base (plane {pp} -> {tp})"
                if edge_ok else
                f"edge {prev_repo} -> {repo} points UP toward a consumer / forbidden "
                f"sideways (plane {pp} -> {tp})"
            )
        # Layer (a) EXISTENCE: from `installed`.
        exists = repo in present

        if not edge_ok:
            status = UNATTESTED if is_guard else BROKEN
            reason = f"topology-forbidden: {edge_reason}"
        elif exists:
            status, reason = PASS, f"present; {edge_reason}"
        elif is_guard:
            status = UNATTESTED
            reason = f"GUARD-TIER stage ABSENT -> unattested (never a bare PASS); {edge_reason}"
        else:
            status = SKIPPED
            reason = f"non-guard stage absent -> skipped; {edge_reason}"

        lines.append(StageLine(stage, repo, status, reason))
        prev_repo = repo

    verdict = BROKEN if any(l.status in _FAILING for l in lines) else PASS
    return Report(composition=composition_name, stages=lines, verdict=verdict)
