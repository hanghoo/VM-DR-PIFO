#!/usr/bin/env python3
"""
Q-learning controller for adaptive WRR.
- State: [qdepth, weight_ratio] with qdepth in [0, Nq], Nq=10 (QCMP style)
- Action: EF quantum adjustment only, Delta=1500, range [3000, 30000]
- Reward: r_t = sum(r'_t) - w_e(t) per the design doc
  r'_t = eps_ub*lambda if d_t <= d_ub else -(1-eps_ub)*lambda
  J = lambda*(P(d<=d_ub) - (1-eps_ub)) - E[w_e]
- AF quantum fixed at 6000, EF quantum variable
"""

import math
import numpy as np
from collections import defaultdict

# Constants from user spec
AF_QUANTUM_FIXED = 6000
EF_QUANTUM_MIN = 3000
EF_QUANTUM_MAX = 30000
DELTA = 1500
NQ = 10  # queue depth range [0, 10]
NUM_ACTIONS = 3  # -1: decrease EF, 0: hold, +1: increase EF


def discretize_qdepth(qdepth_raw):
    """Map raw queue depth to [0, Nq] per QCMP."""
    return min(NQ, max(0, int(qdepth_raw)))


def discretize_weight_ratio(ef_quantum, n_ratio_bins=5):
    """Map EF/(AF+EF) ratio to discrete bins. AF=6000 fixed."""
    total = AF_QUANTUM_FIXED + ef_quantum
    if total <= 0:
        return 0
    ratio = ef_quantum / total
    bin_idx = min(n_ratio_bins - 1, int(ratio * n_ratio_bins))
    return bin_idx


def state_to_idx(qdepth_disc, ratio_disc, n_ratio_bins=5):
    """Encode (qdepth, ratio) as single state index."""
    return qdepth_disc * n_ratio_bins + ratio_disc


def idx_to_state(idx, n_ratio_bins=5):
    """Decode state index to (qdepth, ratio)."""
    qdepth_disc = idx // n_ratio_bins
    ratio_disc = idx % n_ratio_bins
    return qdepth_disc, ratio_disc


class QLearningWRRController:
    def __init__(
        self,
        alpha=0.2,
        gamma=0.9,
        epsilon=0.4,
        d_ub_ms=50.0,
        eps_ub=0.05,
        lambda_tradeoff=1.0,
        n_ratio_bins=5,
    ):
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.d_ub = d_ub_ms
        self.eps_ub = eps_ub
        self.lambda_tradeoff = lambda_tradeoff
        self.n_ratio_bins = n_ratio_bins
        self.n_states = (NQ + 1) * n_ratio_bins
        self.n_actions = NUM_ACTIONS
        self.q_table = defaultdict(lambda: np.zeros(self.n_actions))
        self.ef_quantum = 6000  # initial, will be clamped to [3000,30000]
        self._last_state = None
        self._last_action = None
        self._latency_history = []
        self._we_history = []

    def get_ef_quantum(self):
        return self.ef_quantum

    def get_state(self, qdepth_raw, ef_quantum):
        """Build state (qdepth_disc, ratio_disc)."""
        qd = discretize_qdepth(qdepth_raw)
        rd = discretize_weight_ratio(ef_quantum, self.n_ratio_bins)
        return state_to_idx(qd, rd, self.n_ratio_bins)

    def choose_action(self, state_idx):
        """Epsilon-greedy action: -1 (decrease), 0 (hold), +1 (increase)."""
        if np.random.random() < self.epsilon:
            return np.random.randint(0, self.n_actions)
        q_vals = self.q_table[state_idx]
        return int(np.argmax(q_vals))

    def action_to_delta(self, action):
        """Map action index to EF quantum delta."""
        if action == 0:
            return 0
        if action == 1:
            return DELTA
        return -DELTA

    def apply_action(self, action):
        """Apply action and return new EF quantum."""
        delta = self.action_to_delta(action)
        new_q = self.ef_quantum + delta
        new_q = max(EF_QUANTUM_MIN, min(EF_QUANTUM_MAX, new_q))
        self.ef_quantum = new_q
        return self.ef_quantum

    def compute_r_prime(self, d_t):
        """r'_t = eps_ub*lambda if d_t <= d_ub else -(1-eps_ub)*lambda"""
        if d_t <= self.d_ub:
            return self.eps_ub * self.lambda_tradeoff
        return -(1 - self.eps_ub) * self.lambda_tradeoff

    def compute_w_e(self, ef_quantum):
        """w_e(t): EF weight cost, normalized by max quantum."""
        return ef_quantum / EF_QUANTUM_MAX

    def compute_reward(self, d_t, ef_quantum):
        """r_t = r'_t - w_e(t)"""
        r_prime = self.compute_r_prime(d_t)
        w_e = self.compute_w_e(ef_quantum)
        return r_prime - w_e

    def update_q(self, state, action, reward, next_state):
        """Q(s,a) += alpha * (r + gamma * max_a' Q(s',a') - Q(s,a))"""
        old_q = self.q_table[state][action]
        max_next = np.max(self.q_table[next_state]) if next_state is not None else 0
        td_target = reward + self.gamma * max_next
        new_q = old_q + self.alpha * (td_target - old_q)
        self.q_table[state][action] = new_q

    def step(self, qdepth_raw, latency_ms):
        """
        One control step: observe state, choose action, compute reward, update Q.
        Returns (ef_quantum, reward, action_name).
        """
        state = self.get_state(qdepth_raw, self.ef_quantum)
        action = self.choose_action(state)
        new_ef = self.apply_action(action)
        reward = self.compute_reward(latency_ms, self.ef_quantum)
        next_state = self.get_state(qdepth_raw, self.ef_quantum)
        self.update_q(state, action, reward, next_state)
        self._last_state = state
        self._last_action = action
        self._latency_history.append(latency_ms)
        self._we_history.append(self.compute_w_e(self.ef_quantum))
        action_names = ["decrease", "hold", "increase"]
        return new_ef, reward, action_names[action]

    def decay_epsilon(self, factor=0.95, min_eps=0.1):
        self.epsilon = max(min_eps, self.epsilon * factor)

    def set_ef_quantum(self, value):
        self.ef_quantum = max(EF_QUANTUM_MIN, min(EF_QUANTUM_MAX, int(value)))
