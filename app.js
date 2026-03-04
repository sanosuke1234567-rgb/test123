(() => {
  const RANK_ORDER = ["3","4","5","6","7","8","9","10","J","Q","K","A","2","SJ","BJ","GUARD_TOKEN","EMPEROR_TOKEN"];
  const SUITS = ["♠","♥","♣","♦"];
  const rankValue = Object.fromEntries(RANK_ORDER.map((r, i) => [r, i]));

  const state = {
    players: [0,1,2,3,4],
    hands: {},
    roles: {},
    teams: {},
    emperorId: null,
    guardId: null,
    currentTurn: 0,
    lastPlay: null,
    lastPlayPlayerId: null,
    passesInRow: 0,
    finishOrder: [],
    logs: [],
    revealedGuard: false,
    selected: new Set(),
    ended: false,
  };

  function cardShort(c) {
    if (c.isEmperorToken) return "皇牌";
    if (c.isGuardToken) return "保牌";
    const r = c.rank === "SJ" ? "小王" : c.rank === "BJ" ? "大王" : c.rank;
    return c.suit === "JOKER" ? r : `${c.suit}${r}`;
  }

  function effRank(c) {
    if (c.isEmperorToken) return "EMPEROR_TOKEN";
    if (c.isGuardToken) return "GUARD_TOKEN";
    return c.rank;
  }

  function sortHand(hand) {
    const suitOrder = {"♠":0,"♥":1,"♣":2,"♦":3,"JOKER":4};
    hand.sort((a,b) => {
      const ra = rankValue[effRank(a)] - rankValue[effRank(b)];
      if (ra !== 0) return ra;
      const sa = suitOrder[a.suit] - suitOrder[b.suit];
      if (sa !== 0) return sa;
      return a.id.localeCompare(b.id);
    });
  }

  function createDeck() {
    const ranks = ["3","4","5","6","7","8","9","10","J","Q","K","A","2"];
    const deck = [];
    for (let d=1; d<=4; d++) {
      for (const r of ranks) {
        for (const s of SUITS) deck.push({id:`D${d}-${s}-${r}`, deck:d, suit:s, rank:r, isEmperorToken:false, isGuardToken:false});
      }
      deck.push({id:`D${d}-SJ`, deck:d, suit:"JOKER", rank:"SJ", isEmperorToken:false, isGuardToken:false});
      deck.push({id:`D${d}-BJ`, deck:d, suit:"JOKER", rank:"BJ", isEmperorToken:false, isGuardToken:false});
    }
    // default token cards
    deck.find(c => c.id === "D1-BJ").isEmperorToken = true;
    deck.find(c => c.id === "D1-SJ").isGuardToken = true;
    return deck;
  }

  function shuffle(arr) {
    for (let i=arr.length-1; i>0; i--) {
      const j = Math.floor(Math.random() * (i+1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
  }

  function identifyPlay(cards) {
    if (!cards.length) return null;
    const ranks = cards.map(effRank);
    if (new Set(ranks).size !== 1) return null;
    const mainRank = ranks[0];
    const count = cards.length;
    let type = null;
    if (count === 1) type = "single";
    else if (count === 2) type = "pair";
    else if (count === 3) type = "triple";
    else if (count >= 4) type = "set";
    if (!type) return null;
    return {type, mainRank, count, cards};
  }

  function canBeat(lastPlay, newPlay) {
    if (lastPlay.type !== newPlay.type || lastPlay.count !== newPlay.count) return false;
    return rankValue[newPlay.mainRank] > rankValue[lastPlay.mainRank];
  }

  function violatesThreeLast(hand, play, isLead) {
    if (!isLead || play.mainRank !== "3") return false;
    return hand.some(c => effRank(c) !== "3");
  }

  function isLegalPlay(hand, play, lastPlay) {
    const ids = new Set(hand.map(c => c.id));
    if (play.cards.some(c => !ids.has(c.id))) return [false, "出的牌不在手牌中"];
    const idPlay = identifyPlay(play.cards);
    if (!idPlay) return [false, "牌型不合法"];
    const isLead = !lastPlay;
    if (violatesThreeLast(hand, idPlay, isLead)) return [false, "规则限制：手里还有非3，不能主动出3"];
    if (lastPlay && !canBeat(lastPlay, idPlay)) return [false, "无法压牌：同牌型同张数且主点更大"];
    return [true, "ok"];
  }

  function allCandidates(hand) {
    const byRank = {};
    for (const c of hand) {
      const r = effRank(c);
      byRank[r] ||= [];
      byRank[r].push(c);
    }
    const cands = [];
    for (const k of Object.keys(byRank)) {
      const cards = byRank[k];
      for (let n=1; n<=cards.length; n++) {
        const p = identifyPlay(cards.slice(0,n));
        if (p) cands.push(p);
      }
    }
    return cands;
  }

  function botChoose(pid) {
    const hand = state.hands[pid];
    const cands = allCandidates(hand);
    if (!state.lastPlay) {
      cands.sort((a,b) => (rankValue[a.mainRank]-rankValue[b.mainRank]) || (b.count-a.count));
      return cands[0] || null;
    }
    const beats = cands.filter(p => canBeat(state.lastPlay, p));
    if (!beats.length) return null;
    beats.sort((a,b) => (rankValue[a.mainRank]-rankValue[b.mainRank]) || (a.count-b.count));
    return beats[0];
  }

  function removeCards(hand, cards) {
    const ids = new Set(cards.map(c => c.id));
    return hand.filter(c => !ids.has(c.id));
  }

  function nextActiveTurn() {
    for (let i=0; i<5; i++) {
      state.currentTurn = (state.currentTurn + 1) % 5;
      if (!state.finishOrder.includes(state.currentTurn)) return;
    }
  }

  function clearIfNeeded() {
    const active = state.players.filter(p => !state.finishOrder.includes(p)).length;
    if (state.passesInRow >= Math.max(0, active - 1)) {
      const leader = state.lastPlayPlayerId;
      state.logs.push(`清台，P${leader}重新领出`);
      state.lastPlay = null;
      state.passesInRow = 0;
      if (leader != null && !state.finishOrder.includes(leader)) state.currentTurn = leader;
    }
  }

  function roleAssign() {
    let emperor = null, guard = null;
    for (const pid of state.players) {
      if (state.hands[pid].some(c => c.isEmperorToken)) emperor = pid;
      if (state.hands[pid].some(c => c.isGuardToken)) guard = pid;
    }
    state.emperorId = emperor;
    state.guardId = guard;
    for (const pid of state.players) {
      if (pid === emperor) {
        state.roles[pid] = "emperor";
        state.teams[pid] = "emperor_side";
      } else if (pid === guard) {
        state.roles[pid] = "guard";
        state.teams[pid] = "emperor_side";
      } else {
        state.roles[pid] = "commoner";
        state.teams[pid] = "commoner_side";
      }
    }
    state.currentTurn = emperor;
  }

  function judgeResult() {
    const first = state.finishOrder[0];
    const emperorSide = state.players.filter(p => state.teams[p] === "emperor_side");
    if (emperorSide.length === 1) {
      return first === emperorSide[0] ? "独保玩家第一，皇帝方胜" : "独保失败，平民方胜";
    }
    if (state.teams[first] === "emperor_side") {
      const mate = emperorSide.find(x => x !== first);
      const mateRank = state.finishOrder.indexOf(mate) + 1;
      if (mateRank <= 3) return "皇帝方一人第一且队友前3，皇帝方胜";
    }
    return "平民方胜";
  }

  function maybeFinish() {
    if (state.finishOrder.length === 5) {
      state.ended = true;
      state.revealedGuard = true;
      return true;
    }
    return false;
  }

  function runAIUntilHuman() {
    let guard = 0;
    while (!state.ended && state.currentTurn !== 0) {
      guard++;
      if (guard > 4000) throw new Error("loop overflow");
      const pid = state.currentTurn;
      if (state.finishOrder.includes(pid)) { nextActiveTurn(); continue; }
      const play = botChoose(pid);
      if (!play) {
        if (!state.lastPlay) {
          const forced = identifyPlay([state.hands[pid][0]]);
          doPlay(pid, forced, "AI领出兜底");
        } else {
          state.passesInRow += 1;
          state.logs.push(`P${pid} pass`);
          clearIfNeeded();
          nextActiveTurn();
        }
        continue;
      }
      doPlay(pid, play, "AI出牌");
      if (!maybeFinish()) nextActiveTurn();
    }
  }

  function doPlay(pid, play, reason="") {
    const hand = state.hands[pid];
    const [ok, msg] = isLegalPlay(hand, play, state.lastPlay);
    if (!ok) {
      state.logs.push(`P${pid} illegal(${msg})`);
      return false;
    }
    state.hands[pid] = removeCards(hand, play.cards);
    state.lastPlay = play;
    state.lastPlayPlayerId = pid;
    state.passesInRow = 0;
    state.logs.push(`P${pid} play ${play.type}:${play.mainRank}x${play.count} ${reason}`.trim());
    if (state.hands[pid].length === 0) {
      state.finishOrder.push(pid);
      state.logs.push(`P${pid} 出完，名次#${state.finishOrder.length}`);
      if (state.lastPlayPlayerId === pid) {
        state.lastPlay = null;
        state.lastPlayPlayerId = null;
      }
    }
    return true;
  }

  function newGame() {
    state.hands = {0:[],1:[],2:[],3:[],4:[]};
    state.roles = {};
    state.teams = {};
    state.finishOrder = [];
    state.logs = [];
    state.lastPlay = null;
    state.lastPlayPlayerId = null;
    state.passesInRow = 0;
    state.selected = new Set();
    state.ended = false;
    state.revealedGuard = false;

    const deck = createDeck();
    shuffle(deck);
    deck.forEach((c, i) => state.hands[i % 5].push(c));
    for (const pid of state.players) sortHand(state.hands[pid]);
    roleAssign();
    state.logs.push(`开局：皇帝=P${state.emperorId}，侍卫=暗保`);
    runAIUntilHuman();
    render();
  }

  function selectedCardsFromHand() {
    const hand = state.hands[0];
    const idxs = [...state.selected].sort((a,b)=>a-b);
    if (idxs.some(i => i < 0 || i >= hand.length)) return null;
    return idxs.map(i => hand[i]);
  }

  function doHumanPlay() {
    if (state.ended) return setMsg("对局已结束", "warn");
    if (state.currentTurn !== 0) return setMsg("尚未轮到你", "warn");
    const cards = selectedCardsFromHand();
    if (!cards || !cards.length) return setMsg("请先选择牌", "warn");
    const play = identifyPlay(cards);
    if (!play) return setMsg("牌型不合法", "err");
    if (!doPlay(0, play, "玩家出牌")) return setMsg("出牌失败", "err");
    state.selected.clear();
    if (!maybeFinish()) {
      nextActiveTurn();
      runAIUntilHuman();
      maybeFinish();
    }
    render();
  }

  function doHumanPass() {
    if (state.ended) return setMsg("对局已结束", "warn");
    if (state.currentTurn !== 0) return setMsg("尚未轮到你", "warn");
    if (!state.lastPlay) return setMsg("当前无待压牌，不能过牌", "warn");
    state.logs.push("P0 pass");
    state.passesInRow += 1;
    state.selected.clear();
    clearIfNeeded();
    nextActiveTurn();
    runAIUntilHuman();
    maybeFinish();
    render();
  }

  function setMsg(text, klass="warn") {
    const el = document.getElementById("msg");
    el.textContent = text;
    el.className = klass;
  }

  function hint() {
    if (state.currentTurn !== 0) return setMsg("尚未轮到你", "warn");
    const p = botChoose(0);
    if (!p) return setMsg("提示：pass", "ok");
    return setMsg(`提示：${p.type}:${p.mainRank}x${p.count}`, "ok");
  }

  function render() {
    const guardShown = state.revealedGuard || state.ended ? `P${state.guardId}` : "隐藏";
    document.getElementById("meta").textContent = `皇帝: P${state.emperorId} | 侍卫: ${guardShown} | 当前轮到: P${state.currentTurn}`;
    document.getElementById("table").textContent = `桌面待压牌: ${state.lastPlay ? `${state.lastPlay.type}:${state.lastPlay.mainRank}x${state.lastPlay.count}` : "无"} | 当前领出: ${state.lastPlayPlayerId ?? "无"}`;
    document.getElementById("counts").textContent = `你: ${state.hands[0].length} 张 | AI: P1=${state.hands[1].length}, P2=${state.hands[2].length}, P3=${state.hands[3].length}, P4=${state.hands[4].length}`;
    document.getElementById("finish").textContent = `完成名次: ${state.finishOrder.map(p=>`P${p}`).join(' -> ') || '暂无'}`;
    document.getElementById("result").textContent = state.ended ? `结算：${judgeResult()} | 身份：${state.players.map(p=>`P${p}:${state.roles[p]}`).join(', ')}` : "";
    document.getElementById("logs").textContent = state.logs.slice(-35).join("\n");

    const hand = state.hands[0];
    const handDiv = document.getElementById("hand");
    handDiv.innerHTML = "";
    hand.forEach((c, i) => {
      const b = document.createElement("button");
      b.textContent = `[${i}] ${cardShort(c)}`;
      if (state.selected.has(i)) b.classList.add("selected");
      b.onclick = () => {
        if (state.selected.has(i)) state.selected.delete(i); else state.selected.add(i);
        render();
      };
      handDiv.appendChild(b);
    });
  }

  document.getElementById("new-game").onclick = () => { newGame(); setMsg("已新开一局", "ok"); };
  document.getElementById("play").onclick = doHumanPlay;
  document.getElementById("pass").onclick = doHumanPass;
  document.getElementById("clear").onclick = () => { state.selected.clear(); render(); };
  document.getElementById("hint").onclick = hint;

  newGame();
})();
