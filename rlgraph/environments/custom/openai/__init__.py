from gym.envs.registration import register

register(
    id='bitflip-v0',
    entry_point='rlgraph.environments.custom.openai.envs:BitFlip',
    max_episode_steps=200,
    reward_threshold=195.0,
)