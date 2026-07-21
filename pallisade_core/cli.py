from __future__ import annotations

import secrets
import sys

import typer

from pallisade_core.db.session import get_session_factory
from pallisade_core.users import service as users

app = typer.Typer(help="Pallisade admin CLI")


def _gen_temp_password() -> str:
    return secrets.token_urlsafe(12)[:16]


@app.command("bootstrap-admin")
def bootstrap_admin(email: str = typer.Option(...), name: str = typer.Option(...)) -> None:
    """Create the first admin user. Refuses if any user exists."""
    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        if users.count_users(session) > 0:
            typer.echo("Refusing: users already exist. Use create-user instead.", err=True)
            raise typer.Exit(code=1)
        pw = _gen_temp_password()
        users.create_user(
            session, email=email, name=name, role="admin", password=pw, must_change_password=True,
        )
        session.commit()
        typer.echo(f"Created admin {email}. Temporary password: {pw}")


@app.command("create-user")
def create_user(
    email: str = typer.Option(...),
    name: str = typer.Option(...),
    role: str = typer.Option("member"),
) -> None:
    if role not in {"admin", "member"}:
        typer.echo("--role must be 'admin' or 'member'", err=True)
        raise typer.Exit(1)
    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        if users.find_by_email(session, email) is not None:
            typer.echo(f"User {email} already exists.", err=True)
            raise typer.Exit(1)
        pw = _gen_temp_password()
        users.create_user(
            session, email=email, name=name, role=role, password=pw, must_change_password=True,
        )
        session.commit()
        typer.echo(f"Created {role} {email}. Temporary password: {pw}")


@app.command("reset-password")
def reset_password(email: str = typer.Option(...)) -> None:
    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        u = users.find_by_email(session, email)
        if u is None:
            typer.echo(f"No such user: {email}", err=True)
            raise typer.Exit(1)
        pw = _gen_temp_password()
        users.set_password(session, u, pw)
        u.must_change_password = True
        session.add(u)
        session.commit()
        typer.echo(f"Reset password for {email}. Temporary password: {pw}")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(app())
