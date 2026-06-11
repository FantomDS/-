import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'russian-scholar-secret'
    
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{os.path.join(BASE_DIR, "data", "scholar.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    EMBEDDING_MODEL = 'paraphrase-multilingual-MiniLM-L12-v2'
    
    RESULTS_PER_PAGE = 10
    MAX_SEARCH_RESULTS = 100
    MIN_SIMILARITY_SCORE = 0.2
    
    # Источники научных статей
    SCIENTIFIC_SOURCES = {
        'cyberleninka': {
            'name': 'КиберЛенинка',
            'url': 'https://cyberleninka.ru',
            'type': 'scientific'
        },
        'elibrary': {
            'name': 'eLibrary',
            'url': 'https://elibrary.ru',
            'type': 'scientific'
        },
        'mathnet': {
            'name': 'Math-Net.Ru',
            'url': 'https://mathnet.ru',
            'type': 'scientific'
        },
        'arxiv_ru': {
            'name': 'ArXiv (русские статьи)',
            'url': 'https://arxiv.org',
            'type': 'scientific'
        }
    }