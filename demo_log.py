from ai import MediumAIBot
from engine import GameEngine
from models import VictoryConfig
from players import AIPlayer
from main import build_default_rule_config


def run_demo(seed: int = 42):
    rule = build_default_rule_config(debug_ai_reason=True)
    victory = VictoryConfig()
    engine = GameEngine(rule, victory, seed=seed, debug=True)
    players = [AIPlayer(i, f"AI-{i}", MediumAIBot(), engine.rnd) for i in range(5)]
    state = engine.setup_game(players)
    result = engine.run(state)
    print("名次:", result.finish_order)
    for line in state.logs[:40]:
        print(line)


if __name__ == '__main__':
    run_demo()
