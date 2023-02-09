import smtplib, ssl
from email.message import EmailMessage

DATA_PATH = './mail_sender_info.txt'
MESSAGE_PATH = './message.txt'

PORT = 465  # For SSL
SMPT_SERVER = "smtp.gmail.com"


def read_data(path):
    senders = []
    receivers = []
    with open(path, 'r') as file:
        for row in file.readlines():
            tokens = row.split('\t')
            role = tokens[0]
            if role == 'receiver':
                receivers.append(tokens[1].replace('\n', ''))
            elif role == 'sender':
                senders.append({
                    'mail': tokens[1],
                    'pass': tokens[2].replace('\n', '')
                })
    return senders, receivers


def read_message(path):
    messages = []
    with open(path, 'r') as file:
        for row in file.readlines():
            tokens = row.split('\t')
            role = tokens[0]
            messages.append({
                'role': role,
                'subject': tokens[1],
                'text': tokens[2].replace('\n', '')
            })
    return messages


def send_email(senders=None, receivers=None, messages=None):
    if senders is None:
        senders, _ = read_data(DATA_PATH)
    if receivers is None:
        _, receivers = read_data(DATA_PATH)

    if messages is None:
        messages = read_message(MESSAGE_PATH)

    for sender in senders:
        for receiver in receivers:
            for message in messages:
                role = message['role']
                if role == 'all' or role == receiver:
                    sender_mail = sender['mail']
                    print(f'sending message from {sender_mail} to {receiver}')
                    context = ssl.create_default_context()

                    message_obj = EmailMessage()
                    message_obj['Subject'] = message['subject']
                    message_obj['From'] = sender_mail
                    message_obj['To'] = receiver
                    message_obj.set_content(message['text'])

                    try:
                        with smtplib.SMTP_SSL(SMPT_SERVER, PORT, context=context) as server:
                            server.login(sender_mail, sender['pass'])
                            server.send_message(message_obj)
                        print(f'email from {sender_mail} to {receiver} sent')
                    except:
                        print(f'an error occurred while sending an email from {sender_mail} to {receiver} sent')


send_email(messages=[{'role': 'all',
                      'subject': 'tutto rotto',
                      'text': 'l\'esperimento è andato male'}])

