"""
Quick checks for classify() — run this before handing the module off.
Plain asserts, no pytest needed: python test_classifier.py
"""

from classifier import classify, to_coarse


def test_source_code_detected():
    result = classify("def add(a, b):\n    return a + b")
    assert result["label"] == "SOURCE_CODE", f"expected SOURCE_CODE, got {result['label']}"


def test_safe_detected():
    result = classify("What's a good recipe for pasta tonight?")
    assert result["label"] == "SAFE", f"expected SAFE, got {result['label']}"


def test_output_shape():
    result = classify("Can you help me plan my week?")
    assert set(result.keys()) == {"label", "confidence"}, f"unexpected keys: {result.keys()}"
    assert 0.0 <= result["confidence"] <= 1.0, f"confidence out of range: {result['confidence']}"
    assert isinstance(result["label"], str)


def test_empty_input_raises():
    try:
        classify("")
        raise AssertionError("classify('') should have raised ValueError")
    except ValueError:
        pass  # expected

    try:
        classify("   ")
        raise AssertionError("classify('   ') should have raised ValueError")
    except ValueError:
        pass  # expected


def test_coarse_mapping():
    assert to_coarse("SAFE") == "SAFE"
    assert to_coarse("SOURCE_CODE") == "SOURCE_CODE"
    assert to_coarse("CONFIDENTIAL") == "CONFIDENTIAL"
    assert to_coarse("PASSWORD") == "CONFIDENTIAL"
    assert to_coarse("EMAIL") == "CONFIDENTIAL"


if __name__ == "__main__":
    tests = [
        test_source_code_detected,
        test_safe_detected,
        test_output_shape,
        test_empty_input_raises,
        test_coarse_mapping,
    ]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"PASS  {t.__name__}")
    print(f"\n{passed}/{len(tests)} tests passed")
