"""Create a HireScout login.

    python -m scripts.create_user --email you@example.com --name "Your Name" --role admin

The password is prompted for (never pass it on the command line).
"""

import argparse
import getpass
import sys

from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import User
from app.security import hash_password


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", choices=["admin", "recruiter"], default="admin")
    args = parser.parse_args()

    password = getpass.getpass("Password (min 8 chars): ")
    if len(password) < 8:
        print("Password must be at least 8 characters.", file=sys.stderr)
        return 1
    if getpass.getpass("Repeat password: ") != password:
        print("Passwords do not match.", file=sys.stderr)
        return 1

    Base.metadata.create_all(bind=engine)
    email = args.email.strip().lower()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user:
            user.password_hash = hash_password(password)
            user.name, user.role = args.name, args.role
            action = "Updated"
        else:
            db.add(User(name=args.name, email=email, password_hash=hash_password(password), role=args.role))
            action = "Created"
        db.commit()
    print(f"{action} {args.role} user {email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
