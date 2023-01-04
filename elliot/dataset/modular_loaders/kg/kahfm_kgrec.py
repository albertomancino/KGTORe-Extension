from types import SimpleNamespace
import typing as t
from os.path import splitext

import numpy as np
import pandas as pd

from elliot.dataset.modular_loaders.abstract_loader import AbstractLoader


class KAHFMLoader(AbstractLoader):
    def __init__(self, users: t.Set, items: t.Set, ns: SimpleNamespace, logger: object):
        self.logger = logger
        self.kg_path = getattr(ns, "kg_train", None)
        self.additive = getattr(ns, "additive", True)
        self.users = users
        self.items = items

        train_triples = pd.read_csv(self.kg_path, sep='\t', names=['uri', 'predicate', 'object'],
                                    dtype={'uri': str, 'predicate': str, 'object': str})

        self.triples = train_triples
        del train_triples


        # self.filter_triples()

        # # Filter items
        # self.triples = self.triples[self.triples["uri"].isin(self.mapping.values())]
        # # Filtering for missing values from https://doi.org/10.1007/978-3-030-30793-6_3 and https://doi.org/10.1145/2254129.2254168
        # n_mapped_subjects = self.triples["uri"].nunique()
        # self.triples = self.triples.groupby(['predicate', 'object']).filter(lambda x: (1 - len(x) / n_mapped_subjects) <= self.threshold).astype(str)
        # mapped_items = [str(uri) for uri in self.triples["uri"].unique()]
        self.mapping = {i: str(i) for i in self.items}
        # self.mapping = dict(zip(self.items, self.items))


    def get_mapped(self):
        return self.users, self.items

    def filter(self, users, items):
        self.users = self.users & users
        # self.mapping = {k: v for k, v in self.mapping.items() if k in items}
        self.items = self.items & items

    def create_namespace(self):
        ns = SimpleNamespace()
        ns.__name__ = "KAHFMLoader"

        # Compute features
        inverted_mapping = {v:k for k,v in self.mapping.items()}
        feature_list = list(self.triples.groupby(['predicate', 'object']).indices.keys())
        self.logger.info(f"Final KAHFM Features:\t{len(feature_list)}\tMapped items:\t{len(self.items)}")

        feature_index = {k: p for p, k in enumerate(feature_list)}
        self.triples["idxfeature"] = self.triples[['predicate', 'object']].set_index(['predicate', 'object']).index.map(
            feature_index)

        self.feature_map = self.triples.groupby("uri")["idxfeature"].apply(list).to_dict()
        self.feature_map = {inverted_mapping[k]: v for k, v in self.feature_map.items() if
                            k in inverted_mapping.keys()}

        self.features = list(set(feature_index.values()))
        self.private_features = {p: f for p, f in enumerate(self.features)}
        self.public_features = {v: k for k, v in self.private_features.items()}

        ns.object = self
        ns.__dict__.update(self.__dict__)
        return ns


    def read_triples(self, path: str) -> t.List[t.Tuple[str, str, str]]:
        triples = []

        tmp = splitext(path)
        ext = tmp[1] if len(tmp) > 1 else None

        with open(path, 'rt') as f:
            for line in f.readlines():
                if ext is not None and ext.lower() == '.tsv':
                    s, p, o = line.split('\t')
                else:
                    s, p, o = line.split()
                triples += [(s.strip(), p.strip(), o.strip())]
        return triples

    # def triples_to_vectors(self, triples: t.List[t.Tuple[str, str, str]],
    #                        entity_to_idx: t.Dict[str, int],
    #                        predicate_to_idx: t.Dict[str, int]) -> t.Tuple[np.ndarray, np.ndarray, np.ndarray]:
    #     Xs = np.array([entity_to_idx[s] for (s, p, o) in triples], dtype=np.int32)
    #     Xp = np.array([predicate_to_idx[p] for (s, p, o) in triples], dtype=np.int32)
    #     Xo = np.array([entity_to_idx[o] for (s, p, o) in triples], dtype=np.int32)
    #     return Xs, Xp, Xo

    # def load_mapping_file(self, mapping_file, separator='\t'):
    #     map = {}
    #     with open(mapping_file) as file:
    #         for line in file:
    #             line = line.rstrip("\n").split(separator)
    #             map[int(line[0])] = line[1]
    #     return map
    #
    # def filter_triples(self):
    #     # Filter triples
    #     self.triples = self.triples[self.triples["uri"].isin(self.mapping.values())]
    #     n_mapped_subjects = self.triples["uri"].nunique()
    #     self.triples = self.triples.groupby(['predicate', 'object']).filter(
    #         lambda x: (1 - len(x) / n_mapped_subjects) <= self.threshold).astype(str)
    #     mapped_items = [str(uri) for uri in self.triples["uri"].unique()]
    #     self.logger.info(f"Filtering operation: KAHFM Mapped items:\t{len(self.items)}")
    #     self.mapping = {k: v for k, v in self.mapping.items() if v in mapped_items}
