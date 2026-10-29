-- Optional, read-only check. No table or product data is changed.
USE culturelinkk;
SHOW COLUMNS FROM users;
SHOW INDEX FROM users;
SELECT COUNT(*) AS account_count FROM users;
SELECT user_id, email, role, created_at FROM users ORDER BY user_id DESC LIMIT 10;
