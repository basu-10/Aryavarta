"""
blueprints/clan_bp.py — Clan/alliance creation, joining, and chat.
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


@clan_bp.route("/clan")
@login_required
def clan_page():
    player = m.get_player_by_id(session["player_id"])
    if player.get("clan_id"):
        clan    = m.get_clan(player["clan_id"])
        members = m.get_clan_members(player["clan_id"])
        messages = m.get_clan_messages(player["clan_id"])
    else:
        clan = members = messages = None
    all_clans = m.get_all_clans()
    return render_template(
        "clan/clan.html",
        player=player, clan=clan, members=members,
        messages=messages, all_clans=all_clans,
    )


@clan_bp.route("/api/clan/create", methods=["POST"])
@login_required
def api_create_clan():
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Clan name required"}), 400
    player = m.get_player_by_id(session["player_id"])
    if player.get("clan_id"):
        return jsonify({"error": "You are already in a clan"}), 409
    if m.get_clan_by_name(name):
        return jsonify({"error": "Clan name taken"}), 409
    clan_id = m.create_clan(name, session["player_id"])
    return jsonify({"ok": True, "clan_id": clan_id})


@clan_bp.route("/api/clan/join", methods=["POST"])
@login_required
def api_join_clan():
    data = request.get_json(force=True, silent=True) or {}
    clan_id = int(data.get("clan_id", 0))
    player = m.get_player_by_id(session["player_id"])
    if player.get("clan_id"):
        return jsonify({"error": "Already in a clan. Leave first."}), 409
    if not m.get_clan(clan_id):
        return jsonify({"error": "Clan not found"}), 404
    m.set_player_clan(session["player_id"], clan_id)
    return jsonify({"ok": True})


@clan_bp.route("/api/clan/leave", methods=["POST"])
@login_required
def api_leave_clan():
    player = m.get_player_by_id(session["player_id"])
    if not player.get("clan_id"):
        return jsonify({"error": "Not in a clan"}), 400
    m.set_player_clan(session["player_id"], None)
    return jsonify({"ok": True})


@clan_bp.route("/api/clan/<int:clan_id>/chat")
@login_required
def api_clan_chat(clan_id: int):
    """HTMX-polled endpoint — returns chat messages as an HTML partial."""
    player = m.get_player_by_id(session["player_id"])
    if player.get("clan_id") != clan_id:
        return "Forbidden", 403
    messages = m.get_clan_messages(clan_id)
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
