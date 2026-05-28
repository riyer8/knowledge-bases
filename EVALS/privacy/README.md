# Privacy Evals

Tests that the privacy pipeline works correctly. These must pass before any privacy
module change is considered complete.

## Test Cases

### 1. Password Field Detection

Input events that contain password form context. Expected: `should_pause = True`.

Test file: `test_cases/password_detection.json`

Threshold: true positive rate > 99%, false positive rate < 1%

### 2. Sensitive Site Detection

Input events with URLs from `sensitive_sites.py`. Expected: `should_pause = True`.
Input events with normal URLs. Expected: `should_pause = False`.

Threshold: 100% detection of listed sites.

### 3. Name Hashing Consistency

Same name input on multiple runs. Expected: same hash every time.
Different names. Expected: different hashes.

Threshold: 100% consistency.

### 4. Round-Trip Rendering

Hash a name, store it, retrieve it from map, display it. Expected: original name appears.

Threshold: 100%.

### 5. Clean Event Contains No PII

Run 50 events with known PII through the full pipeline.
Check output events for any unhashed names, emails, or phone numbers.

Threshold: 0 PII leaks.

### 6. False Positive Rate on Normal Content

Run 100 normal content events (news articles, documentation, etc.).
Count events incorrectly flagged as high-sensitivity.

Threshold: false positive rate < 5%.

## Running Evals

```bash
python -m pytest EVALS/privacy/ -v
```

## Adding Test Cases

Add to `test_cases/` as JSON files following the event schema.
Document expected output alongside each test case.
