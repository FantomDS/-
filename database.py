from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import numpy as np

db = SQLAlchemy()

def init_db(app):
    """Инициализация базы данных"""
    db.init_app(app)
    with app.app_context():
        db.create_all()


class Article(db.Model):
    """Научная статья"""
    __tablename__ = 'articles'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    abstract = db.Column(db.Text)
    content = db.Column(db.Text)
    keywords = db.Column(db.Text)  # JSON список
    doi = db.Column(db.String(200), unique=True)
    url = db.Column(db.String(500))
    pdf_url = db.Column(db.String(500))
    
    source = db.Column(db.String(50))
    source_id = db.Column(db.String(100))
    
    published_date = db.Column(db.DateTime)
    indexed_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    language = db.Column(db.String(10), default='ru')
    citation_count = db.Column(db.Integer, default=0)
    download_count = db.Column(db.Integer, default=0)
    popularity_score = db.Column(db.Float, default=0.0)
    
    embedding = db.Column(db.LargeBinary)
    
    authors = db.relationship('ArticleAuthor', backref='article', lazy='dynamic',
                             cascade='all, delete-orphan')
    citations = db.relationship('Citation', 
                               foreign_keys='Citation.article_id',
                               backref='article', 
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    
    def get_embedding(self):
        if self.embedding:
            return np.frombuffer(self.embedding, dtype=np.float32)
        return None
    
    def set_embedding(self, emb):
        if isinstance(emb, np.ndarray):
            self.embedding = emb.astype(np.float32).tobytes()
            self.indexed_date = datetime.utcnow()
    
    def get_keywords(self):
        if self.keywords:
            try:
                return json.loads(self.keywords)
            except:
                return []
        return []
    
    def set_keywords(self, kw_list):
        if kw_list:
            self.keywords = json.dumps(kw_list, ensure_ascii=False)
        else:
            self.keywords = None
    
    def to_dict(self, include_embedding=False):
        authors_list = []
        for aa in self.authors:
            if aa.author:
                authors_list.append(aa.to_dict())
        
        similarity = getattr(self, 'similarity_score', None)
        
        data = {
            'id': self.id,
            'title': self.title,
            'summary': self.abstract[:300] + '...' if self.abstract and len(self.abstract) > 300 else (self.abstract or ''),
            'abstract': self.abstract,
            'keywords': self.get_keywords(),
            'doi': self.doi,
            'url': self.url,
            'source': self.source,
            'source_type': self._get_source_type(),
            'published_date': self.published_date.isoformat() if self.published_date else None,
            'language': self.language or 'ru',
            'citation_count': self.citation_count or 0,
            'authors': authors_list,
            'similarity_score': similarity
        }
        
        if include_embedding:
            emb = self.get_embedding()
            if emb is not None:
                data['embedding'] = emb.tolist()
        
        return data
    
    def _get_source_type(self):
        scientific_sources = ['openalex', 'semantic_scholar', 'crossref', 'doaj', 'core', 'arxiv', 'elibrary']
        return 'scientific' if self.source in scientific_sources else 'news'
    
    def __repr__(self):
        return f'<Article {self.id}: {self.title[:50]}>'


class Author(db.Model):
    """Автор научных статей"""
    __tablename__ = 'authors'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    affiliation = db.Column(db.String(500))
    email = db.Column(db.String(200))
    orcid = db.Column(db.String(50))
    h_index = db.Column(db.Integer, default=0)
    total_citations = db.Column(db.Integer, default=0)
    total_articles = db.Column(db.Integer, default=0)
    
    articles = db.relationship('ArticleAuthor', backref='author', lazy='dynamic',
                              cascade='all, delete-orphan')
    
    def to_dict(self):
        articles_list = []
        citations_list = []
        
        for aa in self.articles:
            if aa.article:
                articles_list.append(aa.article)
                citations_list.append(aa.article.citation_count or 0)
        
        total_art = len(articles_list)
        total_cit = sum(citations_list)
        
        sorted_citations = sorted(citations_list, reverse=True)
        h = 0
        for i, cit_count in enumerate(sorted_citations, 1):
            if cit_count >= i:
                h = i
            else:
                break
        
        return {
            'id': self.id,
            'name': self.name,
            'affiliation': self.affiliation,
            'orcid': self.orcid,
            'h_index': h,
            'total_citations': total_cit,
            'total_articles': total_art
        }
    
    def update_stats(self):
        articles_list = []
        citations_list = []
        
        for aa in self.articles:
            if aa.article:
                articles_list.append(aa.article)
                citations_list.append(aa.article.citation_count or 0)
        
        self.total_articles = len(articles_list)
        self.total_citations = sum(citations_list)
        
        sorted_citations = sorted(citations_list, reverse=True)
        h = 0
        for i, cit_count in enumerate(sorted_citations, 1):
            if cit_count >= i:
                h = i
            else:
                break
        self.h_index = h
        
        return self
    
    def __repr__(self):
        return f'<Author {self.id}: {self.name}>'


class ArticleAuthor(db.Model):
    """Связь статьи и автора"""
    __tablename__ = 'article_authors'
    
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('authors.id', ondelete='CASCADE'), nullable=False)
    position = db.Column(db.Integer)
    
    def to_dict(self):
        return {
            'name': self.author.name if self.author else 'Неизвестен',
            'author_id': self.author_id,
            'affiliation': self.author.affiliation if self.author else None,
            'position': self.position
        }
    
    def __repr__(self):
        return f'<ArticleAuthor: a={self.article_id}, au={self.author_id}>'


class Citation(db.Model):
    """Цитирования"""
    __tablename__ = 'citations'
    
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False)
    cited_article_id = db.Column(db.Integer, db.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False)
    citation_context = db.Column(db.Text)
    
    cited_article = db.relationship('Article', foreign_keys=[cited_article_id])
    
    def __repr__(self):
        return f'<Citation: {self.article_id} -> {self.cited_article_id}>'


class SearchQuery(db.Model):
    """История поисковых запросов"""
    __tablename__ = 'search_queries'
    
    id = db.Column(db.Integer, primary_key=True)
    search_query = db.Column(db.Text, nullable=False)  # ← переименовано с query
    results_count = db.Column(db.Integer)
    search_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_ip = db.Column(db.String(50))
    
    def to_dict(self):
        return {
            'id': self.id,
            'query': self.search_query,
            'results_count': self.results_count,
            'search_date': self.search_date.isoformat() if self.search_date else None
        }
    
    def __repr__(self):
        return f'<SearchQuery: {self.search_query[:50]}>'