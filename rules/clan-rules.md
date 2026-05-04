# Clan Rules

## Creating a clan

- Any player not already in a clan can found one.
- Cost: **1000 food + 1000 timber + 1000 gold + 1000 metal**.
- The founder becomes the **Leader** automatically.

---

## Role hierarchy

```
Leader  >  Co-leader  >  Elder  >  Member
```

All new joiners start as **Member** regardless of how they joined.

### What each role can do

| Role | Promote / Demote | Accept applications | Send recruit DMs | Set description | Kick members | Disband |
|---|---|---|---|---|---|---|
| Leader | Anyone below Leader | Yes | Yes | Yes | Yes | Yes |
| Co-leader | Elders + Members only | Yes | Yes | No | Elders + Members | No |
| Elder | Nobody | Yes | Yes | No | No | No |
| Member | Nobody | No | No | No | No | No |

---

## Leadership transfer

- The Leader can transfer leadership to any other member.
- The old Leader is automatically demoted to **Co-leader**.

---

## Joining a clan

### Application flow
1. A player without a clan applies from any clan page.
2. An application row is created with `status = pending`.
3. Elders and above see the pending application in the Applications tab.
4. An Elder, Co-leader, or Leader accepts or rejects it.
5. Accepted players join as Member. Rejected players may re-apply.

### Recruitment DM (invite)
- Elders, Co-leaders, and Leaders can send a recruitment DM to any player from the world map.
- The recipient sees Accept / Decline buttons in their inbox.
- Accepting an invite adds the player as a Member instantly — no additional approval step.

---

## Leaving and being kicked

- A Member, Elder, or Co-leader can leave at any time.
- A Leader must transfer leadership before leaving or disband the clan.
- A kicked player's clan data (`clan_id`, `clan_role`, `clan_joined_at`) is cleared immediately.

---

## Clan chat

- Chat is polled every 3 seconds.
- A player only sees messages sent **after** the timestamp they joined the clan (`clan_joined_at`). No pre-join history is visible, ever.
- There is no message edit or delete.

---

## Disbanding

- Only the Leader can disband the clan.
- Disbanding removes all members from the clan (clears `clan_id` for every member) and deletes the clan row.
- Resources are not refunded on disband.

---

## Constraints

- A player can be in only **one** clan at a time.
- A player can have only one pending application per clan. They can apply to multiple clans simultaneously.
- Clan names must be unique across the game.
