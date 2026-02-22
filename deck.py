from __future__ import annotations

import random
from collections import defaultdict

from models import Card, RuleConfig, Suit

BASE_RANKS = ["3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2"]
SUITS = [Suit.SPADE, Suit.HEART, Suit.CLUB, Suit.DIAMOND]


def init_deck(rule_config: RuleConfig, emperor_token_card_id: str = "D1-BJ", guard_token_card_id: str = "D1-SJ") -> list[Card]:
    """Create a 4-deck BaoHuang card set with unique IDs and token flags."""
    cards: list[Card] = []
    for deck_i in range(1, 5):
        for rank in BASE_RANKS:
            for suit in SUITS:
                cid = f"D{deck_i}-{suit.name[0]}-{rank}"
                cards.append(Card(card_id=cid, deck_index=deck_i, suit=suit, rank=rank))
        cards.append(Card(card_id=f"D{deck_i}-SJ", deck_index=deck_i, suit=Suit.JOKER, rank="SJ"))
        cards.append(Card(card_id=f"D{deck_i}-BJ", deck_index=deck_i, suit=Suit.JOKER, rank="BJ"))

    remapped: list[Card] = []
    for c in cards:
        remapped.append(
            Card(
                card_id=c.card_id,
                deck_index=c.deck_index,
                suit=c.suit,
                rank=c.rank,
                is_emperor_token=c.card_id == emperor_token_card_id,
                is_guard_token=c.card_id == guard_token_card_id,
            )
        )
    return remapped


def shuffle_deck(cards: list[Card], rnd: random.Random) -> None:
    rnd.shuffle(cards)


def deal_cards(cards: list[Card], player_ids: list[int]) -> dict[int, list[Card]]:
    hands: dict[int, list[Card]] = defaultdict(list)
    for i, c in enumerate(cards):
        hands[player_ids[i % len(player_ids)]].append(c)
    return dict(hands)
