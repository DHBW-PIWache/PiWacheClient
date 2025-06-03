import configparser
import os

config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(__file__), '/home/berry/PiWacheClient/config.properties')
print(f"Lade Config von: {config_path}")
read_files = config.read(config_path)
print(f"Geladene Dateien: {read_files}")

def get(key, default=None):
    return config['DEFAULT'].get(key, default)