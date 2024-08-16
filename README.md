# MATTAR: Multi-Agent Policy Transfer via Task Relationship Modeling

This is the official code repository for ["Multi-Agent Policy Transfer via Task Relationship Modeling"](https://www.sciengine.com/SCIS/doi/10.1007/s11432-023-3862-1;JSESSIONID=09c232b0-25d2-41bb-bf16-d945341f9a24).

## Environment Installation Instructions

This project relies on the StarCraft II Multi-Agent Challenge (SMAC) environment. To install the necessary StarCraft II engine and interface packages, execute the following command in the project root directory:

```shell
bash install_sc2.sh
```

This command will download SC2 to the `3rdparty` directory and set up some basic StarCraft map files. Afterward, you need to set the `SC2PATH` environment variable in your system:

```bash
export SC2PATH=[SC2 download directory, e.g., "/abc/xyz/3rdparty/StarCraftII"]
```

Once the StarCraft II environment is installed, use `conda` to set up the project's Python environment:

```bash
conda create -n pymarl python=3.7 -y
conda activate pymarl
conda install pytorch torchvision torchaudio cudatoolkit=10.2 -c pytorch -y
pip install sacred numpy scipy matplotlib seaborn pyyaml pygame pytest probscale imageio snakeviz tensorboard-logger tensorboard tensorboardx sympy PyYAML==5.4.1
```

After completing the above installations, you need to install the `qplex_smac` package within the project directory using `pip`:

```shell
pip install -e qplex-smac
```

## Adding New StarCraft Maps

This project supplements the default StarCraft maps in the SMAC environment with some new tasks. These maps are bundled in the `new_maps.zip` file. Please extract the archive and transfer the files to the corresponding map directory within your `SC2PATH`.

## Running the Program

### Single-Task Learning

To run the MATTAR algorithm for single-task learning, execute the following command:

```shell
python3 src/main.py --config=mattar --env-config=[Env name] with env_args.map_name=[Map name]
```

Here, set `Env name` to `sc2` and `Map name` to the StarCraft map task you wish to train.

### Multi-Task Learning

To run the MATTAR algorithm for multi-task learning, execute the following command:

```shell
python3 src/main.py --config=mattar_train_beta --task-config=[Task name]
```

Here, `Task name` refers to the multi-task learning configuration, specifying the set of tasks for training. Supported configurations include `marine_battle`, `stalkers_and_zealots`, and `MMM`. If you wish to modify or add multi-task learning configurations, please update or add files in the `./src/config/tasks` directory.

We provide models trained on the `MMM` and `sz` series tasks in the `results/store` and `outputs/store` directories.

### Policy Generalization Testing and Policy Transfer Training

To run the MATTAR algorithm for policy generalization testing, execute the following command:

```shell
python3 src/main.py --config=mattar_test_beta --task-config=[Task name] --map_name=[Map name] --transfer_training=False --few_shot_adaptation=True --checkpoint_path=[checkpoint_path] --load_repre_dir=[load_repre_dir]
```

To run the MATTAR algorithm for policy transfer training, execute the following command:

```shell
python3 src/main.py --config=mattar_test_beta --task-config=[Task name] --map_name=[Map name] --transfer_training=True --few_shot_adaptation=True --checkpoint_path=[checkpoint_path] --load_repre_dir=[load_repre_dir]
```

In these commands, `checkpoint_path` is the path to the saved policy model, and `load_repre_dir` is the path to the saved source task representation vectors.