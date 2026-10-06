"""Trace the action requested by a policy, sent by an adapter, and observed."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time


MESSAGES = {
    "fr": {"missing_sent": "Action envoyée absente à l’étape {step}", "missing_observed": "Action mesurée absente à l’étape {step}", "tracking": "Écart de suivi sur {field} à l’étape {step}", "latency": "Latence excessive à l’étape {step}", "modified": "Action demandée modifiée sur {field} à l’étape {step}", "input": "Entrée invalide", "summary": "{steps} étape(s), {failures} échec(s), {unknown} non vérifiée(s)"},
    "en": {"missing_sent": "Sent action missing at step {step}", "missing_observed": "Measured action missing at step {step}", "tracking": "Tracking error on {field} at step {step}", "latency": "Excessive latency at step {step}", "modified": "Requested action changed on {field} at step {step}", "input": "Invalid input", "summary": "{steps} step(s), {failures} failure(s), {unknown} unverified"},
    "es": {"missing_sent": "Falta la acción enviada en el paso {step}", "missing_observed": "Falta la acción medida en el paso {step}", "tracking": "Error de seguimiento en {field} en el paso {step}", "latency": "Latencia excesiva en el paso {step}", "modified": "Acción solicitada modificada en {field} en el paso {step}", "input": "Entrada no válida", "summary": "{steps} paso(s), {failures} fallo(s), {unknown} sin verificar"},
}


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_rules(rules):
    if not isinstance(rules, dict) or set(rules) != {"fields", "max_latency_ms"}:
        raise ValueError("rules")
    if not _number(rules["max_latency_ms"]) or rules["max_latency_ms"] < 0:
        raise ValueError("max_latency_ms")
    fields = rules["fields"]
    if not isinstance(fields, dict) or not fields:
        raise ValueError("fields")
    for name, spec in fields.items():
        if not isinstance(name, str) or not name or not isinstance(spec, dict) or set(spec) != {"unit", "max_tracking_error"}:
            raise ValueError("field specification")
        if not isinstance(spec["unit"], str) or not spec["unit"] or not _number(spec["max_tracking_error"]) or spec["max_tracking_error"] < 0:
            raise ValueError("field threshold")
    return rules


def _finding(locale, code, episode, step, field=None, **details):
    return {"code": code, "episode": episode, "step": step, "field": field, "details": details, "message": MESSAGES[locale][code].format(step=step, field=field)}


def audit(rows, rules, locale="en"):
    if locale not in MESSAGES:
        raise ValueError("locale")
    validate_rules(rules)
    if not isinstance(rows, list) or not rows:
        raise ValueError("empty trace")
    findings = []
    steps = []
    previous = {}
    for line, row in enumerate(rows, 1):
        if not isinstance(row, dict) or not isinstance(row.get("episode"), str) or not row["episode"] or not isinstance(row.get("step"), int) or isinstance(row["step"], bool) or row["step"] < 0:
            raise ValueError(f"line {line}: episode/step")
        episode, step = row["episode"], row["step"]
        if step <= previous.get(episode, -1):
            raise ValueError(f"line {line}: duplicate or unordered step")
        previous[episode] = step
        requested = row.get("requested")
        if not isinstance(requested, dict) or set(requested) != set(rules["fields"]) or not all(_number(value) for value in requested.values()):
            raise ValueError(f"line {line}: requested")
        sent, observed = row.get("sent"), row.get("observed")
        for label, values in (("sent", sent), ("observed", observed)):
            if values is not None and (not isinstance(values, dict) or set(values) != set(requested) or not all(_number(value) for value in values.values())):
                raise ValueError(f"line {line}: {label}")
        stamps = [row.get("requested_at_ms"), row.get("sent_at_ms"), row.get("observed_at_ms")]
        if not _number(stamps[0]) or stamps[0] < 0 or (sent is not None and (not _number(stamps[1]) or stamps[1] < stamps[0])) or (observed is not None and (not _number(stamps[2]) or stamps[2] < (stamps[1] if _number(stamps[1]) else stamps[0]))):
            raise ValueError(f"line {line}: timestamps")
        if row.get("units") != {field: spec["unit"] for field, spec in rules["fields"].items()}:
            raise ValueError(f"line {line}: units")
        local = []
        if sent is None:
            local.append(_finding(locale, "missing_sent", episode, step))
        else:
            if stamps[1] - stamps[0] > rules["max_latency_ms"]:
                local.append(_finding(locale, "latency", episode, step, duration_ms=stamps[1] - stamps[0]))
            for field in requested:
                if requested[field] != sent[field]:
                    local.append(_finding(locale, "modified", episode, step, field, delta=sent[field] - requested[field]))
            if observed is None:
                local.append(_finding(locale, "missing_observed", episode, step))
            else:
                for field, spec in rules["fields"].items():
                    delta = observed[field] - sent[field]
                    if abs(delta) > spec["max_tracking_error"]:
                        local.append(_finding(locale, "tracking", episode, step, field, delta=delta, threshold=spec["max_tracking_error"]))
        status = "fail" if any(item["code"] in ("tracking", "latency") for item in local) else "inconclusive" if any(item["code"].startswith("missing_") for item in local) else "pass"
        steps.append({"episode": episode, "step": step, "status": status, "findings": local})
        findings.extend(local)
    failures = sum(item["status"] == "fail" for item in steps)
    unknown = sum(item["status"] == "inconclusive" for item in steps)
    return {"format": "robot-action-chain/v1", "locale": locale, "status": "fail" if failures else "inconclusive" if unknown else "pass", "summary": MESSAGES[locale]["summary"].format(steps=len(steps), failures=failures, unknown=unknown), "steps": steps, "findings": findings}


def record_send(robot, requested, output, *, episode, step, units, observe=None, clock=None):
    """Wrap an explicit Robot.send_action call; never dispatches a command by itself."""
    clock = clock or (lambda: time.monotonic_ns() // 1_000_000)
    requested = dict(requested)
    start = clock()
    sent = robot.send_action(dict(requested))
    sent_at = clock()
    observed = observe() if observe is not None else None
    observed_at = clock() if observed is not None else None
    row = {"episode": episode, "step": step, "requested_at_ms": start, "sent_at_ms": sent_at, "observed_at_ms": observed_at, "requested": requested, "sent": sent, "observed": observed, "units": units}
    with Path(output).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    return sent


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit robot actions / Auditer les actions robotiques / Auditar acciones robóticas")
    parser.add_argument("trace")
    parser.add_argument("rules")
    parser.add_argument("--locale", choices=MESSAGES, default="en")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        raw = Path(args.trace).read_bytes()
        rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
        rules = json.loads(Path(args.rules).read_text(encoding="utf-8"))
        report = audit(rows, rules, args.locale)
        report["source"] = {"path": args.trace, "sha256": hashlib.sha256(raw).hexdigest()}
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        print(f"{MESSAGES[args.locale]['input']}: {exc if args.locale == 'en' else type(exc).__name__}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return {"pass": 0, "fail": 1, "inconclusive": 3}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
