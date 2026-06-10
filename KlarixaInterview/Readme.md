Design an Audit Logging System 

A SaaS application needs to maintain audit logs for regulatory and operational purposes. 

Whenever a user performs an action, an audit record should be generated, for example: 

"User A performed Action B at Time T" 

Requirements 

Functional Requirements 

Capture audit logs for user actions.  

Audit logs should be query able for reporting and compliance purposes.  

Audit logging should not significantly increase the latency of the user-facing action.  

Consistency Requirements 

If a user action is successfully recorded, the corresponding audit log must eventually exist.  

If an audit log exists, the corresponding user action must have been successfully recorded.  

No audit log should exist for a failed action.  

No successful action should be missing an audit log.  

Non-Functional Requirements 

High throughput (thousands of actions per second).  

Reliable event delivery.  

Scalable and fault tolerant.  

Support asynchronous processing. 

Fault Tolerance for Queue Outage

Use the Transactional Outbox pattern.

Problem:

The application updates the business database successfully and then tries to publish an audit log message to a queue. If the queue is down at that moment, publishing fails and the successful action may never get an audit log.

Do not publish directly to the queue inside the business transaction as the only source of truth. Instead, write the audit event to an outbox table in the same database transaction as the business update.

Recommended flow:

1. Start database transaction.
2. Perform the business update.
3. Insert an audit event into an `audit_outbox` table with status `PENDING`.
4. Commit the transaction.
5. A separate background worker reads `PENDING` outbox rows and publishes them to the messaging queue.
6. After successful publish, mark the outbox row as `PUBLISHED`.
7. If publish fails because the queue is down, keep the row as `PENDING` or mark it `FAILED_RETRYABLE` and retry later with backoff.

This gives the required guarantees:

- If the business update commits, the audit event is durably stored.
- If the business update rolls back, no audit event is stored.
- If the queue is down, the API still succeeds after the database commit, and the message is published later.
- Once the queue comes back, the worker drains pending outbox rows and recovers automatically.

Suggested outbox table:

```sql
CREATE TABLE audit_outbox (
    id UUID PRIMARY KEY,
    aggregate_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    retry_count INT NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    published_at TIMESTAMP NULL,
    last_error TEXT NULL
);
```

Worker behavior:

```text
Every few seconds:
  fetch pending rows where next_retry_at <= now()
  publish each event to the queue
  if publish succeeds:
    mark row PUBLISHED
  if publish fails:
    increment retry_count
    set next_retry_at using exponential backoff
    store last_error
```

Production considerations:

- Make consumers idempotent because a message can be published more than once if the worker crashes after publishing but before marking the row as `PUBLISHED`.
- Include a unique event id in every message so consumers can deduplicate.
- Use row locking such as `FOR UPDATE SKIP LOCKED` when multiple workers process the outbox.
- Add alerts for old pending rows, high retry counts, and queue publish failures.
- Move permanently failing messages to a dead-letter flow after a configured retry limit.
