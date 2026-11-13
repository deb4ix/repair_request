BEGIN;
CREATE TABLE IF NOT EXISTS request_messages (
 id BIGSERIAL PRIMARY KEY,
 request_id BIGINT NOT NULL REFERENCES repair_requests(id) ON DELETE RESTRICT,
 sender_id BIGINT NOT NULL REFERENCES app_users(id) ON DELETE RESTRICT,
 body TEXT NOT NULL CHECK (length(trim(body)) BETWEEN 1 AND 4000),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_request_messages_request ON request_messages(request_id,id);
CREATE TABLE IF NOT EXISTS request_notifications (
 id BIGSERIAL PRIMARY KEY,
 user_id BIGINT NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
 request_id BIGINT REFERENCES repair_requests(id) ON DELETE SET NULL,
 kind VARCHAR(20) NOT NULL,
 text TEXT NOT NULL,
 is_read BOOLEAN NOT NULL DEFAULT FALSE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_request_notifications_user ON request_notifications(user_id,id DESC);
CREATE TABLE IF NOT EXISTS request_status_history (
 id BIGSERIAL PRIMARY KEY,
 request_id BIGINT NOT NULL REFERENCES repair_requests(id) ON DELETE RESTRICT,
 actor_id BIGINT NOT NULL REFERENCES app_users(id) ON DELETE RESTRICT,
 old_status VARCHAR(30) NOT NULL,
 new_status VARCHAR(30) NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_request_status_history_request ON request_status_history(request_id,id);
COMMIT;
