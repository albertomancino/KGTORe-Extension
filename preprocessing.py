from data_preprocessing import alibaba_preprocessing
alibaba_data_folder = './data/alibaba'

if __name__ == '__main__':
    alibaba_preprocessing.run(data_folder=alibaba_data_folder)
