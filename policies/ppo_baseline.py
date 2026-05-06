from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List
import copy
import numpy as np

from env.mobility import ALL_MOVES


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits)
    exp = np.exp(shifted)
    return exp / max(float(np.sum(exp)), 1e-12)


def _feature_vector(obs: Dict[str, Any], cfg: Dict[str, Any]) -> np.ndarray:
    area_w = float(cfg["area"]["width"])
    area_h = float(cfg["area"]["height"])
    episode_length = max(float(cfg["episode_length"]), 1.0)
    budget = max(float(cfg["sync"]["budget"]), 1e-12)
    r_min = max(float(cfg["channel"]["r_min"]), 1e-12)
    a_max = max(float(cfg["metrics"]["a_max"]), 1e-12)
    d_max = max(float(cfg["metrics"]["d_max"]), 1e-12)
    sigma_max = max(float(cfg["metrics"]["sigma_max"]), 1e-12)

    uav1 = np.asarray(obs["uav1_pos"], dtype=float)
    uav2 = np.asarray(obs["uav2_pos"], dtype=float)
    twin = np.asarray(obs["twin_eve_pos"], dtype=float)

    values = [
        1.0,
        float(obs["slot"]) / episode_length,
        uav1[0] / area_w,
        uav1[1] / area_h,
        uav2[0] / area_w,
        uav2[1] / area_h,
        twin[0] / area_w,
        twin[1] / area_h,
        float(obs["aoi"]) / a_max,
        float(obs["twin_sigma"]) / sigma_max,
        float(obs["remaining_budget"]) / budget,
        float(obs["pred_error_radius"]) / d_max,
        float(obs["pred_margin"]) / r_min,
        float(obs["cert_slack"]) / r_min,
        float(obs["certified_safe"]),
        float(obs["pending_syncs"]) / 4.0,
        float(obs.get("decision_twin_badness", 0.0)),
    ]
    return np.clip(np.asarray(values, dtype=float), -5.0, 5.0)


def reward_from_info(info: Dict[str, Any], cfg: Dict[str, Any]) -> float:
    r_min = float(cfg["channel"]["r_min"])
    return float(
        info["true_r_sec"]
        - float(cfg["control"]["lambda_move"]) * info["movement_cost"]
        - float(cfg["control"]["lambda_power"]) * info["power_cost"]
        - float(cfg["control"]["lambda_sync"]) * info["sync_cost"]
        - float(cfg["control"].get("lambda_outage", 0.0)) * max(r_min - info["true_r_sec"], 0.0)
    )


@dataclass
class PPOPolicy:
    cfg: Dict[str, Any]
    moves: list[str]
    p_s_levels: list[float]
    p_j_levels: list[float]
    bandwidth_levels: list[float]
    weights: list[np.ndarray]
    biases: list[np.ndarray]
    value_w: np.ndarray
    value_b: float

    @classmethod
    def initialize(cls, cfg: Dict[str, Any], rng: np.random.Generator) -> "PPOPolicy":
        moves = list(cfg["control"].get("allowed_moves", ALL_MOVES))
        p_s_levels = [float(x) for x in cfg["control"]["p_s_levels"]]
        p_j_levels = [float(x) for x in cfg["control"]["p_j_levels"]]
        bandwidth_levels = [
            float(x)
            for x in cfg["sync"].get("bandwidth_levels", [cfg["sync"].get("bandwidth_max", 1.0)])
            if float(x) > 0.0
        ]
        dummy_obs = {
            "slot": 0,
            "uav1_pos": np.zeros(2),
            "uav2_pos": np.zeros(2),
            "twin_eve_pos": np.zeros(2),
            "aoi": 0,
            "twin_sigma": 0.0,
            "remaining_budget": float(cfg["sync"]["budget"]),
            "pred_error_radius": 0.0,
            "pred_margin": 0.0,
            "cert_slack": 0.0,
            "certified_safe": 1,
            "pending_syncs": 0,
            "decision_twin_badness": 0.0,
        }
        n_features = len(_feature_vector(dummy_obs, cfg))
        head_sizes = [len(moves), len(moves), len(p_s_levels), len(p_j_levels), 2, len(bandwidth_levels)]
        weights = [rng.normal(0.0, 0.02, size=(n_features, size)) for size in head_sizes]
        biases = [np.zeros(size, dtype=float) for size in head_sizes]
        value_w = np.zeros(n_features, dtype=float)
        return cls(
            cfg=copy.deepcopy(cfg),
            moves=moves,
            p_s_levels=p_s_levels,
            p_j_levels=p_j_levels,
            bandwidth_levels=bandwidth_levels,
            weights=weights,
            biases=biases,
            value_w=value_w,
            value_b=0.0,
        )

    def save(self, path: str | Path) -> None:
        payload: dict[str, Any] = {
            "moves": np.asarray(self.moves, dtype=object),
            "p_s_levels": np.asarray(self.p_s_levels, dtype=float),
            "p_j_levels": np.asarray(self.p_j_levels, dtype=float),
            "bandwidth_levels": np.asarray(self.bandwidth_levels, dtype=float),
            "value_w": self.value_w,
            "value_b": np.asarray([self.value_b], dtype=float),
        }
        for idx, (weight, bias) in enumerate(zip(self.weights, self.biases)):
            payload[f"w_{idx}"] = weight
            payload[f"b_{idx}"] = bias
        np.savez(path, **payload)

    @classmethod
    def load(cls, cfg: Dict[str, Any], path: str | Path) -> "PPOPolicy":
        data = np.load(path, allow_pickle=True)
        weights = []
        biases = []
        idx = 0
        while f"w_{idx}" in data:
            weights.append(np.asarray(data[f"w_{idx}"], dtype=float))
            biases.append(np.asarray(data[f"b_{idx}"], dtype=float))
            idx += 1
        return cls(
            cfg=copy.deepcopy(cfg),
            moves=[str(x) for x in data["moves"].tolist()],
            p_s_levels=[float(x) for x in data["p_s_levels"].tolist()],
            p_j_levels=[float(x) for x in data["p_j_levels"].tolist()],
            bandwidth_levels=[float(x) for x in data["bandwidth_levels"].tolist()],
            weights=weights,
            biases=biases,
            value_w=np.asarray(data["value_w"], dtype=float),
            value_b=float(data["value_b"][0]),
        )

    def distributions(self, features: np.ndarray) -> list[np.ndarray]:
        return [_softmax(features @ weight + bias) for weight, bias in zip(self.weights, self.biases)]

    def value(self, features: np.ndarray) -> float:
        return float(features @ self.value_w + self.value_b)

    def sample(self, obs: Dict[str, Any], rng: np.random.Generator) -> tuple[Dict[str, Any], list[int], float, float, np.ndarray]:
        features = _feature_vector(obs, self.cfg)
        dists = self.distributions(features)
        indices = [int(rng.choice(len(prob), p=prob)) for prob in dists]
        logprob = float(sum(np.log(max(dists[i][idx], 1e-12)) for i, idx in enumerate(indices)))
        return self._action_from_indices(indices, obs), indices, logprob, self.value(features), features

    def act(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        features = _feature_vector(obs, self.cfg)
        indices = [int(np.argmax(prob)) for prob in self.distributions(features)]
        return self._action_from_indices(indices, obs)

    def _action_from_indices(self, indices: list[int], obs: Dict[str, Any]) -> Dict[str, Any]:
        move1_idx, move2_idx, p_s_idx, p_j_idx, sync_idx, bw_idx = indices
        sync = bool(sync_idx)
        bandwidth = 0.0
        if sync and float(obs["remaining_budget"]) >= float(self.cfg["sync"].get("bandwidth_min", 0.25)):
            requested = self.bandwidth_levels[bw_idx]
            bandwidth = min(requested, float(obs["remaining_budget"]))
        return {
            "move_uav1": self.moves[move1_idx],
            "move_uav2": self.moves[move2_idx],
            "p_s": self.p_s_levels[p_s_idx],
            "p_j": self.p_j_levels[p_j_idx],
            "sync": bandwidth > 0.0,
            "sync_bandwidth": float(bandwidth),
            "sync_reason": "ppo_policy" if bandwidth > 0.0 else "ppo_skip",
        }

    def update(
        self,
        samples: list[dict[str, Any]],
        *,
        learning_rate: float,
        value_learning_rate: float,
        clip_eps: float,
        entropy_coef: float,
        epochs: int,
        rng: np.random.Generator,
    ) -> None:
        if not samples:
            return
        adv = np.asarray([row["advantage"] for row in samples], dtype=float)
        adv = (adv - float(np.mean(adv))) / max(float(np.std(adv)), 1e-6)
        for idx, row in enumerate(samples):
            row["norm_advantage"] = float(adv[idx])

        for _ in range(max(1, epochs)):
            order = rng.permutation(len(samples))
            for sample_idx in order:
                row = samples[int(sample_idx)]
                features = row["features"]
                dists = self.distributions(features)
                logprob = float(
                    sum(np.log(max(dists[i][choice], 1e-12)) for i, choice in enumerate(row["indices"]))
                )
                ratio = float(np.exp(np.clip(logprob - row["logprob"], -5.0, 5.0)))
                advantage = float(row["norm_advantage"])
                unclipped = ratio * advantage
                clipped = float(np.clip(ratio, 1.0 - clip_eps, 1.0 + clip_eps)) * advantage
                use_policy_grad = unclipped <= clipped if advantage >= 0.0 else unclipped >= clipped

                if use_policy_grad:
                    coef = learning_rate * ratio * advantage
                    for head_idx, choice in enumerate(row["indices"]):
                        grad_logits = -dists[head_idx].copy()
                        grad_logits[int(choice)] += 1.0
                        grad_logits += entropy_coef * (-np.log(np.maximum(dists[head_idx], 1e-12)) - 1.0)
                        self.weights[head_idx] += coef * np.outer(features, grad_logits)
                        self.biases[head_idx] += coef * grad_logits

                value_error = float(row["return"] - self.value(features))
                self.value_w += value_learning_rate * value_error * features
                self.value_b += value_learning_rate * value_error


class NumpyPPOController:
    def __init__(self, cfg: Dict[str, Any], policy_path: str | Path):
        self.policy = PPOPolicy.load(cfg, policy_path)

    def act(self, env, obs: Dict[str, Any]) -> Dict[str, Any]:
        return self.policy.act(obs)


def discounted_returns(rewards: Iterable[float], gamma: float) -> list[float]:
    values: list[float] = []
    running = 0.0
    for reward in reversed(list(rewards)):
        running = float(reward) + gamma * running
        values.append(running)
    values.reverse()
    return values
