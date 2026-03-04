from __future__ import annotations

import argparse

from engine import GameEngine
from models import RuleConfig, Team, VictoryConfig


def build_default_rule_config(debug_ai_reason: bool = False) -> RuleConfig:
    return RuleConfig(
        rank_order=["3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2", "SJ", "BJ", "GUARD_TOKEN", "EMPEROR_TOKEN"],
        allow_du_bao=True,
        guard_visibility="hidden",
        first_player_rule="emperor",
        three_must_be_last=True,
        special_two_override=False,
        allow_hua_gua=False,
        ai_knows_hidden_roles=True,
        debug_ai_reason=debug_ai_reason,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="山东保皇 CLI 原型")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--open-guard", action="store_true")
    args = parser.parse_args()

    rule_config = build_default_rule_config(debug_ai_reason=args.debug)
    if args.open_guard:
        rule_config.guard_visibility = "open"

    victory_config = VictoryConfig(
        emperor_side_win_if_any_first_and_teammate_top_n=3,
        du_bao_mode_rule="default",  # TODO: 支持更多地方化独保结算
    )

    engine = GameEngine(rule_config, victory_config, seed=args.seed, debug=args.debug)
    players = engine.create_default_players()
    state = engine.setup_game(players)

    print("=== 游戏开始 ===")
    print(f"皇帝玩家: P{state.emperor_id}")
    if state.revealed_guard:
        print(f"侍卫玩家: P{state.guard_id}")
    else:
        print("侍卫身份: 暗保（对局结束后公开）")

    result = engine.run(state)

    print("\n=== 对局结束 ===")
    print("名次:", " -> ".join(f"P{pid}" for pid in result.finish_order))
    print("身份:")
    for pid, role in state.roles.items():
        print(f"  P{pid}: {role.value}, team={state.teams[pid].value}")
    print("胜方:", "皇帝方" if result.winner_team == Team.EMPEROR_SIDE else "平民方")
    print("说明:", result.explanation)
    print("--- 最近日志 ---")
    for line in state.logs[-30:]:
        print(line)


if __name__ == "__main__":
    main()
