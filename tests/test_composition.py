import json
from pathlib import Path

from loomground_composition import BROKEN, PASS, SKIPPED, UNATTESTED, validate
from loomground_composition.__main__ import main


FIXTURE = Path(__file__).parent / "fixtures" / "catalogue.json"


def test_grounding_pipeline_passes_when_every_stage_is_present():
    report = validate("grounding-pipeline", catalogue_path=FIXTURE)

    assert report.verdict == PASS
    assert all(line.status == PASS for line in report.stages)


def test_missing_guard_is_unattested_and_breaks_governed_loop():
    installed = {
        "policy-compiler",
        "a2a-compliance",
        "loomground-escalation",
        "evidence-emitter",
    }
    report = validate("governed-loop", catalogue_path=FIXTURE, installed=installed)
    privacy = next(line for line in report.stages if line.repo == "privacy-shield")

    assert privacy.status == UNATTESTED
    assert privacy.status not in {PASS, SKIPPED}
    assert report.verdict == BROKEN


def test_missing_non_guard_stage_is_skipped_without_breaking():
    report = validate(
        "grounding-pipeline",
        catalogue_path=FIXTURE,
        installed={"ingest"},
    )

    assert report.stages[1].repo == "diagnostic"
    assert report.stages[1].status == SKIPPED
    assert report.verdict == PASS


def test_topology_forbidden_up_dependency_is_broken(tmp_path):
    # Declared-dependency rule: a base-plane repo whose depends_on names a
    # HIGHER-plane (ctrl-family) repo present in the catalogue is topology-forbidden.
    data = {
        "repos": [
            {"repo": "base-consumer", "family": "Standard",
             "depends_on": ["ctrl-orchestrator"]},
            {"repo": "ctrl-orchestrator", "family": "ctrl orchestration"},
        ],
        "pipeline": [
            {"step": 1, "repo": "base-consumer"},
        ],
    }
    catalogue = tmp_path / "catalogue.json"
    catalogue.write_text(json.dumps(data), encoding="utf-8")

    report = validate("grounding-pipeline", catalogue_path=catalogue)
    stage = next(line for line in report.stages if line.repo == "base-consumer")

    assert stage.status == BROKEN
    assert "topology-forbidden" in stage.reason
    assert report.verdict == BROKEN


def test_all_base_depends_on_pass_and_unknown_dep_is_skipped(tmp_path):
    # all-base depends_on points down/sideways -> does NOT trip topology.
    # A depends_on naming a repo ABSENT from the catalogue has an unknown plane
    # and is skipped by the topology layer (never a failure).
    data = {
        "repos": [
            {"repo": "base-a", "family": "Standard", "depends_on": ["base-b"]},
            {"repo": "base-b", "family": "Evidence pipeline"},
            {"repo": "base-c", "family": "Standard", "depends_on": ["ghost-repo"]},
        ],
        "pipeline": [
            {"step": 1, "repo": "base-a"},
            {"step": 2, "repo": "base-b"},
            {"step": 3, "repo": "base-c"},
        ],
    }
    catalogue = tmp_path / "catalogue.json"
    catalogue.write_text(json.dumps(data), encoding="utf-8")

    report = validate("grounding-pipeline", catalogue_path=catalogue)

    assert all(line.status == PASS for line in report.stages)
    assert all("topology-forbidden" not in line.reason for line in report.stages)
    assert report.verdict == PASS


def test_report_states_structural_only_caveat():
    report = validate("grounding-pipeline", catalogue_path=FIXTURE)

    assert "validated != attested/governed" in report.caveat
    assert "STRUCTURAL" in report.caveat


def test_resolvable_validation_and_cli_do_not_raise(capsys):
    report = validate("grounding-pipeline", catalogue_path=FIXTURE)
    exit_code = main(["grounding-pipeline", "--catalogue", str(FIXTURE)])

    assert report.verdict == PASS
    assert exit_code == 0
    assert "verdict: PASS" in capsys.readouterr().out
