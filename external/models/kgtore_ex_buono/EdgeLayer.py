from abc import ABC

from torch_geometric.nn import MessagePassing
from torch_geometric.utils import degree, add_self_loops
from torch.nn import Linear, Parameter
import torch

from torch_sparse import SparseTensor, matmul


class EdgeLayer(MessagePassing, ABC):
    def __init__(self, alpha, beta, normalize=True):
        super(EdgeLayer, self).__init__(aggr='add')
        self.normalize = normalize
        self.alpha = alpha
        self.beta = beta
        # self.lin = Linear(64, 64, bias=False)
        # self.bias = Parameter(torch.nn.init.xavier_normal_(torch.empty(64)))
        # self.bias = torch.nn.Parameter(torch.nn.init.xavier_normal_(torch.empty(1, 64)))

    def forward(self, x, edge_index, edge_attr):

        # x = self.lin(x)
        if self.normalize:
            row, col = edge_index
            deg = degree(col, x.size(0), dtype=x.dtype)
            deg_inv_sqrt = deg.pow(-0.5)
            deg_inv_sqrt[deg_inv_sqrt == float('inf')] = 0
            norm = deg_inv_sqrt[row] * deg_inv_sqrt[col]
            return self.propagate(edge_index, x=x, norm=norm, edge_attr=edge_attr)# + self.bias
        else:
            return self.propagate(edge_index, x=x, edge_attr=edge_attr)# + self.bias

    def message(self, x_j, edge_attr):
        num_trans = x_j.shape[0] // 2
        x_j[:num_trans] = x_j[:num_trans] * self.beta
        x_j[num_trans:] = x_j[num_trans:] * self.alpha
        return edge_attr + x_j

    def message_and_aggregate(self, adj_t, x):
        return matmul(adj_t, x, reduce=self.aggr)




from torch import Tensor
from torch_sparse import SparseTensor, matmul

from torch_geometric.nn.conv import MessagePassing
from torch_geometric.nn.conv.gcn_conv import gcn_norm
from torch_geometric.typing import Adj, OptTensor


class LGConv(MessagePassing):
    r"""The Light Graph Convolution (LGC) operator from the `"LightGCN:
    Simplifying and Powering Graph Convolution Network for Recommendation"
    <https://arxiv.org/abs/2002.02126>`_ paper

    .. math::
        \mathbf{x}^{\prime}_i = \sum_{j \in \mathcal{N}(i)}
        \frac{e_{j,i}}{\sqrt{\deg(i)\deg(j)}} \mathbf{x}_j

    Args:
        normalize (bool, optional): If set to :obj:`False`, output features
            will not be normalized via symmetric normalization.
            (default: :obj:`True`)
        **kwargs (optional): Additional arguments of
            :class:`torch_geometric.nn.conv.MessagePassing`.

    Shapes:
        - **input:**
          node features :math:`(|\mathcal{V}|, F)`,
          edge indices :math:`(2, |\mathcal{E}|)`,
          edge weights :math:`(|\mathcal{E}|)` *(optional)*
        - **output:** node features :math:`(|\mathcal{V}|, F)`
    """
    def __init__(self, alpha, beta, normalize: bool = True, **kwargs):
        kwargs.setdefault('aggr', 'add')
        super().__init__(**kwargs)
        self.alpha = alpha
        self.beta = beta
        self.normalize = normalize

    def reset_parameters(self):
        pass

    def forward(self, x: Tensor, edge_index: Adj,
                edge_attr: OptTensor = None) -> Tensor:

        if self.normalize and isinstance(edge_index, Tensor):
            out = gcn_norm(edge_index, None, x.size(self.node_dim),
                           add_self_loops=False, flow=self.flow, dtype=x.dtype)
            edge_index, edge_weight = out
        elif self.normalize and isinstance(edge_index, SparseTensor):
            edge_index = gcn_norm(edge_index, None, x.size(self.node_dim),
                                  add_self_loops=False, flow=self.flow,
                                  dtype=x.dtype)

        # propagate_type: (x: Tensor, edge_weight: OptTensor)
        return self.propagate(edge_index, x=x, edge_weight=edge_weight, edge_attr=edge_attr,
                              size=None)

    def message(self, x_j: Tensor, edge_weight, edge_attr: OptTensor) -> Tensor:
        num_trans = x_j.shape[0] // 2
        x_j[:num_trans] = x_j[:num_trans] * self.beta
        x_j[num_trans:] = x_j[num_trans:] * self.alpha
        return edge_attr + torch.mul(x_j, edge_weight.reshape(-1, 1))

    def message_and_aggregate(self, adj_t: SparseTensor, x: Tensor) -> Tensor:
        return matmul(adj_t, x, reduce=self.aggr)