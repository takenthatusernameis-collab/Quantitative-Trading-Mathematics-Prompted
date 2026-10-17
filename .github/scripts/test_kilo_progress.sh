#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

test_root="$(mktemp -d)"
trap 'rm -rf "$test_root"' EXIT

export RUNNER_TEMP="$test_root"
export GITHUB_RUN_ID="progress-helper-test"
export GITHUB_RUN_ATTEMPT="1"
WORKFLOW_STARTED_EPOCH="$(date +%s)"
cutoff_epoch=$(( $(date +%s) + 60 ))
SESSION_LIMIT_POLICY=3
agent_index=2
session_attempt=4
sessions_completed=1
failed_sessions=0
persisted_checkpoints=2
last_verified_checkpoint_sha="abc123"

source .github/scripts/kilo-progress.sh

if ! declare -F write_progress >/dev/null; then
  echo "ERROR: write_progress was not defined by the shared helper." >&2
  exit 1
fi

write_progress "smoke-phase" "smoke test detail"

grep -Fq 'phase=smoke-phase' "$KILO_PROGRESS_STATE_FILE"
grep -Fq 'detail=smoke test detail' "$KILO_PROGRESS_STATE_FILE"
grep -Fq 'session_limit=3' "$KILO_PROGRESS_STATE_FILE"
grep -Fq 'session=2' "$KILO_PROGRESS_STATE_FILE"
grep -Fq 'phase=smoke-phase' "$KILO_PROGRESS_LOG"
grep -Fq 'detail=smoke test detail' "$KILO_PROGRESS_LOG"
grep -Fq 'state_written=1' "$KILO_PROGRESS_LOG"

# A state-file failure must not make telemetry fatal or suppress the log record.
KILO_PROGRESS_STATE_FILE="$test_root/missing-directory/state.txt"
write_progress "nonfatal-state-failure" "logging still works" 2>/dev/null
grep -Fq 'phase=nonfatal-state-failure' "$KILO_PROGRESS_LOG"
grep -Fq 'state_written=0' "$KILO_PROGRESS_LOG"

# Restore a writable state file before verifying controller-driven counters.
KILO_PROGRESS_STATE_FILE="$test_root/kilo-progress-state-progress-helper-test-1.txt"

# The controller must populate the progress counters it advertises. The
# telemetry helper emits sessions_completed/persisted_checkpoints/
# last_verified_checkpoint_sha, but the controller must drive them; otherwise
# the CI progress signal is permanently stale (completed=0/checkpoints=0/
# verified_sha=none). Simulate a successful checkpoint-persistence handshake.
persisted_checkpoints=1
last_verified_checkpoint_sha="abc123def456"
sessions_completed=1
write_progress "checkpoint-verified" "remote head verified at abc123def456 after 1 attempt(s)"
grep -Fq 'checkpoints=1' "$KILO_PROGRESS_STATE_FILE"
grep -Fq 'completed=1' "$KILO_PROGRESS_STATE_FILE"
grep -Fq 'verified_checkpoint_sha=abc123def456' "$KILO_PROGRESS_STATE_FILE"
grep -Fq 'verified_sha=abc123def456' "$KILO_PROGRESS_LOG"

echo "Kilo progress helper smoke test, non-fatal state-write test, and controller telemetry population test: OK"
