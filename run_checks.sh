#!/usr/bin/env bash
# Consolidated gate check for the SocialCal redesign.
# Mirrors the CI gates (flake8 hard+soft, Django checks, pytest) but skips the
# scraper test modules whose heavy deps don't build on this Python build.
set +e
cd "$(dirname "$0")"
export DJANGO_SETTINGS_MODULE=socialcal.test_settings
export DISABLE_REDIS_CACHE=true
OUT=/tmp/checks_out.txt
: > "$OUT"

say() { echo "$@" | tee -a "$OUT"; }

say "===== 1. flake8 HARD gate (E9,F63,F7,F82) ====="
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics >>"$OUT" 2>&1
say "flake8_hard_exit=$?"

say "===== 2. flake8 SOFT gate (complexity/line-length, non-failing) ====="
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics >>"$OUT" 2>&1
say "flake8_soft_done"

say "===== 3. manage.py check ====="
python3 manage.py check >>"$OUT" 2>&1
say "django_check_exit=$?"

say "===== 4. makemigrations --check --dry-run ====="
python3 manage.py makemigrations --check --dry-run >>"$OUT" 2>&1
say "makemigrations_check_exit=$?"

say "===== 5. pytest (excluding scraper-dep modules) ====="
python3 -m pytest --ds=socialcal.test_settings -p no:cacheprovider -q -o addopts="" -p no:randomly \
  --ignore=events/tests/test_spotify.py \
  --ignore=events/tests/test_generic_crawl4ai.py \
  --ignore=events/tests/test_ical_scraper.py \
  --ignore=events/management/commands/test_crawl4ai.py \
  --ignore=events/management/commands/test_ical.py \
  >>"$OUT" 2>&1
say "pytest_exit=$?"

say "===== SUMMARY ====="
grep -E "[0-9]+ (passed|failed|error|skipped)|Interrupted|INTERNALERROR" "$OUT" | tail -3 | tee -a "$OUT"
echo "----- FAILED/ERROR (unique) -----" | tee -a "$OUT"
grep -E "^(FAILED|ERROR)" "$OUT" | sed -E 's/ - .*//' | sort -u | tee -a "$OUT"
say "CHECKS_COMPLETE"
