from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

# Pure, plane-neutral, DESCRIPTIVE validator. Reads JSON/text only; runs no plane,
# opens no network connection, spawns no process, imports no plane package.

_CATALOGUE_NOT_FOUND = "catalogue not found (set LOOMGROUND_CATALOGUE or pass --catalogue)"

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


def _resolve_catalogue_path(catalogue_path) -> Optional[Path]:
    # Explicit only, no filesystem guessing: the passed path, else LOOMGROUND_CATALOGUE.
    if catalogue_path:
        return Path(catalogue_path)
    env = os.environ.get("LOOMGROUND_CATALOGUE")
    if env:
        return Path(env)
    return None


def _load_catalogue(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}, {}, set(), {}
    repos = data.get("repos", []) or []
    family = {r.get("repo"): r.get("family") for r in repos if r.get("repo")}
    names = {r.get("repo") for r in repos if r.get("repo")}
    depends = {
        r.get("repo"): list(r.get("depends_on") or [])
        for r in repos if r.get("repo")
    }
    return data, family, names, depends


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
    resolved = _resolve_catalogue_path(catalogue_path)
    if resolved is None:
        return Report(
            composition=composition_name,
            stages=[StageLine("<catalogue>", "-", BROKEN, _CATALOGUE_NOT_FOUND)],
            verdict=BROKEN,
        )
    catalogue, family, cat_names, depends = _load_catalogue(resolved)
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
    for stage, repo in stages:
        is_guard = repo in GUARD_TIER
        repo_plane = _plane(family.get(repo))

        # Layer (b) TOPOLOGY: each DECLARED dependency (repos[].depends_on) is an
        # edge repo -> dep and MUST point DOWN toward base: permitted iff
        # plane(dep) <= plane(repo). A dep at a HIGHER plane is topology-forbidden.
        # A dep whose repo is absent from the catalogue has an unknown plane and is
        # SKIPPED by this layer entirely -- presence is the existence layer's job.
        topo_ok = True
        topo_reason = "declared deps point down toward base"
        for dep in depends.get(repo, []):
            if dep not in cat_names:
                continue
            dep_plane = _plane(family.get(dep))
            if dep_plane > repo_plane:
                topo_ok = False
                topo_reason = (
                    f"topology-forbidden: {repo} depends UP on {dep} "
                    f"(plane {repo_plane} -> {dep_plane})"
                )
                break

        # Layer (a) EXISTENCE: from `installed`.
        exists = repo in present

        if not topo_ok:
            status = UNATTESTED if is_guard else BROKEN
            reason = topo_reason
        elif exists:
            status, reason = PASS, f"present; {topo_reason}"
        elif is_guard:
            status = UNATTESTED
            reason = f"GUARD-TIER stage ABSENT -> unattested (never a bare PASS); {topo_reason}"
        else:
            status = SKIPPED
            reason = f"non-guard stage absent -> skipped; {topo_reason}"

        lines.append(StageLine(stage, repo, status, reason))

    verdict = BROKEN if any(l.status in _FAILING for l in lines) else PASS
    return Report(composition=composition_name, stages=lines, verdict=verdict)
