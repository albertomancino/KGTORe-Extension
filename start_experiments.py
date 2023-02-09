from elliot.run import run_experiment
from email_notify import email_sender
import argparse

parser = argparse.ArgumentParser(description="Run sample main.")
parser.add_argument('--config', type=str, default='movielens_best_kgtore')
args = parser.parse_args()

try:
    run_experiment(f"config_files/{args.config}.yml")
    email_sender.send_email()
except Exception as e:
    email_sender.send_email(messages=[{'role': 'all',
                                       'subject': 'tutto rotto',
                                       'text': 'l\'esperimento è andato male'}])
