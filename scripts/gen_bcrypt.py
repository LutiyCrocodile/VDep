"""Print bcrypt hash for admin123 (run: pip install bcrypt && python scripts/gen_bcrypt.py)."""
import bcrypt

h = bcrypt.hashpw(b"admin123", bcrypt.gensalt(rounds=12))
print(h.decode())
