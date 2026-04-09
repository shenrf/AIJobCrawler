#!/bin/bash
# AIJobCrawler — Overnight Batch Runner
# Usage: bash run.sh (or nohup bash run.sh > overnight-run.log 2>&1 &)

set -euo pipefail

export PYTHONUTF8=1
PYTHON="C:/Users/RR/AppData/Local/Programs/Python/Python311/python.exe"

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

mkdir -p logs data output

TASKS_FILE="tasks.json"
CONSECUTIVE_SKIPS=0
START_TIME=$(date +%s)

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

get_next_task() {
  $PYTHON -c "
import json, sys
with open('$TASKS_FILE', encoding='utf-8') as f:
    data = json.load(f)
for phase in data['phases']:
    for task in phase['tasks']:
        if not task['done'] and not task['skipped']:
            desc = task['description'].replace('\t', ' ').replace('\n', ' ')
            phase_name = phase['name'].replace('\t', ' ')
            print(f\"{task['id']}\t{phase_name}\t{desc}\")
            sys.exit(0)
print('ALL_DONE')
"
}

count_tasks() {
  $PYTHON -c "
import json
with open('$TASKS_FILE', encoding='utf-8') as f:
    data = json.load(f)
total = done = skipped = 0
for phase in data['phases']:
    for task in phase['tasks']:
        total += 1
        if task['done']: done += 1
        if task['skipped']: skipped += 1
print(f'{done}/{total} done, {skipped} skipped')
"
}

is_opus_task() {
  local task_id=$1
  $PYTHON -c "
import json
with open('$TASKS_FILE', encoding='utf-8') as f:
    data = json.load(f)
for phase in data['phases']:
    ids = [t['id'] for t in phase['tasks']]
    if $task_id == ids[0] or $task_id == ids[-1]:
        print('yes')
        exit(0)
print('no')
"
}

log "Starting AIJobCrawler overnight batch run"
log "Tasks: $(count_tasks)"

while true; do
  RESULT=$(get_next_task)

  if [ "$RESULT" = "ALL_DONE" ]; then
    log "All tasks complete!"
    break
  fi

  TASK_ID=$(echo "$RESULT" | cut -f1)
  PHASE_NAME=$(echo "$RESULT" | cut -f2)
  TASK_DESC=$(echo "$RESULT" | cut -f3)

  MODEL="sonnet"
  if [ "$(is_opus_task "$TASK_ID")" = "yes" ]; then
    MODEL="opus"
  fi

  log "Task $TASK_ID [$MODEL] — $TASK_DESC"

  PROMPT="You are working on the AIJobCrawler project. Your working directory is $(pwd).

IMPORTANT: Read progress.md FIRST for context from prior tasks.

Your task (Task $TASK_ID, $PHASE_NAME):
$TASK_DESC

After completing work:
1. Update tasks.json — set this task's 'done' to true and record duration_sec
2. Append to progress.md — record task id, what you did, files changed
3. Run: git add -A && git commit -m 'Task $TASK_ID: <short description>'
4. Do NOT work on any other task. Only complete Task $TASK_ID.
5. If you encounter an error you cannot resolve, document it in progress.md under Known Issues and exit."

  SUCCESS=false
  for ATTEMPT in 1 2 3; do
    log "  Attempt $ATTEMPT/3"

    if timeout 1800 claude -p "$PROMPT" \
      --model "$MODEL" \
      --allowedTools "Bash,Read,Write,Edit,Glob,Grep" \
      --dangerously-skip-permissions \
      --max-budget-usd 5 \
      > "logs/task-${TASK_ID}.log" 2>&1; then
      SUCCESS=true
      break
    else
      log "  Attempt $ATTEMPT failed (exit code $?)"
      if [ "$ATTEMPT" -lt 3 ]; then
        sleep $((30 * ATTEMPT))
      fi
    fi
  done

  TASK_DONE=$($PYTHON -c "
import json
with open('$TASKS_FILE', encoding='utf-8') as f:
    data = json.load(f)
for phase in data['phases']:
    for task in phase['tasks']:
        if task['id'] == $TASK_ID:
            print('yes' if task['done'] else 'no')
            exit(0)
")

  if [ "$TASK_DONE" = "yes" ]; then
    log "Task $TASK_ID: DONE"
    CONSECUTIVE_SKIPS=0
  else
    $PYTHON -c "
import json
with open('$TASKS_FILE', encoding='utf-8') as f:
    data = json.load(f)
for phase in data['phases']:
    for task in phase['tasks']:
        if task['id'] == $TASK_ID:
            task['skipped'] = True
            task['attempts'] = 3
with open('$TASKS_FILE', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
"
    log "Task $TASK_ID: SKIPPED after 3 attempts"
    CONSECUTIVE_SKIPS=$((CONSECUTIVE_SKIPS + 1))

    if [ "$CONSECUTIVE_SKIPS" -ge 3 ]; then
      log "WARNING: 3+ consecutive skips. Pausing 5 min (possible API issue)."
      sleep 300
      CONSECUTIVE_SKIPS=0
    fi
  fi
done

END_TIME=$(date +%s)
ELAPSED=$(( (END_TIME - START_TIME) / 60 ))
log "=========================================="
log "Batch run complete in ${ELAPSED} minutes"
log "Final status: $(count_tasks)"
log "=========================================="
