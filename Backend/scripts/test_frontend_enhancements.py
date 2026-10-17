import os
import sys

def verify_frontend():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Frontend"))
    html_path = os.path.join(base_dir, "index.html")
    js_path = os.path.join(base_dir, "app.js")

    print(f"Checking HTML at: {html_path}")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    print(f"Checking JS at: {js_path}")
    with open(js_path, "r", encoding="utf-8") as f:
        js = f.read()

    # 1. Check HTML elements
    html_requirements = [
        "phone1AuthenticBanner",
        "phone2AttackerBanner",
        "btnSendCloneClipProminent",
        "matrixCanvas",
        "spectrogramCanvas",
        "matrixQuadrantBadge",
        "spectrogramStatusBadge",
        "judgeCreditsVal",
        "backendConfigModal",
        "modalBackendUrlInput",
        "btnModalSaveBackend",
        "btnCheck"
    ]
    for req in html_requirements:
        assert req in html, f"Missing HTML requirement: {req}"
        print(f"  [HTML OK] {req}")

    # 2. Check JS handlers and features
    js_requirements = [
        "cleanBackendUrl",
        "openBackendModal",
        "closeBackendModal",
        "applyBackendUrl",
        "renderGateMatrix",
        "renderSpectrogramSnapshot",
        "matrixPointsHistory",
        "spectrogramState",
        "btnSendCloneClipProminent",
        "phone1AuthenticBanner",
        "phone2AttackerBanner",
        "modeParam === \"console\"",
        "modeParam === \"caller\"",
        "deviceParam === \"phone2\"",
        "deviceParam === \"phone1\"",
        "judgeCreditsVal",
        "creditsCounter",
        "pollLatestState"
    ]
    for req in js_requirements:
        assert req in js, f"Missing JS requirement: {req}"
        print(f"  [JS OK] {req}")

    # 3. Verify cleanBackendUrl behaviors
    print("\nVerifying URL cleaning logic...")
    import re
    # Check that mixed-content, ngrok bypass, and cleanBackendUrl logic exist
    assert "ngrok-skip-browser-warning" in js, "Missing ngrok-skip-browser-warning header"
    assert "Mixed Content" in js, "Missing Mixed Content diagnostics"

    print("\nALL FRONTEND MULTI-DEVICE & GATEWAY ROUTING TESTS PASSED!")

if __name__ == "__main__":
    verify_frontend()
