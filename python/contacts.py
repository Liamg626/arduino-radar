"""Group nearby echoes into contacts (objects)."""

from dataclasses import dataclass

ANGLE_GAP_DEG = 6        # echoes this close in angle...
DISTANCE_GAP_CM = 15     # ...and this close in range belong to the same object
MIN_HITS = 3             # fewer echoes than this is treated as noise, not a contact
RECENT_HITS = 5          # range is the median of this many newest echoes, so moving objects stay current


@dataclass
class Blip:
    angle: int
    distance_cm: int
    born: float


@dataclass
class Contact:
    angle: float
    distance_cm: int
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


def find_contacts(blips: list[Blip]) -> list[Contact]:
    """One contact per group of at least MIN_HITS nearby echoes."""
    contacts = []
    for group in cluster(blips):
        if len(group) < MIN_HITS:
            continue
        recent = sorted(group, key=lambda b: b.born, reverse=True)[:RECENT_HITS]
        distances = sorted(b.distance_cm for b in recent)
        angles = [b.angle for b in group]
        contacts.append(Contact(
            angle=(min(angles) + max(angles)) / 2,
            distance_cm=distances[len(distances) // 2],
            last_seen=recent[0].born,
        ))
    return contacts
