from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from ai import BaseBot, BotDecision
from models import BasePlayer, GameState, RuleConfig
from rules import parse_player_input_to_play, sort_hand


@dataclass
class HumanPlayer(BasePlayer):
    player_id: int
    name: str

    def _show_hand(self, hand, config: RuleConfig) -> None:
        sorted_hand = sort_hand(hand, config)
        print("你的手牌:")
        print("  ".join(f"[{i}] {c.short()}" for i, c in enumerate(sorted_hand)))

    def take_turn(self, state: GameState, config: RuleConfig):
        hand = sort_hand(state.hands[self.player_id], config)
        while True:
            print(f"\n=== 轮到你: {self.name} (ID={self.player_id}) ===")
            self._show_hand(hand, config)
            print(f"桌面牌: {state.last_play.brief() if state.last_play else '无'}")
            print(f"当前领出: {state.trick_leader_player_id}")
            print(f"完成名次: {state.finish_order}")
            raw = input("输入命令(help/hint/hand/log/pass/play ...): ").strip()
            try:
                cmd, play, msg = parse_player_input_to_play(raw, hand, config)
            except Exception as exc:
                print(f"输入错误: {exc}")
                continue
            if cmd == "help":
                print("pass | play 0,4 | play 1 2 3 | hint | hand | log | quit")
                continue
            if cmd == "hand":
                continue
            if cmd == "log":
                for line in state.logs[-10:]:
                    print(line)
                continue
            if cmd == "hint":
                return "hint", None, ""
            if cmd == "quit":
                return "quit", None, ""
            if cmd == "pass":
                return "pass", None, ""
            if cmd == "error":
                print(msg)
                continue
            if cmd == "play":
                ids = [c.card_id for c in play.cards]
                id_to_pos = {c.card_id: i for i, c in enumerate(hand)}
                return "play", [id_to_pos[cid] for cid in ids], ""
            print("未知命令")


@dataclass
class AIPlayer(BasePlayer):
    player_id: int
    name: str
    bot: BaseBot
    rnd: random.Random

    def take_turn(self, state: GameState, config: RuleConfig):
        hand = state.hands[self.player_id]
        decision: BotDecision = self.bot.choose_play(self.player_id, hand, state, config, self.rnd)
        if decision.play is None:
            return "pass", None, decision.reason
        ids = [c.card_id for c in decision.play.cards]
        id_to_pos = {c.card_id: i for i, c in enumerate(sort_hand(hand, config))}
        idxs = [id_to_pos[cid] for cid in ids]
        return "play", idxs, decision.reason
