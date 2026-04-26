"""
blueprints/auth_bp.py — Registration, login, logout, battle history.
"""

from __future__ import annotations

from functools import wraps

from flask import (
    Blueprint, flash, redirect, render_template,
    request, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from db import models as m
from db.models import find_empty_cell
import config

auth_bp = Blueprint("auth", __name__)


# ── Auth guard decorator ─────────────────────────────────────────────── #

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "player_id" not in session:
            return redirect(url_for("auth.login"))
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

            session["player_id"] = player_id
            session["username"] = username
            return redirect(url_for("world.world_map"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "player_id" in session:
        return redirect(url_for("world.world_map"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        player = m.get_player_by_username(username)
        if player and check_password_hash(player["password_hash"], password):
            if player["role"] == "banned":
                flash("Your account has been banned.", "error")
            else:
                session["player_id"] = player["id"]
                session["username"] = player["username"]
                return redirect(url_for("world.world_map"))
        else:
            flash("Invalid username or password.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


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


@auth_bp.route("/profile")
@login_required
def profile_legacy_redirect():
    return redirect(url_for("auth.battles"))
