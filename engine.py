from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from ai import MediumAIBot
from deck import deal_cards, init_deck, shuffle_deck
from models import GamePhase, GameState, Role, RuleConfig, Team, VictoryConfig
from players import AIPlayer, HumanPlayer
from rules import identify_play, is_legal_play, sort_hand


@dataclass
class JudgeResult:
    winner_team: Team
    finish_order: list[int]
    role_mapping: dict[int, Role]
    explanation: str


def judge_result(finish_order: list[int], roles: dict[int, Role], teams: dict[int, Team], config: VictoryConfig) -> JudgeResult:
    first = finish_order[0]
    emperor_side = [pid for pid, t in teams.items() if t == Team.EMPEROR_SIDE]
    if len(emperor_side) == 1:
        winner = Team.EMPEROR_SIDE if first == emperor_side[0] else Team.COMMONER_SIDE
        exp = "独保默认规则：独保玩家必须第一。"
        return JudgeResult(winner, finish_order, roles, exp)
    if teams[first] == Team.EMPEROR_SIDE:
        mate = [p for p in emperor_side if p != first][0]
        mate_rank = finish_order.index(mate) + 1
        if mate_rank <= config.emperor_side_win_if_any_first_and_teammate_top_n:
            return JudgeResult(Team.EMPEROR_SIDE, finish_order, roles, f"皇帝方一人第一且队友前{config.emperor_side_win_if_any_first_and_teammate_top_n}。")
    return JudgeResult(Team.COMMONER_SIDE, finish_order, roles, "默认规则下平民方胜。")


class GameEngine:
    def __init__(self, rule_config: RuleConfig, victory_config: VictoryConfig, seed: Optional[int] = None, debug: bool = False):
        self.rule_config = rule_config
        self.victory_config = victory_config
        self.rnd = random.Random(seed)
        self.debug = debug

    def create_default_players(self) -> list:
        players = [HumanPlayer(0, "You")]
        for i in range(1, 5):
            players.append(AIPlayer(i, f"AI-{i}", MediumAIBot(), self.rnd))
        return players

    def setup_game(self, players: list) -> GameState:
        while True:
            state = GameState(players=players)
            deck = init_deck(self.rule_config)
            shuffle_deck(deck, self.rnd)
            hands = deal_cards(deck, [p.player_id for p in players])
            state.hands = {pid: sort_hand(h, self.rule_config) for pid, h in hands.items()}
            state.phase = GamePhase.IDENTIFY
            emperor = guard = None
            for pid, hand in state.hands.items():
                if any(c.is_emperor_token for c in hand):
                    emperor = pid
                if any(c.is_guard_token for c in hand):
                    guard = pid
            if emperor is None or guard is None:
                raise RuntimeError("无法识别皇/保牌")
            if emperor == guard and not self.rule_config.allow_du_bao:
                if self.rule_config.redeal_on_conflict_if_no_du_bao:
                    continue
                raise RuntimeError("禁独保且同人持双牌")
            state.emperor_id, state.guard_id = emperor, guard
            for p in players:
                if p.player_id == emperor:
                    state.roles[p.player_id] = Role.EMPEROR
                    state.teams[p.player_id] = Team.EMPEROR_SIDE
                elif p.player_id == guard:
                    state.roles[p.player_id] = Role.GUARD
                    state.teams[p.player_id] = Team.EMPEROR_SIDE
                else:
                    state.roles[p.player_id] = Role.COMMONER
                    state.teams[p.player_id] = Team.COMMONER_SIDE
            state.current_turn_index = next(i for i, p in enumerate(players) if p.player_id == emperor)
            state.phase = GamePhase.PLAYING
            if self.rule_config.guard_visibility == "open":
                state.revealed_guard = True
            return state

    def _next_active_turn(self, state: GameState) -> None:
        n = len(state.players)
        for _ in range(n):
            state.current_turn_index = (state.current_turn_index + 1) % n
            pid = state.players[state.current_turn_index].player_id
            if pid not in state.finish_order:
                return

    def _apply_pass(self, state: GameState, pid: int):
        if state.last_play is None:
            raise ValueError("当前无牌可压，不能pass")
        state.passes_in_row += 1
        state.logs.append(f"P{pid} pass")
        active_remaining = len([p for p in state.players if p.player_id not in state.finish_order])
        threshold = max(0, active_remaining - 1)
        if state.passes_in_row >= threshold:
            leader = state.last_play_player_id
            state.logs.append(f"清台，P{leader}重新领出")
            state.last_play = None
            state.passes_in_row = 0
            if leader is not None and leader not in state.finish_order:
                state.current_turn_index = next(i for i, p in enumerate(state.players) if p.player_id == leader)

    def _remove_cards(self, hand, selected):
        sel_ids = {c.card_id for c in selected}
        return [c for c in hand if c.card_id not in sel_ids]

    def run(self, state: GameState) -> JudgeResult:
        while len(state.finish_order) < len(state.players):
            state.turn_count += 1
            if state.turn_count > self.rule_config.max_turns_guard:
                raise RuntimeError("触发安全回合上限，可能存在死循环")
            player = state.players[state.current_turn_index]
            pid = player.player_id
            if pid in state.finish_order:
                self._next_active_turn(state)
                continue
            action, indexes, reason = player.take_turn(state, self.rule_config)
            hand_sorted = sort_hand(state.hands[pid], self.rule_config)

            if action == "quit":
                state.stop_requested = True
                break
            if action == "hint" and isinstance(player, HumanPlayer):
                dec = MediumAIBot().choose_play(pid, hand_sorted, state, self.rule_config, self.rnd)
                print(f"提示: {'pass' if dec.play is None else dec.play.brief()} ({dec.reason})")
                continue
            if action == "pass":
                try:
                    self._apply_pass(state, pid)
                except ValueError as exc:
                    if isinstance(player, HumanPlayer):
                        print(str(exc))
                        continue
                    raise
                self._next_active_turn(state)
                continue
            if action != "play" or indexes is None:
                if isinstance(player, HumanPlayer):
                    print("非法操作")
                    continue
                raise RuntimeError("AI 非法行为")
            selected = [hand_sorted[i] for i in indexes]
            play = identify_play(selected, self.rule_config)
            if play is None:
                if isinstance(player, HumanPlayer):
                    print("牌型不合法")
                    continue
                # AI兜底：若领出阶段不允许pass，则强制打最小单张
                if state.last_play is None:
                    selected = [hand_sorted[0]]
                    play = identify_play(selected, self.rule_config)
                else:
                    state.logs.append(f"P{pid} attempted illegal play -> pass")
                    self._apply_pass(state, pid)
                    self._next_active_turn(state)
                    continue
            ok, msg = is_legal_play(hand_sorted, play, state.last_play, self.rule_config)
            if not ok:
                if isinstance(player, HumanPlayer):
                    print(f"出牌失败: {msg}")
                    continue
                if state.last_play is None:
                    selected = [c for c in hand_sorted if c.rank != "3"][:1] or [hand_sorted[0]]
                    play = identify_play(selected, self.rule_config)
                    ok, msg = is_legal_play(hand_sorted, play, state.last_play, self.rule_config)
                if not ok:
                    state.logs.append(f"P{pid} illegal ({msg}) -> pass")
                    self._apply_pass(state, pid)
                    self._next_active_turn(state)
                    continue
            state.hands[pid] = self._remove_cards(state.hands[pid], selected)
            state.last_play = play
            state.last_play_player_id = pid
            if state.trick_leader_player_id is None or state.passes_in_row == 0:
                state.trick_leader_player_id = pid
            state.passes_in_row = 0
            state.logs.append(f"P{pid} play {play.brief()} {reason}")
            if not state.hands[pid]:
                state.finish_order.append(pid)
                state.logs.append(f"P{pid} 出完，名次#{len(state.finish_order)}")
                if state.last_play_player_id == pid:
                    state.last_play = None
                    state.last_play_player_id = None
                    state.passes_in_row = 0
            self._next_active_turn(state)

        state.phase = GamePhase.FINISHED
        if self.rule_config.guard_visibility == "hidden":
            state.revealed_guard = True
        if state.stop_requested:
            return JudgeResult(Team.COMMONER_SIDE, state.finish_order, state.roles, "玩家提前退出，结果无效")
        return judge_result(state.finish_order, state.roles, state.teams, self.victory_config)
