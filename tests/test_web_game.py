from main import build_default_rule_config
from models import VictoryConfig
from web_game import WebGame


def test_web_game_init_and_state():
    game = WebGame(build_default_rule_config(), VictoryConfig(), seed=1)
    game.new_game()
    vm = game.view_model()
    assert vm["started"] is True
    assert vm["my_hand_count"] in {43, 44}
    assert vm["turn"] in {0, 1, 2, 3, 4}


def test_web_game_reject_invalid_pass_when_no_last_play():
    game = WebGame(build_default_rule_config(), VictoryConfig(), seed=2)
    game.new_game()
    # If not player's turn, force-run until player's turn for deterministic check
    while game.state.phase.value == "playing" and game.state.current_turn_index != 0:
        game._run_ai_until_human_turn()
    game.state.last_play = None
    res = game.human_action("pass")
    assert not res.ok
