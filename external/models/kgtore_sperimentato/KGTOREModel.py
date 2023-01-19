from abc import ABC

from .EdgeLayer import EdgeLayer
import torch
import torch_geometric
import numpy as np
import random
from torch_sparse import matmul
from .DecisionPaths import DecisionPaths


class KGTOREModel(torch.nn.Module, ABC):
    def __init__(self,
                 num_users,
                 num_items,
                 num_interactions,
                 learning_rate,
                 embed_k,
                 embed_f,
                 l_w,
                 proj_lr,
                 edges_lr,
                 n_layers,
                 edge_index,
                 edge_features,
                 random_seed,
                 name="KGTORE",
                 **kwargs
                 ):
        super().__init__()

        # set seed
        random.seed(random_seed)
        np.random.seed(random_seed)
        torch.manual_seed(random_seed)
        torch.cuda.manual_seed(random_seed)
        torch.cuda.manual_seed_all(random_seed)
        torch.backends.cudnn.deterministic = True

        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        self.num_users = num_users
        self.num_items = num_items
        self.num_interactions = num_interactions
        self.embed_k = embed_k
        self.embed_f = embed_f
        self.learning_rate = learning_rate
        self.projection_lr = proj_lr
        self.edges_lr = edges_lr
        self.l_w = l_w
        self.n_layers = n_layers
        self.weight_size_list = [self.embed_k] * (self.n_layers + 1)
        self.alpha = torch.tensor([1 / (k + 1) for k in range(len(self.weight_size_list))])
        self.edge_index = torch.tensor(edge_index, dtype=torch.int64)
        self.edge_features = edge_features
        self.edge_features.to(self.device)

        # ADDITIVE OPTIONS
        self.alfa = 0.1

        self.Gu = torch.nn.Parameter(
            torch.nn.init.xavier_normal_(torch.empty((self.num_users, self.embed_k))))
        self.Gu.to(self.device)
        self.Gi = torch.nn.Parameter(
            torch.nn.init.xavier_normal_(torch.empty((self.num_items, self.embed_k))))
        self.Gi.to(self.device)

        # features matrix (for edges)
        self.feature_dim = edge_features.size(1)
        self.F = torch.nn.Parameter(
            torch.nn.init.xavier_normal_(torch.empty((self.feature_dim, self.embed_f)))
        )
        self.F.to(self.device)

        self.projection = torch.nn.Linear(self.embed_f, 1)
        self.projection.to(self.device)

        propagation_network_list = []

        for layer in range(self.n_layers):
            propagation_network_list.append((EdgeLayer(), 'x, edge_index -> x'))

        self.propagation_network = torch_geometric.nn.Sequential('x, edge_index', propagation_network_list)
        self.propagation_network.to(self.device)
        self.softplus = torch.nn.Softplus()

        # self.optimizer = torch.optim.Adam(self.parameters(), lr=self.learning_rate)

        self.optimizer = torch.optim.Adam([self.Gu, self.Gi], lr=self.learning_rate)
        self.edges_optimizer = torch.optim.Adam([self.F], lr=self.edges_lr)
        self.projection_optimizer = torch.optim.Adam(self.projection.parameters(), lr=self.projection_lr)

    def propagate_embeddings(self, evaluate=False):
        edge_embeddings = matmul(self.edge_features, self.F.to(self.device))

        ego_embeddings = torch.cat((self.Gu.to(self.device), self.Gi.to(self.device)), 0)
        all_embeddings = [ego_embeddings]
        edge_embeddings = torch.cat([self.projection(edge_embeddings), self.projection(edge_embeddings)], dim=0)

        # user_embeddings_edge = torch.cat((self.Gu[self.edge_index[0][:self.num_interactions]], edge_embeddings), dim=1)
        # item_embeddings_edge = torch.cat((self.Gu[self.edge_index[1][:self.num_interactions] - self.num_users], edge_embeddings), dim=1)
        # edge_embeddings = torch.cat([self.projection(user_embeddings_edge), self.projection(item_embeddings_edge)], dim=0)

        for layer in range(0, self.n_layers):
            if evaluate:
                self.propagation_network.eval()
                with torch.no_grad():
                    all_embeddings += [list(
                        self.propagation_network.children()
                    )[layer](all_embeddings[layer].to(self.device), self.edge_index.to(self.device),
                             edge_embeddings.to(self.device))]
            else:
                all_embeddings += [list(
                    self.propagation_network.children()
                )[layer](all_embeddings[layer].to(self.device), self.edge_index.to(self.device),
                         edge_embeddings.to(self.device))]

        if evaluate:
            self.propagation_network.train()

        all_embeddings = sum([all_embeddings[k] * self.alpha[k] for k in range(len(all_embeddings))])
        gu, gi = torch.split(all_embeddings, [self.num_users, self.num_items], 0)

        return gu, gi

    def forward(self, inputs, **kwargs):
        gu, gi = inputs
        gamma_u = torch.squeeze(gu).to(self.device)
        gamma_i = torch.squeeze(gi).to(self.device)
        # b_i = torch.squeeze(bi).to(self.device)
        # xui = torch.sum(gamma_u * gamma_i, 1) + b_i
        xui = torch.sum(gamma_u * gamma_i, 1)

        return xui

    def predict(self, gu, gi, **kwargs):
        return torch.matmul(gu.to(self.device), torch.transpose(gi.to(self.device), 0, 1))  # + self.bi

    def train_step(self, batch):

        gu, gi = self.propagate_embeddings()
        user, pos, neg = batch
        xu_pos = self.forward(inputs=(gu[user[:, 0]], gi[pos[:, 0]]))
        xu_neg = self.forward(inputs=(gu[user[:, 0]], gi[neg[:, 0]]))
        difference = torch.clamp(xu_pos - xu_neg, -80.0, 1e8)
        bpr_loss = torch.sum(self.softplus(-difference))
        reg_loss = self.l_w * (torch.norm(self.Gu, 2) +
                               torch.norm(self.Gi, 2))
        loss = bpr_loss + reg_loss

        # edge_embeddings = matmul(self.edge_features, self.F.to(self.device))
        # edge_embeddings = torch.cat([self.projection(edge_embeddings), self.projection(edge_embeddings)], dim=0)

        proj_reg_loss = self.l_w * (
                torch.norm(self.projection.weight, 2) +
                torch.norm(self.projection.bias, 2))
        loss_proj = bpr_loss + proj_reg_loss

        # independence loss over the features within the same path
        if self.alfa > 0:
            assert self.alfa <= 1
            n_edges = self.edge_features.size(0)
            n_selected_edges = int(n_edges * 0.01)
            selected_edges = random.sample(list(range(n_edges)), n_selected_edges)
            ind_loss = [torch.abs(torch.corrcoef(self.F[self.edge_features[e].storage._col])).sum() - len(
                self.edge_features[e].storage._col) for e in selected_edges]
            ind_loss = sum(ind_loss) / n_selected_edges + self.l_w * (torch.norm(self.F, 2))
            # loss = self.alfa * ind_loss + (1-self.alfa) * bpr_loss + reg_loss

        self.optimizer.zero_grad()
        self.projection_optimizer.zero_grad()
        self.edges_optimizer.zero_grad()
        loss.backward(retain_graph=True)
        if self.alfa > 0:
            ind_loss.backward(retain_graph=True)
        loss_proj.backward()
        self.optimizer.step()
        self.projection_optimizer.step()
        self.edges_optimizer.step()

        return loss.detach().cpu().numpy()

    def get_top_k(self, preds, train_mask, k=100):
        return torch.topk(torch.where(torch.tensor(train_mask).to(self.device), preds.to(self.device),
                                      torch.tensor(-np.inf).to(self.device)), k=k, sorted=True)