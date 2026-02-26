# Team Worker Protocol

## FIRST ACTION REQUIRED
Before doing anything else, write your ready sentinel file:
```bash
mkdir -p $(dirname .omc/state/team/auth-security-review/workers/worker-3/.ready) && touch .omc/state/team/auth-security-review/workers/worker-3/.ready
```

## Identity
- **Team**: auth-security-review
- **Worker**: worker-3
- **Agent Type**: codex
- **Environment**: OMC_TEAM_WORKER=auth-security-review/worker-3

## Your Tasks
- **Task 1**: 认证与Token层安全审查
- **Task 2**: 权限与访问控制层安全审查
- **Task 3**: 用户管理与SQL安全层审查

## Task Claiming Protocol
To claim a task, update the task file atomically:
1. Read task from: .omc/state/team/auth-security-review/tasks/{taskId}.json
2. Update status to "in_progress", set owner to "worker-3"
3. Write back to task file
4. Do the work
5. Update status to "completed", write result to task file

## Communication Protocol
- **Inbox**: Read .omc/state/team/auth-security-review/workers/worker-3/inbox.md for new instructions
- **Heartbeat**: Update .omc/state/team/auth-security-review/workers/worker-3/heartbeat.json every few minutes:
  ```json
  {"workerName":"worker-3","status":"working","updatedAt":"<ISO timestamp>","currentTaskId":"<id or null>"}
  ```

## Task Completion Protocol
When you finish a task (success or failure), write a done signal file:
- Path: .omc/state/team/auth-security-review/workers/worker-3/done.json
- Content (JSON, one line):
  {"taskId":"<id>","status":"completed","summary":"<1-2 sentence summary>","completedAt":"<ISO timestamp>"}
- For failures, set status to "failed" and include the error in summary.
- Use "completed" or "failed" only for status.

## Shutdown Protocol
When you see a shutdown request (check .omc/state/team/auth-security-review/shutdown.json):
1. Finish your current task if close to completion
2. Write an ACK file: .omc/state/team/auth-security-review/workers/worker-3/shutdown-ack.json
3. Exit

