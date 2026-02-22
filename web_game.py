from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from ai import MediumAIBot
from deck import deal_cards, init_deck, shuffle_deck
from engine import JudgeResult, judge_result
from models import GamePhase, GameState, Role, RuleConfig, Team, VictoryConfig
from players import AIPlayer
from rules import identify_play, is_legal_play, sort_hand


@dataclass
class WebActionResult:
    ok: bool
    message: str


class WebGame:
    """Stateful web-friendly BaoHuang game wrapper.

    Human player is always player_id=0. AI players are 1~4.
    """

    def __init__(self, rule_config: RuleConfig, victory_config: VictoryConfig, seed: Optional[int] = None):
        self.rule_config = rule_config
        self.victory_config = victory_config
        self.rnd = random.Random(seed)
        self.state: Optional[GameState] = None
        self.result: Optional[JudgeResult] = None

    def _build_players(self):
        return [AIPlayer(i, f"AI-{i}", MediumAIBot(), self.rnd) for i in range(1, 5)]

    def new_game(self) -> None:
        ai_players = self._build_players()
        players = []
        # dummy for id 0 human in web
        class _Human:
            def __init__(self):
                self.player_id = 0
                self.name = "You"

        players.append(_Human())
        players.extend(ai_players)

        while True:
            state = GameState(players=players)
            deck = init_deck(self.rule_config)
            shuffle_deck(deck, self.rnd)
            hands = deal_cards(deck, [0, 1, 2, 3, 4])
            state.hands = {pid: sort_hand(hand, self.rule_config) for pid, hand in hands.items()}
            emperor = guard = None
            for pid, hand in state.hands.items():
                if any(c.is_emperor_token for c in hand):
                    emperor = pid
                if any(c.is_guard_token for c in hand):
                    guard = pid
            if emperor is None or guard is None:
                raise RuntimeError("missing token card")
            if emperor == guard and (not self.rule_config.allow_du_bao) and self.rule_config.redeal_on_conflict_if_no_du_bao:
                continue
            state.emperor_id = emperor
            state.guard_id = guard
            for pid in [0, 1, 2, 3, 4]:
                if pid == emperor:
                    state.roles[pid] = Role.EMPEROR
                    state.teams[pid] = Team.EMPEROR_SIDE
                elif pid == guard:
                    state.roles[pid] = Role.GUARD
                    state.teams[pid] = Team.EMPEROR_SIDE
                else:
                    state.roles[pid] = Role.COMMONER
                    state.teams[pid] = Team.COMMONER_SIDE
            state.current_turn_index = emperor
            state.phase = GamePhase.PLAYING
            state.revealed_guard = self.rule_config.guard_visibility == "open"
            self.state = state
            self.result = None
            break
        self._run_ai_until_human_turn()

    def _next_active_turn(self) -> None:
        assert self.state is not None
        state = self.state
        for _ in range(5):
            state.current_turn_index = (state.current_turn_index + 1) % 5
            if state.current_turn_index not in state.finish_order:
                return

    def _clear_table_if_needed(self) -> None:
        assert self.state is not None
        state = self.state
        active = [pid for pid in range(5) if pid not in state.finish_order]
        if state.passes_in_row >= max(0, len(active) - 1):
            leader = state.last_play_player_id
            state.logs.append(f"清台，P{leader}重新领出")
            state.last_play = None
            state.passes_in_row = 0
            if leader is not None and leader not in state.finish_order:
                state.current_turn_index = leader

    def _finish_if_needed(self) -> bool:
        assert self.state is not None
        state = self.state
        if len(state.finish_order) == 5:
            state.phase = GamePhase.FINISHED
            if self.rule_config.guard_visibility == "hidden":
                state.revealed_guard = True
            self.result = judge_result(state.finish_order, state.roles, state.teams, self.victory_config)
            return True
        return False

    def _run_ai_until_human_turn(self) -> None:
        assert self.state is not None
        state = self.state
        guard = 0
        while state.phase == GamePhase.PLAYING and state.current_turn_index != 0:
            guard += 1
            if guard > self.rule_config.max_turns_guard:
                raise RuntimeError("AI loop overflow")
            pid = state.current_turn_index
            if pid in state.finish_order:
                self._next_active_turn()
                continue
            ai_player = state.players[pid]
            action, indexes, reason = ai_player.take_turn(state, self.rule_config)
            hand = sort_hand(state.hands[pid], self.rule_config)
            if action == "pass":
                if state.last_play is None:
                    # AI fallback: lead minimal legal card
                    indexes = [0]
                    action = "play"
                else:
                    state.passes_in_row += 1
                    state.logs.append(f"P{pid} pass {reason}".strip())
                    self._clear_table_if_needed()
                    self._next_active_turn()
                    continue

            selected = [hand[i] for i in (indexes or [])]
            play = identify_play(selected, self.rule_config)
            if play is None:
                selected = [hand[0]]
                play = identify_play(selected, self.rule_config)
            ok, msg = is_legal_play(hand, play, state.last_play, self.rule_config)
            if not ok:
                if state.last_play is None:
                    selected = [c for c in hand if c.rank != "3"][:1] or [hand[0]]
                    play = identify_play(selected, self.rule_config)
                    ok, _ = is_legal_play(hand, play, state.last_play, self.rule_config)
                if not ok:
                    state.passes_in_row += 1
                    state.logs.append(f"P{pid} pass(illegal:{msg})")
                    self._clear_table_if_needed()
                    self._next_active_turn()
                    continue

            sel_ids = {c.card_id for c in selected}
            state.hands[pid] = [c for c in state.hands[pid] if c.card_id not in sel_ids]
            state.last_play = play
            state.last_play_player_id = pid
            state.trick_leader_player_id = pid
            state.passes_in_row = 0
            state.logs.append(f"P{pid} play {play.brief()} {reason}".strip())
            if not state.hands[pid]:
                state.finish_order.append(pid)
                state.logs.append(f"P{pid} 出完，名次#{len(state.finish_order)}")
                if state.last_play_player_id == pid:
                    state.last_play = None
                    state.last_play_player_id = None
            if self._finish_if_needed():
                return
            self._next_active_turn()

    def human_action(self, action: str, indexes: Optional[list[int]] = None) -> WebActionResult:
        if self.state is None:
            return WebActionResult(False, "游戏未初始化")
        state = self.state
        if state.phase != GamePhase.PLAYING:
            return WebActionResult(False, "对局已结束")
        if state.current_turn_index != 0:
            return WebActionResult(False, "尚未轮到你")

        hand = sort_hand(state.hands[0], self.rule_config)
        if action == "pass":
            if state.last_play is None:
                return WebActionResult(False, "无待压牌时不能过")
            state.passes_in_row += 1
            state.logs.append("P0 pass")
            self._clear_table_if_needed()
            self._next_active_turn()
            self._run_ai_until_human_turn()
            self._finish_if_needed()
            return WebActionResult(True, "你选择了过牌")

        if action != "play":
            return WebActionResult(False, "未知动作")
        if not indexes:
            return WebActionResult(False, "请至少选择一张牌")
        if len(set(indexes)) != len(indexes):
            return WebActionResult(False, "索引重复")
        if any(i < 0 or i >= len(hand) for i in indexes):
            return WebActionResult(False, "索引越界")

        selected = [hand[i] for i in indexes]
        play = identify_play(selected, self.rule_config)
        if play is None:
            return WebActionResult(False, "牌型不合法")
        ok, msg = is_legal_play(hand, play, state.last_play, self.rule_config)
        if not ok:
            return WebActionResult(False, msg)

        sel_ids = {c.card_id for c in selected}
        state.hands[0] = [c for c in state.hands[0] if c.card_id not in sel_ids]
        state.last_play = play
        state.last_play_player_id = 0
        state.trick_leader_player_id = 0
        state.passes_in_row = 0
        state.logs.append(f"P0 play {play.brief()}")
        if not state.hands[0]:
            state.finish_order.append(0)
            state.logs.append(f"P0 出完，名次#{len(state.finish_order)}")
            state.last_play = None
            state.last_play_player_id = None
        if self._finish_if_needed():
            return WebActionResult(True, "出牌成功，对局结束")
        self._next_active_turn()
        self._run_ai_until_human_turn()
        self._finish_if_needed()
        return WebActionResult(True, "出牌成功")

    def view_model(self) -> dict:
        if self.state is None:
            return {"started": False}
        s = self.state
        hand = sort_hand(s.hands[0], self.rule_config)
        return {
            "started": True,
            "phase": s.phase.value,
            "emperor": s.emperor_id,
            "guard": s.guard_id if s.revealed_guard else "隐藏",
            "my_role": s.roles.get(0).value if s.phase == GamePhase.FINISHED else "未知",
            "my_hand": [f"[{i}] {c.short()}" for i, c in enumerate(hand)],
            "my_hand_count": len(hand),
            "last_play": s.last_play.brief() if s.last_play else "无",
            "leader": s.last_play_player_id,
            "turn": s.current_turn_index,
            "finish_order": s.finish_order,
            "logs": s.logs[-25:],
            "result": None if self.result is None else {
                "winner": self.result.winner_team.value,
                "explanation": self.result.explanation,
                "finish_order": self.result.finish_order,
                "roles": {str(k): v.value for k, v in s.roles.items()},
            },
            "ai_hand_counts": {pid: len(s.hands[pid]) for pid in [1, 2, 3, 4]},
        }
