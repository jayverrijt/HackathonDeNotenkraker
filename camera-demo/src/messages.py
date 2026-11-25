"""Natural-language phrasing for spoken alerts."""

from __future__ import annotations


def indefinite_article(noun: str) -> str:
    word = (noun or "").strip().lower()
    if not word:
        return "a"
    if word.startswith(("hour", "honest", "honor")):
        return "an"
    if word.startswith(("uni", "use", "user", "usual", "eu", "one", "once")):
        return "a"
    return "an" if word[0] in "aeiou" else "a"


def object_phrase(name: str) -> str:
    return f"{indefinite_article(name)} {name}"


def direction_phrase(position: str, lower: bool, close: bool = False) -> str:
    if close:
        if position == "left":
            return "close on your left"
        if position == "right":
            return "close on your right"
        return "close in front of you"

    if position == "left":
        return "to your left"
    if position == "right":
        return "to your right"
    return "in front of you" if lower else "ahead"


def there_is_object(
    name: str,
    position: str,
    lower: bool,
    close: bool = False,
    uncertain: bool = False,
) -> str:
    lead = "There may be" if uncertain else "There is"
    return (
        f"{lead} {object_phrase(name)} "
        f"{direction_phrase(position, lower, close)}."
    )


def there_are_people(
    count: int,
    position: str,
    lower: bool,
    close: bool = False,
) -> str:
    direction = direction_phrase(position, lower, close)
    if count >= 3:
        return f"There are several people {direction}."
    if count == 2:
        return f"There are two people {direction}."
    return f"There is a person {direction}."


def curb_message(zone: str) -> str:
    if zone == "left":
        return "There may be a curb on your left."
    if zone == "right":
        return "There may be a curb on your right."
    if zone == "ahead":
        return "There may be a curb or road edge ahead."
    return "There may be a curb nearby."


def scene_message(name: str, position: str) -> str:
    if name == "vegetation":
        return (
            "There are trees or plants "
            f"{direction_phrase(position, lower=True)}."
        )
    if name in {"building", "wall", "fence"}:
        return (
            f"There is {object_phrase(name)} "
            f"{direction_phrase(position, lower=True)}."
        )
    return there_is_object(name, position, lower=True)
