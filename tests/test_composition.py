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


def test_topology_forbidden_edge_is_broken(tmp_path):
    data = {
        "repos": [
            {"repo": "outer", "family": "ctrl"},
            {"repo": "base", "family": "Standard"},
        ],
        "pipeline": [
            {"step": 1, "repo": "outer"},
            {"step": 2, "repo": "base"},
        ],
    }
    catalogue = tmp_path / "catalogue.json"
    catalogue.write_text(json.dumps(data), encoding="utf-8")

    report = validate("grounding-pipeline", catalogue_path=catalogue)

    assert report.stages[1].status == BROKEN
    assert "topology-forbidden" in report.stages[1].reason
    assert report.verdict == BROKEN


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
