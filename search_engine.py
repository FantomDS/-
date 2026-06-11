import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from database import Article
from models import ScholarDatabase
import time

class ScholarSearchEngine:
    def __init__(self, embedding_service):
        self.embedding_service = embedding_service
        self.sdb = ScholarDatabase()
        self.metrics = {'searches': 0, 'total_time': 0.0}
    
    def semantic_search(self, query_text, top_k=10, min_score=0.2, filters=None):
        """Семантический поиск статей"""
        start = time.time()
        self.metrics['searches'] += 1
        
        # Создаем эмбеддинг запроса
        query_emb = self.embedding_service.create_embedding(query_text)
        if query_emb is None:
            return self.sdb.search_by_keywords(query_text, per_page=top_k, filters=filters)
        
        # Получаем проиндексированные статьи
        q = Article.query.filter(Article.embedding != None)
        if filters:
            if filters.get('source'):
                q = q.filter_by(source=filters['source'])
            if filters.get('year_from'):
                q = q.filter(Article.published_date >= f"{filters['year_from']}-01-01")
        
        candidates = q.limit(500).all()
        
        # Вычисляем схожесть
        results = []
        query_emb_2d = query_emb.reshape(1, -1)
        
        for article in candidates:
            emb = article.get_embedding()
            if emb is not None:
                sim = cosine_similarity(query_emb_2d, emb.reshape(1, -1))[0][0]
                if sim >= min_score:
                    result = article.to_dict()
                    result['similarity_score'] = float(sim)
                    results.append(result)
        
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        elapsed = time.time() - start
        self.metrics['total_time'] += elapsed
        
        total = len(results)
        pages = (total + top_k - 1) // top_k
        
        return {
            'articles': results[:top_k],
            'total': total,
            'page': 1,
            'per_page': top_k,
            'pages': pages,
            'search_time': elapsed,
            'search_type': 'semantic'
        }
    
    def hybrid_search(self, query_text, page=1, per_page=10, filters=None):
        """Гибридный поиск (семантический + ключевые слова)"""
        # Семантический поиск
        semantic = self.semantic_search(query_text, top_k=50, filters=filters)
        
        # Поиск по ключевым словам
        keyword = self.sdb.search_by_keywords(query_text, per_page=50, filters=filters)
        
        # Объединение результатов
        seen_ids = set()
        combined = []
        
        for article in semantic.get('articles', []):
            if article['id'] not in seen_ids:
                seen_ids.add(article['id'])
                article['search_type'] = 'semantic'
                combined.append(article)
        
        for article in keyword.get('articles', []):
            if article['id'] not in seen_ids:
                seen_ids.add(article['id'])
                article['similarity_score'] = 0.3
                article['search_type'] = 'keyword'
                combined.append(article)
        
        # Сортировка
        combined.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
        
        total = len(combined)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        self.sdb.save_search_query(query_text, total)
        
        return {
            'articles': combined[start_idx:end_idx],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page,
            'search_time': self.metrics.get('total_time', 0),
            'search_type': 'hybrid'
        }
    
    def get_metrics(self):
        return {
            **self.metrics,
            'avg_time': self.metrics['total_time'] / self.metrics['searches']
            if self.metrics['searches'] > 0 else 0
        }