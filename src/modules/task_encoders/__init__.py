#### encoder
ENC_REGISTRY = {}
## single task
from .encoders import AttnEncoder
from .encoders import PoolingEncoder
ENC_REGISTRY["attn"] = AttnEncoder
ENC_REGISTRY["pooling"] = PoolingEncoder
## multi task
from .encoders import MultiTaskPoolingEncoder
ENC_REGISTRY["mt_pooling"] = MultiTaskPoolingEncoder

#### decoder
DEC_REGISTRY = {}
from .decoders import MLPDecoder
DEC_REGISTRY["mlp"] = MLPDecoder
