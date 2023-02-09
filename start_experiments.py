from elliot.run import run_experiment
from email_notifier import email_sender
import argparse

parser = argparse.ArgumentParser(description="Run sample main.")
parser.add_argument('--config', type=str, default='movielens_best_kgtore')
parser.add_argument('--email', type=str, default='')
args = parser.parse_args()

email_reference = args.email
senders, receivers, messages = None, None, None
if email_reference:
    senders = '_'.join([email_reference, 'info.txt'])
    receivers = '_'.join([email_reference, 'info.txt'])
    messages = '_'.join([email_reference, 'message.txt'])

try:
    run_experiment(f"config_files/{args.config}.yml")
    email_sender.send_email(senders=senders, receivers=receivers, messages=messages)
except Exception as e:
    print(f'An error occurred. Exception {e}')
    print('Sending emails')
    email_sender.send_email(senders=senders, receivers=receivers, messages=messages, error=True, error_exception=e)
