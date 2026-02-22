from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Suit(str, Enum):
    SPADE = "♠"
    HEART = "♥"
    CLUB = "♣"
    DIAMOND = "♦"
    JOKER = "JOKER"


class Role(str, Enum):
    EMPEROR = "emperor"
    GUARD = "guard"
    COMMONER = "commoner"


class Team(str, Enum):
    EMPEROR_SIDE = "emperor_side"
    COMMONER_SIDE = "commoner_side"


class GamePhase(str, Enum):
    DEAL = "deal"
    IDENTIFY = "identify"
    PLAYING = "playing"
    FINISHED = "finished"


class PlayType(str, Enum):
    SINGLE = "single"
    PAIR = "pair"
    TRIPLE = "triple"
    SET = "set"


@dataclass(frozen=True)
class Card:
    card_id: str
    deck_index: int
    suit: Suit
    rank: str
    is_emperor_token: bool = False
    is_guard_token: bool = False

    def display_rank(self) -> str:
        if self.is_emperor_token:
            return "皇牌"
        if self.is_guard_token:
            return "保牌"
        if self.rank == "SJ":
            return "小王"
        if self.rank == "BJ":
            return "大王"
        return self.rank

    def short(self) -> str:
        if self.suit == Suit.JOKER:
            return self.display_rank()
        return f"{self.suit.value}{self.display_rank()}"


@dataclass
class Play:
    type: PlayType
    main_rank: str
    count: int
    cards: list[Card]

    def brief(self) -> str:
        return f"{self.type.value}:{self.main_rank}x{self.count}"


@dataclass
class RuleConfig:
    rank_order: list[str]
    allow_du_bao: bool = True
    guard_visibility: str = "hidden"
    first_player_rule: str = "emperor"
    three_must_be_last: bool = True
    special_two_override: bool = False
    allow_hua_gua: bool = False
    ai_knows_hidden_roles: bool = True
    debug_ai_reason: bool = False
    max_turns_guard: int = 5000
    redeal_on_conflict_if_no_du_bao: bool = True


@dataclass
class VictoryConfig:
    emperor_side_win_if_any_first_and_teammate_top_n: int = 3
    du_bao_mode_rule: str = "default"


@dataclass
class GameState:
    players: list["BasePlayer"]
    hands: dict[int, list[Card]] = field(default_factory=dict)
    roles: dict[int, Role] = field(default_factory=dict)
    teams: dict[int, Team] = field(default_factory=dict)
    current_turn_index: int = 0
    last_play: Optional[Play] = None
    last_play_player_id: Optional[int] = None
    trick_leader_player_id: Optional[int] = None
    passes_in_row: int = 0
    finish_order: list[int] = field(default_factory=list)
    phase: GamePhase = GamePhase.DEAL
    revealed_guard: bool = False
    turn_count: int = 0
    logs: list[str] = field(default_factory=list)
    emperor_id: Optional[int] = None
    guard_id: Optional[int] = None
    stop_requested: bool = False

    def is_finished_player(self, player_id: int) -> bool:
        return player_id in self.finish_order


class BasePlayer:
    player_id: int
    name: str

    def take_turn(self, state: GameState, config: RuleConfig) -> tuple[str, Optional[list[int]], str]:
        raise NotImplementedError
