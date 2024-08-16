REGISTRY = {}

# normal controllers
from .basic_controller import BasicMAC
from .basic_dc_controller import BasicDCMAC
from .xtrans_controller import XTransMAC

REGISTRY["basic_mac"] = BasicMAC
REGISTRY["basic_dc_mac"] = BasicDCMAC
REGISTRY["xtrans_mac"] = XTransMAC


# some mutli-task controllers
from .multi_task import XTransMAC as MultiTaskXTransMAC

REGISTRY["mt_xtrans_mac"] = MultiTaskXTransMAC