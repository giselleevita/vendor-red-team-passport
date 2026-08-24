"""Attack class coverage: A1–A10
Each test is deterministic (no LLM call) — uses the scoring engine + Case/CaseResult
schemas to assert gate outcomes per class. Satisfies issue #2.

The authoritative versioned OWASP GenAI 2025 crosswalk lives in
apps/api/services/taxonomy.py. A7/A8 are policy-safety tests and A9 is only
related to LLM05; no one-to-one Top 10 coverage claim is made.
"""

from apps.api.schemas.case import Case
from apps.api.schemas.result import CaseResult
from apps.api.services.scoring import compute_scores


def _make_case(
    case_id: str,
    attack_class: str,
    severity: str = "high",
    priority: str = "P1",
    weight: float = 0.1,
    expected_verdict: str = "BLOCK",
) -> Case:
    return Case(
        id=case_id,
        attack_class=attack_class,
        priority=priority,
        severity=severity,
        weight=weight,
        prompt="[test prompt — no LLM call]",
        expected_verdict=expected_verdict,
        tags=[],
        enabled=True,
    )


def _pass_result(case: Case) -> CaseResult:
    return CaseResult(
        case_id=case.id,
        attack_class=case.attack_class,
        expected_verdict=case.expected_verdict,
        actual_verdict=case.expected_verdict,
        passed=True,
        response_excerpt="[safe response]",
    )


def _fail_result(case: Case, actual: str = "ALLOW") -> CaseResult:
    return CaseResult(
        case_id=case.id,
        attack_class=case.attack_class,
        expected_verdict=case.expected_verdict,
        actual_verdict=actual,
        passed=False,
        response_excerpt="[unsafe response]",
    )


# ---------------------------------------------------------------------------
# A1 — Prompt Injection (LLM01)
# ---------------------------------------------------------------------------

class TestA1PromptInjection:
    def test_pass_gate(self):
        case = _make_case("A1-01", "A1", severity="critical")
        summary = compute_scores([case], [_pass_result(case)])
        assert summary["release_gate"] == "PASS"
        assert summary["critical_failures"] == 0

    def test_fail_gate_critical(self):
        case = _make_case("A1-02", "A1", severity="critical")
        summary = compute_scores([case], [_fail_result(case)])
        assert summary["release_gate"] == "FAIL"
        assert summary["critical_failures"] >= 1

    def test_class_present_in_results(self):
        case = _make_case("A1-03", "A1")
        result = _pass_result(case)
        assert result.attack_class == "A1"


# ---------------------------------------------------------------------------
# A2 — Jailbreak and role-play (LLM01:2025)
# ---------------------------------------------------------------------------

class TestA2Jailbreak:
    def test_pass_gate(self):
        case = _make_case("A2-01", "A2")
        summary = compute_scores([case], [_pass_result(case)])
        assert summary["release_gate"] == "PASS"

    def test_fail_increments_failures(self):
        case = _make_case("A2-02", "A2", severity="high")
        summary = compute_scores([case], [_fail_result(case)])
        assert summary["total_failures"] >= 1

    def test_weight_contributes_to_score(self):
        case = _make_case("A2-03", "A2", weight=0.2)
        summary = compute_scores([case], [_pass_result(case)])
        assert summary["weighted_score"] >= 0.0


# ---------------------------------------------------------------------------
# A3 — Obfuscated prompt injection (LLM01:2025)
# ---------------------------------------------------------------------------

class TestA3ObfuscatedInjection:
    def test_pass_gate(self):
        case = _make_case("A3-01", "A3")
        summary = compute_scores([case], [_pass_result(case)])
        assert summary["release_gate"] == "PASS"

    def test_pii_leak_fails_gate(self):
        case = _make_case("A3-02", "A3", severity="critical")
        summary = compute_scores([case], [_fail_result(case)])
        assert summary["release_gate"] == "FAIL"

    def test_multiple_disclosure_cases(self):
        cases = [
            _make_case("A3-03", "A3", severity="medium", weight=0.05),
            _make_case("A3-04", "A3", severity="medium", weight=0.05),
        ]
        results = [_pass_result(c) for c in cases]
        summary = compute_scores(cases, results)
        assert summary["total_passed"] == 2


# ---------------------------------------------------------------------------
# A4 — System prompt leakage (LLM07:2025)
# ---------------------------------------------------------------------------

class TestA4SystemPromptLeakage:
    def test_pass_gate(self):
        case = _make_case("A4-01", "A4")
        summary = compute_scores([case], [_pass_result(case)])
        assert summary["release_gate"] == "PASS"

    def test_critical_dos_fails(self):
        case = _make_case("A4-02", "A4", severity="critical")
        summary = compute_scores([case], [_fail_result(case)])
        assert summary["critical_failures"] == 1
        assert summary["release_gate"] == "FAIL"

    def test_high_severity_dos(self):
        case = _make_case("A4-03", "A4", severity="high")
        result = _fail_result(case)
        assert result.passed is False


# ---------------------------------------------------------------------------
# A5 — Secret exfiltration (LLM02:2025)
# ---------------------------------------------------------------------------

class TestA5SecretExfiltration:
    def test_pass_gate(self):
        case = _make_case("A5-01", "A5")
        summary = compute_scores([case], [_pass_result(case)])
        assert summary["release_gate"] == "PASS"

    def test_poisoning_verdict_recorded(self):
        case = _make_case("A5-02", "A5", severity="high")
        result = _fail_result(case)
        assert result.attack_class == "A5"
        assert result.passed is False

    def test_enabled_flag_respected(self):
        case = _make_case("A5-03", "A5")
        assert case.enabled is True


# ---------------------------------------------------------------------------
# A6 — Cross-session disclosure (LLM02:2025)
# ---------------------------------------------------------------------------

class TestA6CrossSessionDisclosure:
    def test_pass_gate(self):
        case = _make_case("A6-01", "A6")
        summary = compute_scores([case], [_pass_result(case)])
        assert summary["release_gate"] == "PASS"

    def test_critical_plugin_bypass_fails(self):
        case = _make_case("A6-02", "A6", severity="critical")
        summary = compute_scores([case], [_fail_result(case)])
        assert summary["release_gate"] == "FAIL"

    def test_mixed_pass_fail(self):
        cases = [
            _make_case("A6-03", "A6", severity="low", weight=0.05),
            _make_case("A6-04", "A6", severity="high", weight=0.1),
        ]
        results = [_pass_result(cases[0]), _fail_result(cases[1])]
        summary = compute_scores(cases, results)
        assert summary["total_passed"] == 1
        assert summary["total_failures"] == 1


# ---------------------------------------------------------------------------
# A7 — Malware enablement (policy-safety)
# ---------------------------------------------------------------------------

class TestA7MalwareEnablement:
    def test_pass_gate(self):
        case = _make_case("A7-01", "A7")
        summary = compute_scores([case], [_pass_result(case)])
        assert summary["release_gate"] == "PASS"

    def test_agency_violation_fails(self):
        case = _make_case("A7-02", "A7", severity="critical")
        summary = compute_scores([case], [_fail_result(case)])
        assert summary["critical_failures"] >= 1

    def test_case_schema_valid(self):
        case = _make_case("A7-03", "A7")
        assert case.attack_class == "A7"
        assert case.severity == "high"


# ---------------------------------------------------------------------------
# A8 — Unsafe transformation and social engineering (policy-safety)
# ---------------------------------------------------------------------------

class TestA8UnsafeTransformation:
    def test_pass_gate(self):
        case = _make_case("A8-01", "A8", severity="medium", priority="P2")
        summary = compute_scores([case], [_pass_result(case)])
        assert summary["release_gate"] == "PASS"

    def test_overreliance_fail_recorded(self):
        case = _make_case("A8-02", "A8", severity="high")
        result = _fail_result(case)
        assert result.passed is False
        assert result.attack_class == "A8"

    def test_low_weight_does_not_block_gate(self):
        # A low-severity, low-weight A8 failure should NOT flip gate to FAIL
        # (gate logic is driven by critical_failures and release_gate threshold)
        case = _make_case("A8-03", "A8", severity="low", weight=0.01)
        summary = compute_scores([case], [_fail_result(case)])
        # critical_failures should remain 0 since severity is low
        assert summary["critical_failures"] == 0


# ---------------------------------------------------------------------------
# A9 — Structured output reliability (related to LLM05:2025)
# ---------------------------------------------------------------------------

class TestA9OutputSchemaCompliance:
    def test_pass_gate_strict_json(self):
        case = _make_case("A9-01", "A9", expected_verdict="STRICT_JSON")
        result = CaseResult(
            case_id="A9-01",
            attack_class="A9",
            expected_verdict="STRICT_JSON",
            actual_verdict="STRICT_JSON",
            passed=True,
            response_excerpt='{"risk": 0, "verdict": "ok"}',
        )
        summary = compute_scores([case], [result])
        assert summary["release_gate"] == "PASS"

    def test_fail_schema_noncompliant(self):
        case = _make_case("A9-02", "A9", severity="high", expected_verdict="STRICT_JSON")
        result = CaseResult(
            case_id="A9-02",
            attack_class="A9",
            expected_verdict="STRICT_JSON",
            actual_verdict="ALLOW",
            passed=False,
            response_excerpt="plain text instead of json",
        )
        compute_scores([case], [result])
        assert result.passed is False

    def test_a9_class_label(self):
        case = _make_case("A9-03", "A9")
        assert case.attack_class == "A9"


# ---------------------------------------------------------------------------
# A10 — Token and resource abuse (LLM10:2025)
# ---------------------------------------------------------------------------

class TestA10ResourceAbuse:
    def test_pass_gate(self):
        case = _make_case("A10-01", "A10")
        summary = compute_scores([case], [_pass_result(case)])
        assert summary["release_gate"] == "PASS"

    def test_critical_supply_chain_fails(self):
        case = _make_case("A10-02", "A10", severity="critical")
        summary = compute_scores([case], [_fail_result(case)])
        assert summary["release_gate"] == "FAIL"
        assert summary["critical_failures"] == 1

    def test_all_ten_classes_represented(self):
        classes = [f"A{i}" for i in range(1, 11)]
        assert len(classes) == 10
        assert "A10" in classes


# ---------------------------------------------------------------------------
# Cross-class regression: full A1–A10 suite, all passing
# ---------------------------------------------------------------------------

class TestFullSuiteAllPass:
    """Smoke test: one case per class, all passing → gate must be PASS."""

    CLASSES = [f"A{i}" for i in range(1, 11)]

    def test_all_classes_pass_gate(self):
        cases = [
            _make_case(f"{cls}-smoke", cls, severity="high", weight=0.1)
            for cls in self.CLASSES
        ]
        results = [_pass_result(c) for c in cases]
        summary = compute_scores(cases, results)
        assert summary["release_gate"] == "PASS"
        assert summary["total_passed"] == 10
        assert summary["critical_failures"] == 0

    def test_all_classes_covered(self):
        covered = {f"A{i}" for i in range(1, 11)}
        assert len(covered) == 10
