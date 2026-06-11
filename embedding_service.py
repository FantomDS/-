from sentence_transformers import SentenceTransformer
import numpy as np
from database import db

class EmbeddingService:
    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        print(f"Загрузка модели: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        print(f"Размерность эмбеддинга: {self.dimension}")
    
    def create_embedding(self, text):
        if not text or len(text.strip()) < 10:
            return None
        text = text[:2000] if len(text) > 2000 else text
        return self.model.encode([text])[0].astype(np.float32)
    
    def create_article_embedding(self, article):
        """Создание эмбеддинга из заголовка и аннотации"""
        text = f"{article.title}. {article.abstract or ''}"
        return self.create_embedding(text)
    
    def index_articles(self):
        """Индексация всех статей без эмбеддингов"""
        from models import ScholarDatabase
        sdb = ScholarDatabase()
        articles = sdb.get_unindexed_articles()
        
        indexed = 0
        for article in articles:
            try:
                emb = self.create_article_embedding(article)
                if emb is not None:
                    article.set_embedding(emb)
                    indexed += 1
                    if indexed % 100 == 0:
                        db.session.commit()
                        print(f"  Проиндексировано: {indexed}")
            except Exception as e:
                print(f"  Ошибка: {e}")
                continue
        
        db.session.commit()
        return indexed