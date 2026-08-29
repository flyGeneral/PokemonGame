"""随机智能体跑 PokeEnv,验证环境并输出探索统计(参考 PokemonRedExperiments 的基线思路)。

用法: python3 tools/run_random_agent.py [步数,默认3000]
"""
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from envs.pokemon_env import PokeEnv, ACTION_NAMES


def run(total_steps=3000, verbose_every=200):
    env = PokeEnv(max_steps=total_steps)
    obs, info = env.reset(seed=0)
    rewards = deque(maxlen=100)
    ep_r = 0.0
    best = (-1, None)
    for t in range(total_steps):
        a = int(env.rng.integers(env.action_space_n))
        obs, r, term, trunc, info = env.step(a)
        ep_r += r
        rewards.append(r)
        if info["explored"] > best[0]:
            best = (info["explored"], dict(info))
        if (t + 1) % verbose_every == 0:
            avg = sum(rewards) / len(rewards)
            print(f"step {t+1:5d}  action={ACTION_NAMES[a]:6s}  r={r:+.3f}  "
                  f"avg100={avg:+.3f}  total={ep_r:+.2f}  "
                  f"pos=({info['map']}:{info['x']},{info['y']})  "
                  f"explored={info['explored']}  lv={info['total_levels']}  "
                  f"team={info['party_size']}  balls={info['balls']}")
        if term or trunc:
            print(f"回合结束 @step {t+1}: total_reward={ep_r:+.2f} terminated={term}")
            break
    out = "/tmp/explo_heatmap.png"
    env.render_exploration(out)
    print(f"\n最终统计: total_reward={ep_r:+.2f}  explored={best[0]} 格")
    print(f"最佳时刻: {best[1]}")
    print(f"探索热力图已保存: {out}")
    return ep_r


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    run(steps)
