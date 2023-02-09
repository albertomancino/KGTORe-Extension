from data_preprocessing import alibaba_preprocessing, lastfm_preprocessing
from email_notifier import email_sender

alibaba_data_folder = './data/alibaba'
lastfm_data_folder = './data/last_fm'

messages = 'preprocessing_message.txt'

if __name__ == '__main__':
    try:
        alibaba_preprocessing.run(data_folder=alibaba_data_folder)
        lastfm_preprocessing.run(data_folder=lastfm_data_folder)
        email_sender.send_email(messages=messages)
    except Exception as e:
        print(f'An error occurred. Exception {e}')
        print('Sending emails')
        email_sender.send_email(messages=messages, error=True, error_exception=e)
