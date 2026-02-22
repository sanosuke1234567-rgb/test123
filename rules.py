from __future__ import annotations

from collections import Counter
from typing import Optional

from models import Card, Play, PlayType, RuleConfig


class RuleError(ValueError):
    pass


def build_rank_value_map(config: RuleConfig) -> dict[str, int]:
    return {r: i for i, r in enumerate(config.rank_order)}


def effective_rank(card: Card) -> str:
    if card.is_emperor_token:
        return "EMPEROR_TOKEN"
    if card.is_guard_token:
        return "GUARD_TOKEN"
    return card.rank


def sort_hand(hand: list[Card], config: RuleConfig) -> list[Card]:
    order = build_rank_value_map(config)
    suit_order = {"♠": 0, "♥": 1, "♣": 2, "♦": 3, "JOKER": 4}
    return sorted(hand, key=lambda c: (order[effective_rank(c)], suit_order.get(c.suit.value, 9), c.card_id))


def identify_play(cards: list[Card], config: RuleConfig) -> Optional[Play]:
    if not cards:
        return None
    ranks = [effective_rank(c) for c in cards]
    counter = Counter(ranks)
    if len(counter) != 1:
        return None
    main_rank = next(iter(counter))
    n = len(cards)
    if n == 1:
        ptype = PlayType.SINGLE
    elif n == 2:
        ptype = PlayType.PAIR
    elif n == 3:
        ptype = PlayType.TRIPLE
    elif n >= 4:
        ptype = PlayType.SET
    else:
        return None
    return Play(type=ptype, main_rank=main_rank, count=n, cards=cards)


def can_beat(last_play: Play, new_play: Play, config: RuleConfig) -> bool:
    if last_play.type != new_play.type or last_play.count != new_play.count:
        return False
    rv = build_rank_value_map(config)
    return rv[new_play.main_rank] > rv[last_play.main_rank]


def violates_three_must_be_last(hand: list[Card], play: Play, config: RuleConfig, is_lead: bool) -> bool:
    if not (config.three_must_be_last and is_lead):
        return False
    if play.main_rank != "3":
        return False
    for c in hand:
        if effective_rank(c) != "3":
            return True
    return False


def is_legal_play(hand: list[Card], play: Play, last_play: Optional[Play], config: RuleConfig) -> tuple[bool, str]:
    hand_ids = {c.card_id for c in hand}
    for c in play.cards:
        if c.card_id not in hand_ids:
            return False, "出的牌不在手牌中"
    identified = identify_play(play.cards, config)
    if identified is None:
        return False, "牌型不合法，仅支持 single/pair/triple/set"
    is_lead = last_play is None
    if violates_three_must_be_last(hand, identified, config, is_lead):
        return False, "规则限制：手里还有非3，不能主动出3"
    if last_play is not None and not can_beat(last_play, identified, config):
        return False, "无法压牌：需要同牌型同张数且主点数更大"
    return True, "ok"


def parse_player_input_to_indexes(raw: str) -> tuple[str, list[int]]:
    data = raw.strip()
    if not data:
        return "", []
    cmd = data.split()[0].lower()
    if cmd == "play":
        tail = data[4:].strip().replace(",", " ")
        if not tail:
            raise RuleError("play 命令后需要索引")
        try:
            idxs = [int(x) for x in tail.split()]
        except ValueError as exc:
            raise RuleError("索引必须是整数") from exc
        return "play", idxs
    return cmd, []


def parse_player_input_to_play(raw: str, sorted_hand: list[Card], config: RuleConfig) -> tuple[str, Optional[Play], str]:
    """Parse raw CLI text into action and play object.

    Returns (action, play, message). action in {play, pass, hint, hand, help, log, quit}.
    """
    cmd, idxs = parse_player_input_to_indexes(raw)
    if cmd != "play":
        return cmd, None, ""
    if len(set(idxs)) != len(idxs):
        return "error", None, "索引重复"
    if any(i < 0 or i >= len(sorted_hand) for i in idxs):
        return "error", None, "索引越界"
    selected = [sorted_hand[i] for i in idxs]
    play = identify_play(selected, config)
    if play is None:
        return "error", None, "牌型不合法"
    return "play", play, ""
