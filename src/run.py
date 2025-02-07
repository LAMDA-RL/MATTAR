import datetime
import os
import pprint
import time
import threading
import torch as th
from types import SimpleNamespace as SN
from utils.logging import Logger
from utils.timehelper import time_left, time_str
from os.path import dirname, abspath
import json

from learners import REGISTRY as le_REGISTRY
from runners import REGISTRY as r_REGISTRY
from controllers import REGISTRY as mac_REGISTRY
from components.episode_buffer import ReplayBuffer
from components.transforms import OneHot


def run(_run, _config, _log):

    # check args sanity
    _config = args_sanity_check(_config, _log)

    args = SN(**_config)
    args.device = "cuda" if args.use_cuda else "cpu"

    # setup loggers
    logger = Logger(_log)

    _log.info("Experiment Parameters:")
    experiment_params = pprint.pformat(_config,
                                       indent=4,
                                       width=1)
    _log.info("\n\n" + experiment_params + "\n")

    remark_str = getattr(args, "remark", "nop")
    unique_token = "{}__{}_{}".format(args.name, remark_str, datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    args.unique_token = unique_token
    
    if args.use_tensorboard and not args.evaluate:
        # only log tensorboard when in training mode
        if args.env == "sc2":
            # sc2
            tb_logs_direc = os.path.join(dirname(dirname(abspath(__file__))), "results", args.env, args.env_args["map_name"], args.name)
        else:
            tb_logs_direc = os.path.join(dirname(dirname(abspath(__file__))), "results", args.env, args.name)
        
        if not os.path.exists(tb_logs_direc):
            os.makedirs(tb_logs_direc)
        tb_exp_direc = os.path.join(tb_logs_direc, "{}").format(unique_token)
        logger.setup_tb(tb_exp_direc)
        
        # write config file
        config_str = json.dumps(vars(args), indent=4)
        with open(os.path.join(tb_exp_direc, "config.json"), "w") as f:
            f.write(config_str)

    # get unique output file name
    if args.env == "sc2":
        # sc2
        output_dirname = os.path.join(dirname(dirname(abspath(__file__))), "outputs", args.env, args.env_args["map_name"], args.name)
    else:
        output_dirname = os.path.join(dirname(dirname(abspath(__file__))), "outputs", args.env, args.name)

    if not os.path.exists(output_dirname):
        os.makedirs(output_dirname)

    # set output dir
    args.output_dir = os.path.join(output_dirname, unique_token)
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    output_file = os.path.join(output_dirname, f"{unique_token}.out")

    # sacred is on by default
    logger.setup_sacred(_run, output_file)

    # Run and train
    run_sequential(args=args, logger=logger)

    # Clean up after finishing
    print("Exiting Main")

    print("Stopping all threads")
    for t in threading.enumerate():
        if t.name != "MainThread":
            print("Thread {} is alive! Is daemon: {}".format(t.name, t.daemon))
            t.join(timeout=1)
            print("Thread joined")

    print("Exiting script")

    # Making sure framework really exits
    os._exit(os.EX_OK)


def evaluate_sequential(args, runner):

    for _ in range(args.test_nepisode):
        runner.run(test_mode=True)

    if args.save_replay:
        runner.save_replay()
    
    runner.close_env()

def run_sequential(args, logger):

    # Init runner so we can get env info
    runner = r_REGISTRY[args.runner](args=args, logger=logger)

    # Set up schemes and groups here
    env_info = runner.get_env_info()
    args.n_agents = env_info["n_agents"]
    args.n_actions = env_info["n_actions"]
    args.state_shape = env_info["state_shape"]

    # Default/Base scheme
    scheme = {
        "state": {"vshape": env_info["state_shape"]},
        "obs": {"vshape": env_info["obs_shape"], "group": "agents"},
        "actions": {"vshape": (1,), "group": "agents", "dtype": th.long},
        "avail_actions": {"vshape": (env_info["n_actions"],), "group": "agents", "dtype": th.int},
        "reward": {"vshape": (1,)},
        "terminated": {"vshape": (1,), "dtype": th.uint8},
    }
    groups = {
        "agents": args.n_agents
    }
    preprocess = {
        "actions": ("actions_onehot", [OneHot(out_dim=args.n_actions)])
    }

    buffer = ReplayBuffer(scheme, groups, args.buffer_size, env_info["episode_limit"] + 1,
                          preprocess=preprocess,
                          device="cpu" if args.buffer_cpu_only else args.device)

    # Setup multiagent controller here
    mac = mac_REGISTRY[args.mac](buffer.scheme, groups, args)

    # Give runner the scheme
    runner.setup(scheme=scheme, groups=groups, preprocess=preprocess, mac=mac)

    # Learner
    learner = le_REGISTRY[args.learner](mac, buffer.scheme, logger, args)

    if args.use_cuda:
        learner.cuda()

    if args.checkpoint_path != "":

        timesteps = []
        timestep_to_load = 0

        if not os.path.isdir(args.checkpoint_path):
            logger.console_logger.info("Checkpoint directiory {} doesn't exist".format(args.checkpoint_path))
            return

        # Go through all files in args.checkpoint_path
        for name in os.listdir(args.checkpoint_path):
            full_name = os.path.join(args.checkpoint_path, name)
            # Check if they are dirs the names of which are numbers
            if os.path.isdir(full_name) and name.isdigit():
                timesteps.append(int(name))

        if args.load_step == 0:
            # choose the max timestep
            timestep_to_load = max(timesteps)
        else:
            # choose the timestep closest to load_step
            timestep_to_load = min(timesteps, key=lambda x: abs(x - args.load_step))

        model_path = os.path.join(args.checkpoint_path, str(timestep_to_load))

        logger.console_logger.info("Loading model from {}".format(model_path))
        learner.load_models(model_path)
        if getattr(args, "breakpoint_train", False):
            runner.t_env = timestep_to_load

        if args.evaluate or args.save_replay:
            evaluate_sequential(args, runner)
            return

    # start training
    episode = 0
    last_test_T = -args.test_interval - 1
    last_log_T = 0
    model_save_time = 0

    start_time = time.time()
    last_time = start_time

    logger.console_logger.info("Beginning training for {} timesteps".format(args.t_max))

    # normal marl algorithm, e.g. QMIX, should not have pretrain phase
    pretrain_phase = getattr(args, "pretrain", False)

    while runner.t_env <= args.t_max:
        # Run for a whole episode at a time
        episode_batch = runner.run(test_mode=False, pretrain_phase=pretrain_phase)
        buffer.insert_episode_batch(episode_batch)

        if buffer.can_sample(args.batch_size):
            # balance between parallel and episode run
            terminated = False
            for _run in range(runner.batch_size):
                episode_sample = buffer.sample(args.batch_size)

                # Truncate batch to only filled timesteps
                max_ep_t = episode_sample.max_t_filled()
                episode_sample = episode_sample[:, :max_ep_t]

                if episode_sample.device != args.device:
                    episode_sample.to(args.device)
                
                terminated = learner.train(episode_sample, runner.t_env, episode)
                if terminated:
                    break

            if terminated:
                if getattr(args, "only_repre_learning", False):
                    logger.console_logger.info("Only task repre learning!")
                    break
                else:
                    logger.console_logger.info("Finish pretrain and begin training for {} timesteps".format(args.t_max))
                    # Reset some properties in run.py, not need to modify episode, last_log_T, ...
                    pretrain_phase = False
                    start_time = time.time()
                    last_time = start_time
                    # Reset some properties about buffer and runner
                    buffer.clear()
                    runner.t_env = 0
                    continue
        
        # Only for rl training phase
        if not pretrain_phase:            
            # Execute test runs once in a while
            n_test_runs = max(1, args.test_nepisode // runner.batch_size)
            if (runner.t_env - last_test_T) / args.test_interval >= 1.0:

                logger.console_logger.info("t_env: {} / {}".format(runner.t_env, args.t_max))
                logger.console_logger.info("Estimated time left: {}. Time passed: {}".format(
                    time_left(last_time, last_test_T, runner.t_env, args.t_max), time_str(time.time() - start_time)))
                last_time = time.time()

                last_test_T = runner.t_env
                for _ in range(n_test_runs):
                    runner.run(test_mode=True)

            if args.save_model and (runner.t_env - model_save_time >= args.save_model_interval or model_save_time == 0):
                model_save_time = runner.t_env
                local_results_path = os.path.join(dirname(dirname(abspath(__file__))), "results")
                if args.env == "sc2":
                    save_path = os.path.join(local_results_path, args.env, args.env_args["map_name"], args.name, "models", args.unique_token, str(runner.t_env))
                else:
                    save_path = os.path.join(local_results_path, args.env, args.name, "models", args.unique_token, str(runner.t_env))
                os.makedirs(save_path, exist_ok=True)
                logger.console_logger.info("Saving models to {}".format(save_path))

                # learner should handle saving/loading -- delegate actor save/load to mac,
                # use appropriate filenames to do critics, optimizer states
                learner.save_models(save_path)

            episode += args.batch_size_run

            if (runner.t_env - last_log_T) >= args.log_interval:
                logger.log_stat("episode", episode, runner.t_env)
                logger.print_recent_stats()
                last_log_T = runner.t_env

    # close environment
    runner.close_env()
    logger.console_logger.info("Finished Training")


def args_sanity_check(config, _log):

    # set CUDA flags
    # config["use_cuda"] = True # Use cuda whenever possible!
    if config["use_cuda"] and not th.cuda.is_available():
        config["use_cuda"] = False
        _log.warning("CUDA flag use_cuda was switched OFF automatically because no CUDA devices are available!")

    if config["test_nepisode"] < config["batch_size_run"]:
        config["test_nepisode"] = config["batch_size_run"]
    else:
        config["test_nepisode"] = (config["test_nepisode"]//config["batch_size_run"]) * config["batch_size_run"]

    return config
