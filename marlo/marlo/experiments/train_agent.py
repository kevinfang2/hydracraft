from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from future import standard_library
from matplotlib.axes._base import _AxesBase

standard_library.install_aliases()  # NOQA

import logging
import os

from marlo.experiments.evaluator import Evaluator
from marlo.experiments.evaluator import save_agent
from chainerrl.misc.ask_yes_no import ask_yes_no
from chainerrl.misc.makedirs import makedirs


# By default all experiment logging is relative to the current directory. Change with set_log_base_dir.
_log_dir = "."


def set_log_base_dir(log_dir):
    """Change the default directory for experiment logs & results."""
    global _log_dir
    if log_dir != '' and not log_dir.endswith('/'):
        _log_dir = log_dir + '/'
    else:
        _log_dir = log_dir


def get_log_base_dir():
    return _log_dir


def save_agent_replay_buffer(agent, t, outdir, suffix='', logger=None):
    logger = logger or logging.getLogger(__name__)
    filename = os.path.join(outdir, '{}{}.replay.pkl'.format(t, suffix))
    agent.replay_buffer.save(filename)
    logger.info('Saved the current replay buffer to %s', filename)


def ask_and_save_agent_replay_buffer(agent, t, outdir, suffix=''):
    if hasattr(agent, 'replay_buffer') and \
            ask_yes_no('Replay buffer has {} transitions. Do you save them to a file?'.format(len(agent.replay_buffer))):  # NOQA
        save_agent_replay_buffer(agent, t, outdir, suffix=suffix)


def train_agent(agent, env, steps, outdir, max_episode_len=None,
                step_offset=0, evaluator=None, successful_score=None,
                step_hooks=[], num_resets=10**6, logger=None):

    logger = logger or logging.getLogger(__name__)

    episode_r = 0
    episode_idx = 0

    # o_0, r_0
    obs = env.reset()
    #action = env.action_space.sample()
    #obs, r, done, info = env.step(action)
    num_resets -= 1
    r = 0

    t = step_offset
    if hasattr(agent, 't'):
        agent.t = step_offset

    episode_len = 0
    try:
        while t < steps or num_resets > 0:
            # a_t
            action = agent.act_and_train(obs, r)
            # o_{t+1}, r_{t+1}
            obs, r, done, info = env.step(action)
            t += 1
            episode_r += r
            episode_len += 1

            for hook in step_hooks:
                hook(env, agent, t)

            if done or episode_len == max_episode_len or t == steps:
                agent.stop_episode_and_train(obs, r, done=done)
                logger.info('outdir:%s step:%s episode:%s R:%s',
                            outdir, t, episode_idx, episode_r)
                logger.info('statistics:%s', agent.get_statistics())


                f = open('rewards.txt', 'a+')
                f.write("reward: " + str(episode_r) + "\n")

                if evaluator is not None and num_resets > evaluator.n_runs:
                    evaluated, score = evaluator.evaluate_if_necessary(
                        t=t, episodes=episode_idx + 1)
                    if evaluated:
                        num_resets -= evaluator.n_runs
                    if (successful_score is not None and
                            evaluator.max_score >= successful_score):
                        break
                if t == steps and num_resets > 0:
                    print("WARNING ran out of steps. Any background agents will continue to run.")
                if t == steps or num_resets == 0:
                    break
                # Start a new episode
                episode_r = 0
                episode_idx += 1
                episode_len = 0
                obs = env.reset()
                num_resets -= 1
                print("eval resets " + str(num_resets))
                r = 0

    except (Exception, KeyboardInterrupt):
        # Save the current model before being killed
        save_agent(agent, t, outdir, logger, suffix='_except')
        raise

    # Save the final model
    save_agent(agent, t, outdir, logger, suffix='_finish')


def train_agent_with_evaluation(agent,
                                env,
                                steps,
                                eval_n_runs,
                                eval_interval,
                                outdir,
                                max_episode_len=None,
                                step_offset=0,
                                eval_explorer=None,
                                eval_max_episode_len=None,
                                eval_env=None,
                                successful_score=None,
                                step_hooks=[],
                                save_best_so_far_agent=True,
                                num_resets=10**6,
                                logger=None,
                                ):
    """Train an agent while regularly evaluating it.

    Args:
        agent: Agent to train.
        env: Environment train the againt against.
        steps (int): Number of total time steps for training.
        eval_n_runs (int): Number of runs for each time of evaluation.
        eval_interval (int): Interval of evaluation.
        outdir (str): Path to the directory to output things.
        max_episode_len (int): Maximum episode length.
        step_offset (int): Time step from which training starts.
        eval_explorer: Explorer used for evaluation.
        eval_max_episode_len (int or None): Maximum episode length of
            evaluation runs. If set to None, max_episode_len is used instead.
        eval_env: Environment used for evaluation.
        successful_score (float): Finish training if the mean score is greater
            or equal to this value if not None
        step_hooks (list): List of callable objects that accepts
            (env, agent, step) as arguments. They are called every step.
            See chainerrl.experiments.hooks.
        save_best_so_far_agent (bool): If set to True, after each evaluation,
            if the score (= mean return of evaluation episodes) exceeds
            the best-so-far score, the current agent is saved.
        num_resets: The number of resets to do - synchronized with background agents.
        logger (logging.Logger): Logger used in this function.
    """

    logger = logger or logging.getLogger(__name__)

    makedirs(outdir, exist_ok=True)

    if eval_env is None:
        eval_env = env

    if eval_max_episode_len is None:
        eval_max_episode_len = max_episode_len

    evaluator = Evaluator(agent=agent,
                          n_runs=eval_n_runs,
                          eval_interval=eval_interval, outdir=outdir,
                          max_episode_len=eval_max_episode_len,
                          explorer=eval_explorer,
                          env=eval_env,
                          step_offset=step_offset,
                          save_best_so_far_agent=save_best_so_far_agent,
                          logger=logger,
                          )

    train_agent(
        agent, env, steps, outdir,
        max_episode_len=max_episode_len,
        step_offset=step_offset,
        evaluator=evaluator,
        successful_score=successful_score,
        step_hooks=step_hooks,
        num_resets=num_resets,
        logger=logger)
