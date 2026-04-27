"""
blueprints/clan_bp.py — Full clan system.

Positions:   leader > co-leader > elder > member
Promotion rules:
  leader    → can promote/demote anyone
  co-leader → can promote/demote elders and members
  elder     → can only accept/reject join applications
  member    → no management abilities

Creation cost: 1000 Food, Timber, Gold, Metal each.
"""

from __future__ import annotations

from flask import (
    Blueprint, jsonify, render_template,
    request, session,
)

from blueprints.auth_bp import login_required
from db import models as m

clan_bp = Blueprint("clan", __name__)

_MAX_MESSAGE_LEN = 500

# ── Permission helpers ──────────────────────────────────────────────── #

_RANK = {"member": 0, "elder": 1, "co-leader": 2, "leader": 3}


def _rank(role: str | None) -> int:
    return _RANK.get(role or "member", 0)


def _can_manage(actor_role: str | None, target_role: str | None) -> bool:
    """
    Return True when actor can promote/demote target.
    leader    → anyone below leader
    co-leader → elders and members (rank < co-leader)
    elder     → nobody
    member    → nobody
    """
    ar = _rank(actor_role)
    tr = _rank(target_role)
    if ar < _rank("elder"):  # member
        return False
    if ar == _rank("elder"):  # elder can't manage
        return False
    if ar == _rank("co-leader"):
        return tr < _rank("co-leader")
    if ar == _rank("leader"):
        return tr < _rank("leader")
    return False


def _can_accept_applications(role: str | None) -> bool:
    return _rank(role) >= _rank("elder")


# ── Page routes ─────────────────────────────────────────────────────── #

@clan_bp.route("/clan")
@login_required
def clan_page():
    player = m.get_player_by_id(session["player_id"])
    if player.get("clan_id"):
        clan    = m.get_clan_with_member_count(player["clan_id"])
        members = m.get_clan_members(player["clan_id"])
        messages = m.get_clan_messages(
            player["clan_id"],
            since_iso=player.get("clan_joined_at"),
        )
        applications = m.get_pending_applications(player["clan_id"])
        all_clans = None
    else:
        clan = members = messages = applications = None
        all_clans = m.get_all_clans()
    return render_template(
        "clan/clan.html",
        player=player,
        clan=clan,
        members=members,
        messages=messages,
        applications=applications,
        all_clans=all_clans,
        cost=m.CLAN_CREATION_COST,
    )


@clan_bp.route("/clan/<int:clan_id>")
@login_required
def clan_public(clan_id: int):
    """Public clan page — any logged-in player can view; non-members see an apply button."""
    player = m.get_player_by_id(session["player_id"])
    clan = m.get_clan_with_member_count(clan_id)
    if not clan:
        return "Clan not found", 404
    members = m.get_clan_members(clan_id)
    is_member = player.get("clan_id") == clan_id
    existing_app = m.get_player_application(clan_id, player["id"]) if not is_member else None
    return render_template(
        "clan/clan_public.html",
        player=player,
        clan=clan,
        members=members,
        is_member=is_member,
        existing_app=existing_app,
    )


# ── API: Clan CRUD ───────────────────────────────────────────────────── #

@clan_bp.route("/api/clan/create", methods=["POST"])
@login_required
def api_create_clan():
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name", "").strip()
    if not name or len(name) > 40:
        return jsonify({"error": "Clan name required (max 40 chars)"}), 400
    player = m.get_player_by_id(session["player_id"])
    if player.get("clan_id"):
        return jsonify({"error": "You are already in a clan"}), 409
    if m.get_clan_by_name(name):
        return jsonify({"error": "Clan name taken"}), 409
    cost = m.CLAN_CREATION_COST
    ok = m.deduct_player_resources(
        session["player_id"],
        food=cost["food"], timber=cost["timber"],
        gold=cost["gold"], metal=cost["metal"],
    )
    if not ok:
        return jsonify({"error": "Not enough resources (need 1000 of each)"}), 400
    clan_id = m.create_clan(name, session["player_id"])
    return jsonify({"ok": True, "clan_id": clan_id})


@clan_bp.route("/api/clan/leave", methods=["POST"])
@login_required
def api_leave_clan():
    player = m.get_player_by_id(session["player_id"])
    if not player.get("clan_id"):
        return jsonify({"error": "Not in a clan"}), 400
    if player.get("clan_role") == "leader":
        members = m.get_clan_members(player["clan_id"])
        if len(members) > 1:
            return jsonify({"error": "Transfer leadership before leaving"}), 400
        m.disband_clan(player["clan_id"])
        return jsonify({"ok": True})
    m.leave_clan(session["player_id"])
    return jsonify({"ok": True})


@clan_bp.route("/api/clan/<int:clan_id>/description", methods=["POST"])
@login_required
def api_set_description(clan_id: int):
    player = m.get_player_by_id(session["player_id"])
    if player.get("clan_id") != clan_id:
        return jsonify({"error": "Forbidden"}), 403
    if player.get("clan_role") not in ("leader", "co-leader"):
        return jsonify({"error": "Only leader or co-leader can change description"}), 403
    data = request.get_json(force=True, silent=True) or {}
    desc = data.get("description", "").strip()[:500]
    m.set_clan_description(clan_id, desc)
    return jsonify({"ok": True})


# ── API: Member management ───────────────────────────────────────────── #

@clan_bp.route("/api/clan/<int:clan_id>/set_role", methods=["POST"])
@login_required
def api_set_role(clan_id: int):
    actor = m.get_player_by_id(session["player_id"])
    if actor.get("clan_id") != clan_id:
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(force=True, silent=True) or {}
    target_id = int(data.get("player_id", 0))
    new_role = data.get("role", "").strip()
    if new_role not in ("leader", "co-leader", "elder", "member"):
        return jsonify({"error": "Invalid role"}), 400
    if target_id == session["player_id"]:
        return jsonify({"error": "Cannot change your own role"}), 400
    target = m.get_player_by_id(target_id)
    if not target or target.get("clan_id") != clan_id:
        return jsonify({"error": "Player not in clan"}), 404
    if not _can_manage(actor.get("clan_role"), target.get("clan_role")):
        return jsonify({"error": "You don't have permission to manage this member"}), 403
    if actor.get("clan_role") == "co-leader" and new_role in ("co-leader", "leader"):
        return jsonify({"error": "Co-leaders cannot assign that rank"}), 403
    m.set_clan_member_role(clan_id, target_id, new_role)
    return jsonify({"ok": True})


@clan_bp.route("/api/clan/<int:clan_id>/kick", methods=["POST"])
@login_required
def api_kick(clan_id: int):
    actor = m.get_player_by_id(session["player_id"])
    if actor.get("clan_id") != clan_id:
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(force=True, silent=True) or {}
    target_id = int(data.get("player_id", 0))
    if target_id == session["player_id"]:
        return jsonify({"error": "Use leave instead"}), 400
    target = m.get_player_by_id(target_id)
    if not target or target.get("clan_id") != clan_id:
        return jsonify({"error": "Player not in clan"}), 404
    if not _can_manage(actor.get("clan_role"), target.get("clan_role")):
        return jsonify({"error": "No permission to kick this member"}), 403
    m.remove_clan_member(clan_id, target_id)
    return jsonify({"ok": True})


# ── API: Applications ────────────────────────────────────────────────── #

@clan_bp.route("/api/clan/<int:clan_id>/apply", methods=["POST"])
@login_required
def api_apply(clan_id: int):
    player = m.get_player_by_id(session["player_id"])
    if player.get("clan_id"):
        return jsonify({"error": "Leave your current clan first"}), 409
    if not m.get_clan(clan_id):
        return jsonify({"error": "Clan not found"}), 404
    ok, err = m.apply_to_clan(clan_id, session["player_id"])
    if not ok:
        return jsonify({"error": err}), 409
    return jsonify({"ok": True})


@clan_bp.route("/api/clan/<int:clan_id>/application/<int:app_id>/resolve", methods=["POST"])
@login_required
def api_resolve_application(clan_id: int, app_id: int):
    actor = m.get_player_by_id(session["player_id"])
    if actor.get("clan_id") != clan_id:
        return jsonify({"error": "Forbidden"}), 403
    if not _can_accept_applications(actor.get("clan_role")):
        return jsonify({"error": "Only elders and above can resolve applications"}), 403
    data = request.get_json(force=True, silent=True) or {}
    accept = bool(data.get("accept", False))
    ok, err = m.resolve_application(app_id, session["player_id"], accept)
    if not ok:
        return jsonify({"error": err}), 400
    return jsonify({"ok": True})


# ── API: Recruitment DM ───────────────────────────────────────────────── #

@clan_bp.route("/api/clan/<int:clan_id>/recruit", methods=["POST"])
@login_required
def api_recruit(clan_id: int):
    actor = m.get_player_by_id(session["player_id"])
    if actor.get("clan_id") != clan_id:
        return jsonify({"error": "Forbidden"}), 403
    if actor.get("clan_role") == "member":
        return jsonify({"error": "Members cannot send recruitment messages"}), 403
    data = request.get_json(force=True, silent=True) or {}
    target_id = int(data.get("player_id", 0))
    message = data.get("message", "").strip()[:_MAX_MESSAGE_LEN]
    if not message:
        return jsonify({"error": "Message required"}), 400
    if target_id == session["player_id"]:
        return jsonify({"error": "Cannot recruit yourself"}), 400
    target = m.get_player_by_id(target_id)
    if not target:
        return jsonify({"error": "Player not found"}), 404
    m.send_recruit_dm(session["player_id"], target_id, clan_id, message)
    return jsonify({"ok": True})


@clan_bp.route("/api/clan/recruit/respond", methods=["POST"])
@login_required
def api_recruit_respond():
    """Accept or decline a recruitment invite."""
    data = request.get_json(force=True, silent=True) or {}
    dm_id = int(data.get("dm_id", 0))
    accept = bool(data.get("accept", False))
    player = m.get_player_by_id(session["player_id"])

    from db import get_db
    db = get_db()
    row = db.execute(
        "SELECT * FROM dm_message WHERE id=? AND recipient_id=? AND is_recruit=1",
        (dm_id, session["player_id"]),
    ).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    if accept:
        if player.get("clan_id"):
            return jsonify({"error": "Leave your current clan first"}), 409
        clan_id = row["recruit_clan_id"]
        if not clan_id or not m.get_clan(clan_id):
            return jsonify({"error": "Clan no longer exists"}), 404
        db.execute(
            "UPDATE player SET clan_id=?, clan_role='member', clan_joined_at=datetime('now') WHERE id=?",
            (clan_id, session["player_id"]),
        )
    db.execute("UPDATE dm_message SET read_at=datetime('now') WHERE id=?", (dm_id,))
    db.commit()
    return jsonify({"ok": True})


# ── API: Chat ─────────────────────────────────────────────────────────── #

@clan_bp.route("/api/clan/<int:clan_id>/chat")
@login_required
def api_clan_chat(clan_id: int):
    player = m.get_player_by_id(session["player_id"])
    if player.get("clan_id") != clan_id:
        return "Forbidden", 403
    messages = m.get_clan_messages(
        clan_id, since_iso=player.get("clan_joined_at"),
    )
    return render_template("clan/chat_messages.html", messages=messages)


@clan_bp.route("/api/clan/<int:clan_id>/chat", methods=["POST"])
@login_required
def api_send_message(clan_id: int):
    player = m.get_player_by_id(session["player_id"])
    if player.get("clan_id") != clan_id:
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(force=True, silent=True) or {}
    msg = data.get("message", "").strip()[:_MAX_MESSAGE_LEN]
    if not msg:
        return jsonify({"error": "Empty message"}), 400
    m.add_clan_message(clan_id, session["player_id"], msg)
    return jsonify({"ok": True})


# ── API: Pending applications partial (HTMX poll) ────────────────────── #

@clan_bp.route("/api/clan/<int:clan_id>/applications")
@login_required
def api_applications(clan_id: int):
    player = m.get_player_by_id(session["player_id"])
    if player.get("clan_id") != clan_id:
        return "Forbidden", 403
    if not _can_accept_applications(player.get("clan_role")):
        return "", 200
    applications = m.get_pending_applications(clan_id)
    return render_template(
        "clan/applications_partial.html",
        applications=applications, clan_id=clan_id, player=player,
    )

