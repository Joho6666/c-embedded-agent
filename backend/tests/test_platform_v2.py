"""Phase I tests: capability matrix, approval policy, ContextManifest, ActionPlan."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.agent.context import build_context, attach_manifest
from app.agent.planner import make_plan
from app.core.approvals import policy
from app.core.capabilities import platform_capabilities
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------- capabilities

def test_capability_matrix_is_honest():
    platforms = {p["platformId"]: p for p in platform_capabilities()}
    stm = platforms["stm32"]["capabilities"]
    # Build verified only when the toolchain really is present
    build = stm["BUILD"]
    assert build["status"] in {"VERIFIED", "NOT_INSTALLED"}
    assert build["evidence"]
    # Simulation is backed by the real Renode spike
    sim = stm["SIMULATE"]
    assert sim["status"] in {"VERIFIED", "NOT_INSTALLED"}
    assert "RENODE_SPIKE" in sim["evidence"] or "Renode" in sim["evidence"]
    # Hardware validate cannot claim VERIFIED without a hardware lab session
    assert stm["HARDWARE_VALIDATE"]["status"] != "VERIFIED"
    # No platform may fake a backend adapter it does not have
    for pid in ("esp32", "c51", "rp2040", "host-c"):
        caps = platforms[pid]["capabilities"]
        assert all(c["status"] == "NOT_SUPPORTED" for c in caps.values())


def test_api_platforms_endpoint():
    r = client.get("/api/platforms")
    assert r.status_code == 200
    body = r.json()
    ids = {p["platformId"] for p in body["platforms"]}
    assert {"stm32", "esp32"} <= ids


def test_api_approvals_policy_endpoint():
    r = client.get("/api/approvals/policy")
    assert r.status_code == 200
    body = r.json()
    assert body["levels"]["DANGEROUS_HARDWARE"]["default"] == "deny"
    assert "mass_erase" in body["dangerousOperations"]


# ---------------------------------------------------------------- manifest

def test_build_context_attaches_manifest(tmp_path: Path):
    (tmp_path / "Core" / "Src").mkdir(parents=True)
    (tmp_path / "Core" / "Src" / "main.c").write_text("int main(){}\n", encoding="utf-8")
    ctx = build_context(tmp_path, iteration=1, prompt="LED 500ms 闪烁")
    manifest = ctx.get("manifest")
    assert manifest and len(manifest) >= 4
    for entry in manifest:
        assert {"source", "key", "reason", "priority", "tokens", "hash"} <= set(entry)
        assert entry["tokens"] >= 1 and len(entry["hash"]) == 12
    assert ctx["manifestTokens"] == sum(m["tokens"] for m in manifest)
    # determinism: same content → same hash
    again = attach_manifest(dict(ctx))
    by_key = {m["key"]: m["hash"] for m in manifest}
    by_key2 = {m["key"]: m["hash"] for m in again["manifest"]}
    assert by_key == by_key2


# ---------------------------------------------------------------- action plan

def test_action_plan_steps_carry_enforcement_fields():
    plan = make_plan("USART1 DMA 接收，每秒输出统计")
    assert plan and len(plan) >= 5
    for step in plan:
        assert {"action", "tool", "permission", "expectedEvidence", "retryPolicy"} <= set(step)
    build_steps = [s for s in plan if s["action"] == "build"]
    assert build_steps and build_steps[0]["permission"] == "SAFE_BUILD"
    assert "Error Memory" in build_steps[0]["retryPolicy"]
    write_steps = [s for s in plan if s["permission"] == "PROJECT_WRITE"]
    assert write_steps  # peripheral config / edits are gated


def test_action_plan_is_deterministic():
    assert make_plan("LED 闪烁") == make_plan("LED 闪烁")
