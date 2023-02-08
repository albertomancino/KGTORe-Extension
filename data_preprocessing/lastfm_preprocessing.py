import os.path

from data_preprocessing.filters.dataset import Splitter, UserItemIterativeKCore
from data_preprocessing.filters import load_kg, load_dataset, load_linking, store_dataset
from data_preprocessing.filters.knowledge import LinkingCleaning, ItemFeatures, KGDatasetAlignment, DatasetKGAlignment

dataset_relative_path = 'dataset.tsv'
kg_relative_path = 'knowledge/kg.tsv'
linking_relative_path = 'knowledge/linking.tsv'


def run(data_folder):
    print('\n***** last-fm data preparation *****\n'.upper())
    dataset_path = os.path.join(data_folder, dataset_relative_path)
    kg_path = os.path.join(data_folder, kg_relative_path)
    linking_path = os.path.join(data_folder, linking_relative_path)

    kg = load_kg(kg_path)
    dataset = load_dataset(dataset_path)
    linking = load_linking(linking_path)

    kwargs = {
        'kg': kg,
        'dataset': dataset,
        'linking': linking,
        'core': 10
    }

    # item-entity linking cleaning
    alignment = LinkingCleaning(linking=linking)
    kwargs.update(alignment.filter())
    del alignment

    # iterative user-item k-core
    kcore = UserItemIterativeKCore(**kwargs)
    kwargs.update(kcore.filter())
    del kcore

    # kg dataset alignment (check missing items/entities)
    kgdata_align = KGDatasetAlignment(**kwargs)
    kwargs.update(kgdata_align.filter())
    del kgdata_align

    datakg_align = DatasetKGAlignment(**kwargs)
    kwargs.update(datakg_align.filter())
    del datakg_align

    kgflex_item_features = ItemFeatures(**kwargs)
    store_dataset(kgflex_item_features.filter()['item_features'],
                  folder=os.path.join(data_folder, 'kgflex'),
                  name='item_features',
                  message='item features')
    del kgflex_item_features

    print(f'\nFinal transactions: {len(kwargs["dataset"])}')
    store_dataset(data=kwargs["dataset"],
                  folder=data_folder,
                  name='dataset',
                  message='dataset')

    print('\nThere will be the splitting...')

    splitter = Splitter(data=kwargs["dataset"],
                        test_ratio=0.2,
                        val_ratio=0.1)
    splitting_results = splitter.filter()
    print(f'Final training set transactions: {len(splitting_results["train"])}')
    print(f'Final test set transactions: {len(splitting_results["test"])}')
    print(f'Final validation set transactions: {len(splitting_results["val"])}')

    store_dataset(data=splitting_results["train"],
                  folder=data_folder,
                  name='train',
                  message='training set')

    store_dataset(data=splitting_results["test"],
                  folder=data_folder,
                  name='test',
                  message='test set')

    store_dataset(data=splitting_results["val"],
                  folder=data_folder,
                  name='val',
                  message='validation set')

