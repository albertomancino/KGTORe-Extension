from data_preprocessing import alibaba_preprocessing, lastfm_preprocessing
alibaba_data_folder = './data/alibaba'
lastfm_data_folder = './data/last_fm'

if __name__ == '__main__':
    alibaba_preprocessing.run(data_folder=alibaba_data_folder)
    lastfm_preprocessing.run(data_folder=lastfm_data_folder)
