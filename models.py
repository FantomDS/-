from database import db, Article, Author, ArticleAuthor, Citation, SearchQuery
from sqlalchemy import or_, func, desc
from datetime import datetime
import json
import numpy as np
import hashlib


class ScholarDatabase:
    """Менеджер базы данных для Russian Scholar"""
    
    def __init__(self):
        pass
    
    # =====================================================================
    #  ДОБАВЛЕНИЕ СТАТЕЙ
    # =====================================================================
    
    def add_article(self, data):
        """
        Добавление одной статьи в базу данных
        
        Args:
            data: словарь с данными статьи
            
        Returns:
            Article object
        """
        # Проверка дубликатов по DOI
        if data.get('doi'):
            existing = Article.query.filter_by(doi=data['doi']).first()
            if existing:
                return existing
        
        # Проверка дубликатов по URL
        if data.get('url'):
            existing = Article.query.filter_by(url=data['url']).first()
            if existing:
                return existing
        
        # Проверка дубликатов по заголовку
        existing = Article.query.filter_by(title=data['title']).first()
        if existing:
            return existing
        
        # Создаём статью
        article = Article(
            title=data['title'],
            abstract=data.get('abstract', ''),
            content=data.get('content', ''),
            doi=data.get('doi'),
            url=data.get('url'),
            pdf_url=data.get('pdf_url'),
            source=data.get('source', 'unknown'),
            source_id=data.get('source_id'),
            published_date=data.get('published_date'),
            language=data.get('language', 'ru'),
            citation_count=data.get('citation_count', 0),
            popularity_score=data.get('popularity_score', 0.0)
        )
        
        # Сохраняем ключевые слова
        article.set_keywords(data.get('keywords', []))
        
        db.session.add(article)
        db.session.flush()  # Получаем ID статьи
        
        # Добавляем авторов
        for i, author_data in enumerate(data.get('authors', [])):
            author = self._get_or_create_author(author_data)
            if author:
                # Создаём связь статьи с автором
                article_author = ArticleAuthor(
                    article_id=article.id,
                    author_id=author.id,
                    position=i + 1
                )
                db.session.add(article_author)
                
                # Обновляем статистику автора
                author.total_articles = (author.total_articles or 0) + 1
                author.total_citations = (author.total_citations or 0) + (data.get('citation_count', 0))
        
        db.session.commit()
        return article
    
    def _get_or_create_author(self, data):
        """
        Получить существующего автора или создать нового
        
        Args:
            data: словарь с данными автора {'name': '...', 'affiliation': '...'}
            
        Returns:
            Author object
        """
        name = data.get('name', '').strip()
        if not name:
            return None
        
        # Ищем автора по имени
        author = Author.query.filter_by(name=name).first()
        
        if not author:
            author = Author(
                name=name,
                affiliation=data.get('affiliation'),
                orcid=data.get('orcid'),
                total_articles=0,
                total_citations=0,
                h_index=0
            )
            db.session.add(author)
            db.session.flush()
        
        return author
    
    def add_articles_batch(self, articles_data):
        """
        Массовое добавление статей
        
        Args:
            articles_data: список словарей с данными статей
            
        Returns:
            int: количество добавленных статей
        """
        added = 0
        for data in articles_data:
            try:
                self.add_article(data)
                added += 1
                if added % 50 == 0:
                    db.session.commit()
                    print(f"  Сохранено: {added}")
            except Exception as e:
                print(f"  Ошибка сохранения статьи: {e}")
                continue
        
        db.session.commit()
        
        # Обновляем h-индекс для всех авторов
        print("  Обновление h-индекса авторов...")
        self._update_all_authors_h_index()
        
        return added
    
    def _update_all_authors_h_index(self):
        """Обновление h-индекса для всех авторов"""
        authors = Author.query.all()
        
        for author in authors:
            author.update_stats()
        
        db.session.commit()
        print(f"  Обновлено авторов: {len(authors)}")
    
    # =====================================================================
    #  ПОИСК СТАТЕЙ
    # =====================================================================
    
    def search_by_keywords(self, query, page=1, per_page=10, filters=None):
        """
        Поиск статей по ключевым словам (через SQL LIKE)
        
        Args:
            query: поисковый запрос
            page: номер страницы
            per_page: результатов на страницу
            filters: словарь с фильтрами
            
        Returns:
            dict с результатами поиска
        """
        search = f"%{query}%"
        
        q = Article.query.filter(
            or_(
                Article.title.ilike(search),
                Article.abstract.ilike(search),
                Article.keywords.ilike(search)
            )
        )
        
        # Применяем фильтры
        if filters:
            if filters.get('year_from'):
                try:
                    year = int(filters['year_from'])
                    q = q.filter(Article.published_date >= datetime(year, 1, 1))
                except:
                    pass
            
            if filters.get('year_to'):
                try:
                    year = int(filters['year_to'])
                    q = q.filter(Article.published_date <= datetime(year, 12, 31))
                except:
                    pass
            
            if filters.get('source'):
                q = q.filter_by(source=filters['source'])
            
            if filters.get('language'):
                q = q.filter_by(language=filters['language'])
            
            if filters.get('source_type'):
                q = q.filter_by(source=filters['source_type'])
        
        # Сортировка
        sort = filters.get('sort', 'relevance') if filters else 'relevance'
        if sort == 'date':
            q = q.order_by(desc(Article.published_date))
        elif sort == 'citations':
            q = q.order_by(desc(Article.citation_count))
        
        # Пагинация
        total = q.count()
        articles = q.offset((page - 1) * per_page).limit(per_page).all()
        
        return {
            'articles': [a.to_dict() for a in articles],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': max(1, (total + per_page - 1) // per_page)
        }
    
    def search_authors(self, query, limit=10):
        """
        Поиск авторов по имени
        
        Args:
            query: поисковый запрос (имя автора)
            limit: максимальное количество результатов
            
        Returns:
            list: список словарей с данными авторов
        """
        search = f"%{query}%"
        authors = Author.query.filter(
            Author.name.ilike(search)
        ).limit(limit).all()
        
        return [a.to_dict() for a in authors]
    
    def search_by_author(self, author_name, page=1, per_page=10, filters=None):
        """
        Поиск статей по имени автора
        
        Args:
            author_name: имя автора
            page: номер страницы
            per_page: результатов на страницу
            filters: словарь с фильтрами
            
        Returns:
            dict с результатами поиска
        """
        search = f"%{author_name}%"
        
        # Находим ID авторов
        authors = Author.query.filter(Author.name.ilike(search)).all()
        author_ids = [a.id for a in authors]
        
        if not author_ids:
            return {
                'articles': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'pages': 0
            }
        
        # Находим ID статей этих авторов
        article_authors = ArticleAuthor.query.filter(
            ArticleAuthor.author_id.in_(author_ids)
        ).all()
        article_ids = list(set(aa.article_id for aa in article_authors))
        
        if not article_ids:
            return {
                'articles': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'pages': 0
            }
        
        # Получаем статьи
        q = Article.query.filter(Article.id.in_(article_ids))
        
        # Применяем фильтры
        if filters:
            if filters.get('year_from'):
                try:
                    year = int(filters['year_from'])
                    q = q.filter(Article.published_date >= datetime(year, 1, 1))
                except:
                    pass
            
            if filters.get('year_to'):
                try:
                    year = int(filters['year_to'])
                    q = q.filter(Article.published_date <= datetime(year, 12, 31))
                except:
                    pass
        
        # Сортировка
        sort = filters.get('sort', 'date') if filters else 'date'
        if sort == 'date':
            q = q.order_by(desc(Article.published_date))
        elif sort == 'citations':
            q = q.order_by(desc(Article.citation_count))
        
        # Пагинация
        total = q.count()
        articles = q.offset((page - 1) * per_page).limit(per_page).all()
        
        return {
            'articles': [a.to_dict() for a in articles],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': max(1, (total + per_page - 1) // per_page)
        }
    
    # =====================================================================
    #  ПОЛУЧЕНИЕ ДАННЫХ
    # =====================================================================
    
    def get_article(self, article_id):
        """
        Получение статьи по ID
        
        Args:
            article_id: ID статьи
            
        Returns:
            dict или None
        """
        article = Article.query.get(article_id)
        if not article:
            return None
        
        data = article.to_dict()
        
        # Добавляем похожие статьи
        data['similar'] = self._get_similar_articles(article)
        
        # Добавляем цитирования
        citations_data = []
        for citation in article.citations:
            if citation.cited_article:
                citations_data.append(citation.cited_article.to_dict())
        data['citations'] = citations_data
        
        return data
    
    def _get_similar_articles(self, article, limit=5):
        """
        Получение похожих статей на основе эмбеддингов
        
        Args:
            article: объект Article
            limit: количество результатов
            
        Returns:
            list: список похожих статей
        """
        try:
            embedding = article.get_embedding()
            if embedding is None:
                return []
            
            if not isinstance(embedding, np.ndarray) or embedding.ndim != 1:
                return []
            
            from sklearn.metrics.pairwise import cosine_similarity
            
            query_emb = embedding.reshape(1, -1)
            
            # Получаем кандидатов
            candidates = Article.query.filter(
                Article.id != article.id,
                Article.embedding != None
            ).limit(100).all()
            
            results = []
            for cand in candidates:
                try:
                    cand_emb = cand.get_embedding()
                    if cand_emb is None or not isinstance(cand_emb, np.ndarray):
                        continue
                    if cand_emb.ndim != 1 or len(cand_emb) != len(embedding):
                        continue
                    
                    cand_emb_2d = cand_emb.reshape(1, -1)
                    sim = cosine_similarity(query_emb, cand_emb_2d)[0][0]
                    
                    result = cand.to_dict()
                    result['similarity_score'] = float(sim)
                    results.append(result)
                except Exception:
                    continue
            
            # Сортируем по схожести
            results.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            return results[:limit]
            
        except Exception as e:
            print(f"Ошибка получения похожих статей: {e}")
            return []
    
    def get_author(self, author_id):
        """
        Получение информации об авторе
        
        Args:
            author_id: ID автора
            
        Returns:
            dict или None
        """
        author = Author.query.get(author_id)
        if not author:
            return None
        
        # Обновляем статистику
        author.update_stats()
        db.session.commit()
        
        data = author.to_dict()
        
        # Собираем статьи автора
        articles = []
        for aa in author.articles:
            if aa.article:
                articles.append(aa.article.to_dict())
        
        # Сортируем по дате (новые сначала)
        articles.sort(key=lambda x: x.get('published_date', ''), reverse=True)
        data['articles'] = articles
        
        return data
    
    def get_unindexed_articles(self):
        """
        Получение статей без эмбеддингов
        
        Returns:
            list: список объектов Article
        """
        return Article.query.filter(Article.embedding == None).all()
    
    def get_recent_articles(self, limit=100):
        """
        Получение последних добавленных статей
        
        Args:
            limit: количество статей
            
        Returns:
            list: список объектов Article
        """
        return Article.query.order_by(
            Article.created_at.desc()
        ).limit(limit).all()
    
    # =====================================================================
    #  СТАТИСТИКА
    # =====================================================================
    
    def get_statistics(self):
        """
        Получение статистики базы данных
        
        Returns:
            dict с общей статистикой
        """
        total_articles = Article.query.count()
        total_authors = Author.query.count()
        total_citations = Citation.query.count()
        total_searches = SearchQuery.query.count()
        
        # Статистика по источникам
        sources = db.session.query(
            Article.source, func.count(Article.id)
        ).group_by(Article.source).all()
        
        # Статистика по годам
        years = db.session.query(
            func.strftime('%Y', Article.published_date).label('year'),
            func.count(Article.id)
        ).filter(
            Article.published_date != None
        ).group_by('year').order_by(desc('year')).limit(10).all()
        
        # Статистика по языкам
        languages = db.session.query(
            Article.language, func.count(Article.id)
        ).group_by(Article.language).all()
        
        # Статистика по типам
        scientific = Article.query.filter(
            Article.source.in_(['openalex', 'semantic_scholar', 'crossref', 'doaj', 'core', 'arxiv', 'elibrary'])
        ).count()
        
        news = total_articles - scientific
        
        return {
            'total_articles': total_articles,
            'total_authors': total_authors,
            'total_citations': total_citations,
            'total_searches': total_searches,
            'scientific_articles': scientific,
            'news_articles': news,
            'by_source': [{'name': s, 'count': c} for s, c in sources],
            'by_year': [{'year': y, 'count': c} for y, c in years],
            'by_language': [{'language': l, 'count': c} for l, c in languages]
        }
    
    # =====================================================================
    #  ИСТОРИЯ ПОИСКА
    # =====================================================================
    
    def save_search_query(self, query_text, results_count, user_ip=None):
        search_entry = SearchQuery(
            search_query=query_text,
            results_count=results_count,
            user_ip=user_ip
        )
        db.session.add(search_entry)
        db.session.commit()
    
    def get_recent_searches(self, limit=10):
        """
        Получение последних поисковых запросов
        
        Args:
            limit: количество запросов
            
        Returns:
            list: список словарей с запросами
        """
        searches = SearchQuery.query.order_by(
            desc(SearchQuery.search_date)
        ).limit(limit).all()
        
        return [s.to_dict() for s in searches]
    
    def get_popular_searches(self, limit=10):
        """
        Получение популярных поисковых запросов
        
        Args:
            limit: количество запросов
            
        Returns:
            list: список словарей с запросами
        """
        popular = db.session.query(
            SearchQuery.query, func.count(SearchQuery.id).label('count')
        ).group_by(
            SearchQuery.query
        ).order_by(
            desc('count')
        ).limit(limit).all()
        
        return [{'query': q, 'count': c} for q, c in popular]
    
    # =====================================================================
    #  УПРАВЛЕНИЕ БАЗОЙ
    # =====================================================================
    
    def delete_article(self, article_id):
        """
        Удаление статьи по ID
        
        Args:
            article_id: ID статьи
            
        Returns:
            bool: успешно ли удалено
        """
        article = Article.query.get(article_id)
        if article:
            db.session.delete(article)
            db.session.commit()
            return True
        return False
    
    def clear_database(self):
        """Полная очистка базы данных"""
        try:
            Citation.query.delete()
            ArticleAuthor.query.delete()
            SearchQuery.query.delete()
            Article.query.delete()
            Author.query.delete()
            db.session.commit()
            print("База данных очищена")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка очистки: {e}")
            return False
    
    def get_database_size(self):
        """
        Получение размера базы данных в записях
        
        Returns:
            dict с количеством записей в каждой таблице
        """
        return {
            'articles': Article.query.count(),
            'authors': Author.query.count(),
            'article_authors': ArticleAuthor.query.count(),
            'citations': Citation.query.count(),
            'search_queries': SearchQuery.query.count()
        }