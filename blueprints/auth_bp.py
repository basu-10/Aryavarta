"""
blueprints/auth_bp.py — Registration, login, logout, battle history.
"""

from __future__ import annotations

from functools import wraps
import hashlib
import secrets
import time

from flask import (
    Blueprint, flash, redirect, render_template,
    request, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from db import models as m
from db.models import find_empty_cell
import config

auth_bp = Blueprint("auth", __name__)

REMEMBER_COOKIE_NAME = "bc_remember"
REMEMBER_TTL_SECONDS = 60 * 60 * 24 * 14  # 14 days


def _hash_remember_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _is_safe_local_path(next_url: str) -> bool:
    return bool(next_url) and next_url.startswith("/") and not next_url.startswith("//")


def _next_target(default_endpoint: str = "world.world_map") -> str:
    candidate = (
        request.form.get("next")
        or request.args.get("next")
        or ""
    ).strip()
    if _is_safe_local_path(candidate):
        return candidate
    return url_for(default_endpoint)


def _set_auth_session(player_id: int, username: str) -> None:
    session["player_id"] = player_id
    session["username"] = username
    session.permanent = True


def _issue_remember_token(player_id: int) -> str:
    token = secrets.token_urlsafe(48)
    token_hash = _hash_remember_token(token)
    expires_at_ts = int(time.time()) + REMEMBER_TTL_SECONDS
    m.create_remember_token(player_id, token_hash, expires_at_ts)
    return token


def _set_remember_cookie(response, token: str):
    response.set_cookie(
        REMEMBER_COOKIE_NAME,
        token,
        max_age=REMEMBER_TTL_SECONDS,
        httponly=True,
        samesite="Lax",
        secure=request.is_secure,
    )
    return response


@auth_bp.before_app_request
def restore_session_from_remember_cookie() -> None:
    if session.get("player_id"):
        return

    token = request.cookies.get(REMEMBER_COOKIE_NAME, "")
    if not token:
        return

    player = m.get_player_by_remember_token_hash(_hash_remember_token(token))
    if not player or player.get("role") == "banned":
        return

    _set_auth_session(player["id"], player["username"])


# ── Auth guard decorator ─────────────────────────────────────────────── #

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "player_id" not in session:
            next_url = request.full_path if request.query_string else request.path
            return redirect(url_for("auth.login", next=next_url.rstrip("?")))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "player_id" not in session:
            return redirect(url_for("auth.login"))
        player = m.get_player_by_id(session["player_id"])
        if not player or player["role"] != "admin":
            return "Forbidden", 403
        return f(*args, **kwargs)
    return decorated


# ── Routes ────────────────────────────────────────────────────────────── #

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm  = request.form.get("confirm", "").strip()

        if not username or not password:
            flash("Username and password are required.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif m.get_player_by_username(username):
            flash("Username already taken.", "error")
        else:
            pw_hash = generate_password_hash(password)
            player_id = m.create_player(username, pw_hash)

            # Assign a random castle on the world grid
            import random
            slot_count = random.choices(
                [4, 5, 6, 7, 8, 9, 10],
                weights=config.FORT_SLOT_WEIGHTS,
            )[0]
            cx, cy = find_empty_cell()
            m.create_castle(player_id, slot_count, cx, cy)

            _set_auth_session(player_id, username)
            token = _issue_remember_token(player_id)
            response = redirect(url_for("world.world_map"))
            return _set_remember_cookie(response, token)

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = _next_target()

    if "player_id" in session:
        return redirect(next_url)

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        player = m.get_player_by_username(username)
        if player and check_password_hash(player["password_hash"], password):
            if player["role"] == "banned":
                flash("Your account has been banned.", "error")
            else:
                _set_auth_session(player["id"], player["username"])
                token = _issue_remember_token(player["id"])
                response = redirect(next_url)
                return _set_remember_cookie(response, token)
        else:
            flash("Invalid username or password.", "error")

    return render_template("auth/login.html", next_url=next_url)


@auth_bp.route("/logout")
def logout():
    token = request.cookies.get(REMEMBER_COOKIE_NAME, "")
    if token:
        m.revoke_remember_token_hash(_hash_remember_token(token))
    session.clear()
    response = redirect(url_for("auth.login"))
    response.delete_cookie(REMEMBER_COOKIE_NAME, samesite="Lax", secure=request.is_secure)
    return response


@auth_bp.route("/battles")
@login_required
def battles():
    player = m.get_player_by_id(session["player_id"])
    missions = m.get_recent_resolved_missions(session["player_id"], limit=50)
    wins = sum(1 for mis in missions if mis.get("winner") == "attacker")
    losses = sum(1 for mis in missions if mis.get("winner") == "defender")
    return render_template(
        "auth/battles.html",
        player=player,
        missions=missions,
        wins=wins,
        losses=losses,
    )


@auth_bp.route("/api/tutorial/seen", methods=["POST"])
@login_required
def mark_tutorial_seen():
    m.mark_tutorial_seen(session["player_id"])
    return "", 204


@auth_bp.route("/profile")
@login_required
def profile_legacy_redirect():
    return redirect(url_for("auth.battles"))
