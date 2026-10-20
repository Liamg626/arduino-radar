"""Group nearby echoes into contacts (objects) and keep their IDs stable between frames."""

from dataclasses import dataclass

ANGLE_GAP_DEG = 6        # echoes this close in angle...
DISTANCE_GAP_CM = 15     # ...and this close in range belong to the same object
MIN_HITS = 3             # fewer echoes than this is treated as noise, not a contact
RECENT_HITS = 5          # range is the median of this many newest echoes, so moving objects stay current
MATCH_ANGLE_DEG = 12     # how far a contact may move between frames and keep its ID
MATCH_DISTANCE_CM = 30


@dataclass
class Blip:
    angle: int
    distance_cm: int
    born: float


@dataclass
class Contact:
    id: int
    angle: float
    distance_cm: int
    hits: int
    last_seen: float  # birth time of its newest echo


def cluster(blips: list[Blip]) -> list[list[Blip]]:
    """Split blips into groups where each blip is near at least one other in the group."""
    ordered = sorted(blips, key=lambda b: b.angle)
    parent = list(range(len(ordered)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, a in enumerate(ordered):
        for j in range(i + 1, len(ordered)):
            b = ordered[j]
            if b.angle - a.angle > ANGLE_GAP_DEG:
                break  # sorted by angle, so nothing further along can be close either
            if abs(b.distance_cm - a.distance_cm) <= DISTANCE_GAP_CM:
                parent[find(j)] = find(i)

    groups: dict[int, list[Blip]] = {}
    for i, blip in enumerate(ordered):
        groups.setdefault(find(i), []).append(blip)
    return list(groups.values())


def _summarise(group: list[Blip]) -> Contact:
    recent = sorted(group, key=lambda b: b.born, reverse=True)[:RECENT_HITS]
    distances = sorted(b.distance_cm for b in recent)
    angles = [b.angle for b in group]
    return Contact(
        id=0,
        angle=(min(angles) + max(angles)) / 2,
        distance_cm=distances[len(distances) // 2],
        hits=len(group),
        last_seen=recent[0].born,
    )


class ContactTracker:
    def __init__(self):
        self.contacts: list[Contact] = []
        self._next_id = 1

    def update(self, blips: list[Blip]) -> list[Contact]:
        found = [_summarise(g) for g in cluster(blips) if len(g) >= MIN_HITS]

        # Biggest contacts claim their nearest previous ID first.
        unclaimed = list(self.contacts)
        for contact in sorted(found, key=lambda c: c.hits, reverse=True):
            candidates = [
                p for p in unclaimed
                if abs(p.angle - contact.angle) <= MATCH_ANGLE_DEG
                and abs(p.distance_cm - contact.distance_cm) <= MATCH_DISTANCE_CM
            ]
            match = min(
                candidates,
                key=lambda p: abs(p.angle - contact.angle) + abs(p.distance_cm - contact.distance_cm),
                default=None,
            )
            if match:
                contact.id = match.id
                unclaimed.remove(match)
            else:
                contact.id = self._next_id
                self._next_id += 1

        self.contacts = sorted(found, key=lambda c: c.id)
        return self.contacts
