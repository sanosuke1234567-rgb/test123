from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from models import GameState, Play, RuleConfig, Team
from rules import can_beat, effective_rank, identify_play


@dataclass
class BotDecision:
    play: Optional[Play]
    reason: str


def generate_candidate_plays(hand, config: RuleConfig) -> list[Play]:
    by_rank = defaultdict(list)
    for c in hand:
        by_rank[effective_rank(c)].append(c)
    candidates: list[Play] = []
    for cards in by_rank.values():
        for k in range(1, len(cards) + 1):
            p = identify_play(cards[:k], config)
            if p:
                candidates.append(p)
    return candidates


class BaseBot:
    def choose_play(self, player_id: int, hand, state: GameState, config: RuleConfig, rnd: random.Random) -> BotDecision:
        raise NotImplementedError


class RandomBot(BaseBot):
    def choose_play(self, player_id, hand, state, config, rnd):
        cands = generate_candidate_plays(hand, config)
        if state.last_play is not None:
            cands = [c for c in cands if can_beat(state.last_play, c, config)]
            if not cands:
                return BotDecision(None, "random pass")
        return BotDecision(rnd.choice(cands), "random")


class GreedyBot(BaseBot):
    def choose_play(self, player_id, hand, state, config, rnd):
        cands = generate_candidate_plays(hand, config)
        rv = {r: i for i, r in enumerate(config.rank_order)}
        if state.last_play is None:
            cands.sort(key=lambda p: (rv[p.main_rank], -p.count))
            return BotDecision(cands[0], "lead low rank")
        beats = [c for c in cands if can_beat(state.last_play, c, config)]
        if not beats:
            return BotDecision(None, "cannot beat")
        beats.sort(key=lambda p: (rv[p.main_rank], p.count))
        return BotDecision(beats[0], "minimal beat")


class MediumAIBot(BaseBot):
    def _is_teammate(self, state: GameState, me: int, other: int) -> bool:
        return state.teams.get(me) == state.teams.get(other)

    def _high_value_penalty(self, rank: str) -> float:
        if rank in {"2", "SJ", "BJ", "GUARD_TOKEN", "EMPEROR_TOKEN"}:
            return 2.4
        return 0.0

    def _break_structure_penalty(self, hand, play: Play) -> float:
        same = [c for c in hand if effective_rank(c) == play.main_rank]
        remain = len(same) - play.count
        if len(same) >= 5 and remain > 0:
            return 2.0
        if len(same) >= 4 and play.count == 1:
            return 1.5
        return 0.0

    def _sprint_mode(self, hand) -> bool:
        return len(hand) <= 8

    def _score_lead(self, hand, play: Play, config: RuleConfig, rnd: random.Random) -> float:
        rv = {r: i for i, r in enumerate(config.rank_order)}
        score = 10.0
        score += max(0, 20 - rv[play.main_rank]) * 0.3
        score += play.count * 0.7
        score -= self._break_structure_penalty(hand, play)
        score -= self._high_value_penalty(play.main_rank)
        if self._sprint_mode(hand):
            score += play.count * 0.8
        score += rnd.uniform(-0.1, 0.1)
        return score

    def _score_response(self, player_id: int, hand, play: Play, state: GameState, config: RuleConfig, rnd: random.Random) -> float:
        rv = {r: i for i, r in enumerate(config.rank_order)}
        score = 8.0 - rv[play.main_rank] * 0.25
        score -= self._break_structure_penalty(hand, play)
        score -= self._high_value_penalty(play.main_rank)
        if state.last_play_player_id is not None and self._is_teammate(state, player_id, state.last_play_player_id):
            score -= 4.5
        else:
            if state.last_play_player_id is not None:
                enemy_cards = len(state.hands[state.last_play_player_id])
                if enemy_cards <= 5:
                    score += 3.0
        for pid, cards in state.hands.items():
            if pid != player_id and self._is_teammate(state, player_id, pid) and len(cards) <= 5:
                score -= 1.2
        if self._sprint_mode(hand):
            score += play.count * 0.6
        score += rnd.uniform(-0.15, 0.15)
        return score

    def choose_play(self, player_id, hand, state, config, rnd):
        cands = generate_candidate_plays(hand, config)
        if state.last_play is None:
            best = max(cands, key=lambda p: self._score_lead(hand, p, config, rnd))
            return BotDecision(best, "lead heuristic")
        beats = [c for c in cands if can_beat(state.last_play, c, config)]
        if not beats:
            return BotDecision(None, "no valid beat")
        scored = sorted(((self._score_response(player_id, hand, p, state, config, rnd), p) for p in beats), key=lambda x: x[0], reverse=True)
        threshold = 2.0
        if scored[0][0] < threshold:
            return BotDecision(None, "low benefit -> pass")
        return BotDecision(scored[0][1], f"response score={scored[0][0]:.2f}")
