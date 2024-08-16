REGISTRY = {}

# normal agents
from .rnn_agent import RNNAgent
from .sota_agent import SotaAgent
from .sotax_agent import SotaXAgent

REGISTRY["rnn"] = RNNAgent
REGISTRY["sota"] = SotaAgent
REGISTRY["sotax"] = SotaXAgent

# multi-task agents
from .multi_task import AllyUnionRNNAgent as MultiTaskAllyUnionRNNAgent
from .multi_task import SotaXAgent as MultiTaskSotaXAgent
from .multi_task import SotaAgent as MultiTaskSotaAgent

REGISTRY["mt_ally_union_rnn"] = MultiTaskAllyUnionRNNAgent
REGISTRY["mt_sotax"] = MultiTaskSotaXAgent
REGISTRY["mt_sota"] = MultiTaskSotaAgent