-- Token revocation list for cross-service logout.
-- Any service can call auth-service /logout to revoke current access token.

CREATE TABLE IF NOT EXISTS revoked_tokens (
  token_hash varchar(64) PRIMARY KEY,
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expires_at ON revoked_tokens(expires_at);

