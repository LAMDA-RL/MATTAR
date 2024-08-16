REGISTRY = {}

# normal learner
from .q_learner import QLearner
from .dc_learner import DCLearner
from .xtrans_learner import XTransLearner

REGISTRY["q_learner"] = QLearner
REGISTRY["dc_learner"] = DCLearner
REGISTRY["xtrans_learner"] = XTransLearner


# some multi-task learner
from .multi_task import XTransLearner as MultiTaskXTransLearner

REGISTRY["mt_xtrans_learner"] = MultiTaskXTransLearner