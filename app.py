from flask import Flask
from config import Config
from database import init_db
from models import ScholarDatabase
from embedding_service import EmbeddingService
from search_engine import ScholarSearchEngine
from parser_service import ScholarParser
from scholar_routes import create_scholar_routes
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    os.makedirs(os.path.join(app.config['BASE_DIR'], 'data'), exist_ok=True)
    
    init_db(app)
    
    with app.app_context():
        sdb = ScholarDatabase()
        embedding_service = EmbeddingService(app.config['EMBEDDING_MODEL'])
        search_engine = ScholarSearchEngine(embedding_service)
        
        app.sdb = sdb
        app.embedding_service = embedding_service
        app.search_engine = search_engine
        
        # Индексация новых статей
        unindexed = len(sdb.get_unindexed_articles())
        if unindexed > 0:
            print(f"Индексация {unindexed} статей...")
            embedding_service.index_articles()
    
    app = create_scholar_routes(app, search_engine, sdb, embedding_service)
    
    return app

if __name__ == '__main__':
    app = create_app()
    print("\n" + "=" * 50)
    print("Russian Scholar - поиск научных статей")
    print("=" * 50)
    print("\nОткройте http://localhost:5000")
    print("\nДля сбора базы данных:")
    print("python scripts/build_scholar_db.py")
    print("=" * 50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)