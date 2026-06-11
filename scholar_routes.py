from flask import Blueprint, render_template, request, jsonify
import traceback

scholar = Blueprint('scholar', __name__)

def create_scholar_routes(app, search_engine, sdb, embedding_service):
    
    @app.route('/')
    def index():
        """Главная страница"""
        stats = sdb.get_statistics()
        return render_template('index.html', stats=stats)
    
    @app.route('/search')
    def search():
        """Страница результатов поиска"""
        query = request.args.get('q', '')
        page = int(request.args.get('page', 1))
        sort = request.args.get('sort', 'relevance')
        year_from = request.args.get('year_from')
        year_to = request.args.get('year_to')
        source = request.args.get('source')
        
        if not query:
            return render_template('search.html', query='', results=None)
        
        filters = {
            'sort': sort,
            'year_from': year_from,
            'year_to': year_to,
            'source': source
        }
        
        results = search_engine.hybrid_search(query, page=page, per_page=10, filters=filters)
        
        return render_template('search.html', query=query, results=results, filters=filters)
    
    @app.route('/api/search', methods=['POST'])
    def api_search():
        """API поиска"""
        try:
            data = request.get_json()
            query = data.get('q', '').strip()
            page = data.get('page', 1)
            filters = data.get('filters', {})
            
            if not query:
                return jsonify({'error': 'Пустой запрос'}), 400
            
            results = search_engine.hybrid_search(query, page=page, filters=filters)
            results['search_time_ms'] = int(results.get('search_time', 0) * 1000)
            
            return jsonify(results)
            
        except Exception as e:
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/article/<int:article_id>')
    def article(article_id):
        """Страница статьи"""
        article_data = sdb.get_article(article_id)
        if not article_data:
            return "Статья не найдена", 404
        return render_template('article.html', article=article_data)
    
    @app.route('/author/<int:author_id>')
    def author(author_id):
        """Страница автора"""
        author_data = sdb.get_author(author_id)
        if not author_data:
            return "Автор не найден", 404
        return render_template('author.html', author=author_data)
    
    @app.route('/api/stats')
    def api_stats():
        """API статистики"""
        stats = sdb.get_statistics()
        metrics = search_engine.get_metrics()
        stats['search_metrics'] = metrics
        return jsonify(stats)
    
    return app