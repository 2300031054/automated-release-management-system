"""
Rule-based release decision engine.
Evaluates collected release indicators and returns a decision:
RELEASE / BLOCK / MANUAL_APPROVAL.

Every condition includes:
  - status        : PASS / FAIL
  - summary       : one-line result
  - explanation   : root cause — how/why this happened
  - recommendation: what to do next
No condition is ever returned without an explanation.
"""

from typing import List, Dict


def _condition(title, passed, summary, explanation, recommendation):
    return {
        "title": title,
        "status": "PASS" if passed else "FAIL",
        "summary": summary,
        "explanation": explanation,
        "recommendation": recommendation,
    }


def evaluate_release(
    build_passed: bool,
    test_pass_rate: float,
    code_quality_score: float,
    critical_vulns: int,
    high_vulns: int,
    previous_release_success_rate: float,
) -> Dict:
    conditions: List[Dict] = []
    decision = "RELEASE"

    # ---------- Rule 1: Build status ----------
    if build_passed:
        conditions.append(_condition(
            "Build status", True,
            "Build completed successfully.",
            "Jenkins ran the build stage (compile/package) against the latest "
            "commit and it completed without errors, so the pipeline was able "
            "to proceed to the test stage.",
            "No action needed."
        ))
    else:
        conditions.append(_condition(
            "Build status", False,
            "Build failed.",
            "The build stage in Jenkins did not complete — this is typically "
            "caused by a compilation error, a missing/incompatible dependency, "
            "or a broken import introduced in the latest commit. Because the "
            "build never finished, none of the later stages (tests, code "
            "quality, security scan) could run on this candidate.",
            "Open the Jenkins console log for the failed build and fix the "
            "reported compile/dependency error, then re-trigger the pipeline."
        ))
        decision = "BLOCK"

    # ---------- Rule 2: Critical vulnerabilities ----------
    crit_ok = critical_vulns == 0
    if crit_ok:
        conditions.append(_condition(
            "Critical vulnerabilities", True,
            "No critical vulnerabilities detected.",
            "The security scan stage completed and found zero critical-severity "
            "findings in the dependency/code scan for this build.",
            "No action needed."
        ))
    else:
        conditions.append(_condition(
            "Critical vulnerabilities", False,
            f"{critical_vulns} critical vulnerability(ies) detected.",
            "The security scan flagged one or more critical-severity issues — "
            "usually a known CVE in a dependency, or a critical code-level "
            "flaw such as hardcoded credentials or an injection risk. These "
            "are severe enough that shipping them could expose the system to "
            "exploitation immediately after release.",
            "Review the security scan report, upgrade/patch the affected "
            "dependency or fix the flagged code, and re-run the scan before "
            "this candidate can be reconsidered."
        ))
        decision = "BLOCK"

    # ---------- Rule 3: Test pass rate ----------
    test_block = test_pass_rate < 80
    test_manual = 80 <= test_pass_rate < 90
    if test_pass_rate >= 90:
        conditions.append(_condition(
            "Test pass rate", True,
            f"{test_pass_rate}% of automated tests passed.",
            "The test stage executed the automated test suite and met the "
            "90% pass-rate threshold required for an automatic release.",
            "No action needed."
        ))
    else:
        cause = ("a large share of tests are failing, which usually means the "
                  "latest change broke existing functionality rather than a "
                  "flaky/isolated test") if test_block else \
                 ("a modest number of tests are failing — this can be a real "
                  "regression from the latest change, or a smaller number of "
                  "flaky/environment-dependent tests")
        conditions.append(_condition(
            "Test pass rate", False,
            f"Only {test_pass_rate}% of automated tests passed.",
            f"The automated test suite reported failures during the test "
            f"stage. At {test_pass_rate}%, {cause}.",
            "Open the Jenkins test report, identify which test cases failed "
            "and whether they point to a real regression, then fix the "
            "underlying code or the test before re-running the pipeline."
        ))
        if test_block:
            decision = "BLOCK"
        elif test_manual and decision == "RELEASE":
            decision = "MANUAL_APPROVAL"

    # ---------- Rule 4: Code quality ----------
    quality_ok = code_quality_score >= 80
    if quality_ok:
        conditions.append(_condition(
            "Code quality score", True,
            f"{code_quality_score}/100 from static analysis.",
            "The code-quality scan (e.g. SonarQube) rated maintainability, "
            "complexity, and duplication above the 80-point threshold.",
            "No action needed."
        ))
    else:
        conditions.append(_condition(
            "Code quality score", False,
            f"{code_quality_score}/100 from static analysis — below threshold.",
            "The code-quality scan found issues such as high cyclomatic "
            "complexity, duplicated code blocks, or code smells introduced in "
            "recent commits, pulling the maintainability score under 80. This "
            "does not break functionality today, but raises the risk of bugs "
            "and slows future changes.",
            "Review the code-quality report for the specific files flagged, "
            "refactor the highest-impact issues, and consider a manual code "
            "review before approving this release."
        ))
        if decision == "RELEASE":
            decision = "MANUAL_APPROVAL"

    # ---------- Rule 5: High-severity vulnerabilities ----------
    high_ok = high_vulns == 0
    if high_ok:
        conditions.append(_condition(
            "High-severity vulnerabilities", True,
            "No high-severity vulnerabilities detected.",
            "The security scan found zero high-severity findings for this "
            "build.",
            "No action needed."
        ))
    else:
        conditions.append(_condition(
            "High-severity vulnerabilities", False,
            f"{high_vulns} high-severity issue(s) detected.",
            "The security scan flagged high-severity (but not critical) "
            "issues — commonly an outdated dependency with a known "
            "vulnerability, or a moderate code-level security gap. These "
            "don't block release outright but need a human decision on "
            "acceptable risk before shipping.",
            "Have a reviewer assess the flagged issues; patch before release "
            "if feasible, or document the accepted risk if a manual approval "
            "is granted."
        ))
        if decision == "RELEASE":
            decision = "MANUAL_APPROVAL"

    # ---------- Rule 6: Previous release performance ----------
    prev_ok = previous_release_success_rate >= 70
    if prev_ok:
        conditions.append(_condition(
            "Previous release performance", True,
            f"{previous_release_success_rate}% success rate on recent releases.",
            "Recent releases from this pipeline have largely deployed and "
            "run successfully, with no signal of an unstable release trend.",
            "No action needed."
        ))
    else:
        conditions.append(_condition(
            "Previous release performance", False,
            f"Only {previous_release_success_rate}% success rate on recent "
            f"releases.",
            "A significant share of recent releases from this pipeline "
            "required rollback or produced post-deployment incidents. This "
            "pattern suggests systemic issues — e.g. insufficient test "
            "coverage, unstable environments, or rushed releases — rather "
            "than a one-off failure.",
            "Investigate the cause of recent release failures before "
            "proceeding; a manual approval step is recommended until the "
            "success rate stabilizes."
        ))
        if decision == "RELEASE":
            decision = "MANUAL_APPROVAL"

    return {"decision": decision, "conditions": conditions}
