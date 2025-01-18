from pathlib import Path

class Config:
    BASE_DIR = Path(__file__).resolve().parent
    SECRET_KEY = 'dev'  # Change this in production
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{BASE_DIR}/instance/pos.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False