from __future__ import annotations

import random

from ai import MediumAIBot
from deck import deal_cards, init_deck
from engine import GameEngine, judge_result
from models import GameState, Play, PlayType, Role, RuleConfig, Team, VictoryConfig
from rules import can_beat, identify_play, is_legal_play


def default_config() -> RuleConfig:
    return RuleConfig(
        rank_order=["3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2", "SJ", "BJ", "GUARD_TOKEN", "EMPEROR_TOKEN"],
        allow_du_bao=True,
    )


def test_deal_counts():
    deck = init_deck(default_config())
    assert len(deck) == 216
    hands = deal_cards(deck, [0, 1, 2, 3, 4])
    counts = sorted(len(v) for v in hands.values())
    assert sum(counts) == 216
    assert counts == [43, 43, 43, 43, 44]


def test_role_identification_du_bao_allowed():
    cfg = default_config()
    engine = GameEngine(cfg, VictoryConfig(), seed=7)
    state = engine.setup_game(engine.create_default_players())
    assert state.roles[state.emperor_id] == Role.EMPEROR
    assert state.roles[state.guard_id] in (Role.GUARD, Role.EMPEROR)


def test_identify_play_types_and_invalid():
    cfg = default_config()
    deck = init_deck(cfg)
    c1 = [c for c in deck if c.rank == "9"][0]
    c2 = [c for c in deck if c.rank == "9"][1]
    c3 = [c for c in deck if c.rank == "9"][2]
    c4 = [c for c in deck if c.rank == "9"][3]
    c5 = [c for c in deck if c.rank == "10"][0]
    assert identify_play([c1], cfg).type == PlayType.SINGLE
    assert identify_play([c1, c2], cfg).type == PlayType.PAIR
    assert identify_play([c1, c2, c3], cfg).type == PlayType.TRIPLE
    assert identify_play([c1, c2, c3, c4], cfg).type == PlayType.SET
    assert identify_play([c1, c5], cfg) is None


def test_can_beat_rules():
    cfg = default_config()
    l = Play(PlayType.TRIPLE, "8", 3, [])
    n = Play(PlayType.TRIPLE, "9", 3, [])
    bad_type = Play(PlayType.PAIR, "9", 2, [])
    same = Play(PlayType.TRIPLE, "8", 3, [])
    assert can_beat(l, n, cfg)
    assert not can_beat(l, bad_type, cfg)
    assert not can_beat(l, same, cfg)


def test_three_must_be_last():
    cfg = default_config()
    cfg.three_must_be_last = True
    deck = init_deck(cfg)
    c3 = [c for c in deck if c.rank == "3"][:2]
    c4 = [c for c in deck if c.rank == "4"][:1]
    play3 = identify_play(c3[:1], cfg)
    ok, _ = is_legal_play(c3 + c4, play3, None, cfg)
    assert not ok
    ok2, _ = is_legal_play(c3, play3, None, cfg)
    assert ok2


def test_clear_table_after_passes():
    cfg = default_config()
    engine = GameEngine(cfg, VictoryConfig(), seed=1)
    state = engine.setup_game(engine.create_default_players())
    state.last_play = Play(PlayType.SINGLE, "9", 1, [])
    state.last_play_player_id = 1
    state.finish_order = []
    state.passes_in_row = 0
    engine._apply_pass(state, 2)
    engine._apply_pass(state, 3)
    engine._apply_pass(state, 4)
    engine._apply_pass(state, 0)
    assert state.last_play is None


def test_judge_result():
    roles = {0: Role.EMPEROR, 1: Role.GUARD, 2: Role.COMMONER, 3: Role.COMMONER, 4: Role.COMMONER}
    teams = {0: Team.EMPEROR_SIDE, 1: Team.EMPEROR_SIDE, 2: Team.COMMONER_SIDE, 3: Team.COMMONER_SIDE, 4: Team.COMMONER_SIDE}
    res = judge_result([0, 2, 1, 3, 4], roles, teams, VictoryConfig(3))
    assert res.winner_team == Team.EMPEROR_SIDE
    res2 = judge_result([2, 0, 1, 3, 4], roles, teams, VictoryConfig(3))
    assert res2.winner_team == Team.COMMONER_SIDE


def test_ai_decision_basic_validity():
    cfg = default_config()
    deck = init_deck(cfg)
    hand = [c for c in deck if c.rank in {"7", "8", "9"}][:8]
    state = GameState(players=[])
    state.hands = {1: hand.copy(), 2: []}
    state.teams = {1: Team.COMMONER_SIDE, 2: Team.EMPEROR_SIDE}
    state.last_play = Play(PlayType.SET, "Q", 5, [])
    state.last_play_player_id = 2
    bot = MediumAIBot()
    dec = bot.choose_play(1, hand, state, cfg, random.Random(0))
    assert dec.play is None

    state.last_play = None
    dec2 = bot.choose_play(1, hand, state, cfg, random.Random(1))
    assert dec2.play is not None
    assert all(c in hand for c in dec2.play.cards)
    assert identify_play(dec2.play.cards, cfg) is not None
