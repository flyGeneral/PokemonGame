"""用 Stable Baselines3 PPO 训练智能体玩星钻精灵(可选,需安装依赖)。

安装(参考 PokemonRedExperiments 的训练栈):
    python3 -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \
        stable-baselines3 torch tensorboard

训练: python3 tools/train_ppo.py [总步数,默认100000]
回放: python3 tools/train_ppo.py play
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "ppo_stardrop")


def main():
    try:
        from stable_baselines3 import PPO
    except ImportError:
        print("未安装 stable-baselines3。请先执行:")
        print("  python3 -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple "
              "stable-baselines3 torch tensorboard")
        return 1

    from envs.pokemon_env import PokeEnv

    if len(sys.argv) > 1 and sys.argv[1] == "play":
        assert os.path.exists(MODEL_PATH + ".zip"), "还没有训练好的模型,先运行训练。"
        model = PPO.load(MODEL_PATH)
        env = PokeEnv(max_steps=20000)
        obs, info = env.reset()
        total = 0.0
        for _ in range(20000):
            action, _ = model.predict(obs, deterministic=True)
            obs, r, term, trunc, info = env.step(int(action))
            total += r
            if term or trunc:
                print(f"回合结束: reward={total:+.2f} info={info}")
                break
        env.render_exploration("/tmp/explo_heatmap_play.png")
        print("回放热力图: /tmp/explo_heatmap_play.png")
        return 0

    total_steps = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    env = PokeEnv(max_steps=20000)
    os.makedirs(MODEL_DIR, exist_ok=True)
    model = PPO(
        "MultiInputPolicy", env,
        n_steps=512, batch_size=256, gamma=0.99,
        ent_coef=0.02,               # 提高探索(随机基线几乎不动,需强探索)
        verbose=1, tensorboard_log=MODEL_DIR,
    )
    model.learn(total_timesteps=total_steps)
    model.save(MODEL_PATH)
    print(f"模型已保存: {MODEL_PATH}.zip")
    print("查看训练曲线: tensorboard --logdir", MODEL_DIR)
    print("回放: python3 tools/train_ppo.py play")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
