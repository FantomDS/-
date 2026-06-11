#!/usr/bin/env python3
"""Обновление статистики всех авторов"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

def update_stats():
    app = create_app()
    
    with app.app_context():
        from database import db, Author, ArticleAuthor, Article
        
        print("Обновление статистики авторов...")
        
        authors = Author.query.all()
        updated = 0
        
        for author in authors:
            # Собираем статьи автора
            article_ids = [aa.article_id for aa in author.articles]
            articles = Article.query.filter(Article.id.in_(article_ids)).all()
            
            # Обновляем метрики
            author.total_articles = len(articles)
            author.total_citations = sum(a.citation_count or 0 for a in articles)
            
            # Вычисляем h-индекс
            citations = sorted(
                [a.citation_count or 0 for a in articles], 
                reverse=True
            )
            h = 0
            for i, c in enumerate(citations, 1):
                if c >= i:
                    h = i
                else:
                    break
            author.h_index = h
            
            updated += 1
            
            if updated % 100 == 0:
                db.session.commit()
                print(f"  Обновлено: {updated}/{len(authors)}")
        
        db.session.commit()
        print(f"Обновлено авторов: {updated}")
        
        # Проверка
        sample = Author.query.limit(5).all()
        for a in sample:
            print(f"  {a.name}: {a.total_articles} ст., {a.total_citations} цит., h={a.h_index}")

if __name__ == '__main__':
    update_stats()