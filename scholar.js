/**
 * Russian Scholar - основной JavaScript файл
 */

document.addEventListener('DOMContentLoaded', function() {
    initSearchForm();
    initFilters();
    highlightSearchTerms();
});

/**
 * Инициализация поисковой формы
 */
function initSearchForm() {
    const searchForm = document.querySelector('form[action="/search"]');
    const searchInput = document.querySelector('input[name="q"]');
    
    if (searchInput) {
        // Автофокус на поле поиска
        searchInput.focus();
        
        // Обработка отправки формы
        if (searchForm) {
            searchForm.addEventListener('submit', function(e) {
                const query = searchInput.value.trim();
                if (!query) {
                    e.preventDefault();
                    searchInput.focus();
                    searchInput.classList.add('is-invalid');
                    setTimeout(() => searchInput.classList.remove('is-invalid'), 2000);
                }
            });
        }
        
        // Живой поиск (опционально)
        let debounceTimer;
        searchInput.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                const query = searchInput.value.trim();
                if (query.length >= 3) {
                    fetchSuggestions(query);
                }
            }, 500);
        });
    }
}

/**
 * Получение подсказок поиска
 */
function fetchSuggestions(query) {
    // Можно реализовать позже
    // fetch(`/api/suggest?q=${encodeURIComponent(query)}`)
    //     .then(r => r.json())
    //     .then(data => { ... });
}

/**
 * Инициализация фильтров
 */
function initFilters() {
    const filterForm = document.querySelector('.filter-card form');
    
    if (filterForm) {
        // Автоматическое применение фильтров при изменении
        const selects = filterForm.querySelectorAll('select');
        selects.forEach(select => {
            select.addEventListener('change', function() {
                // Можно добавить авто-отправку формы
                // filterForm.submit();
            });
        });
    }
}

/**
 * Подсветка поисковых терминов в результатах
 */
function highlightSearchTerms() {
    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get('q');
    
    if (!query) return;
    
    const terms = query.toLowerCase().split(/\s+/).filter(t => t.length > 2);
    const results = document.querySelectorAll('.result-card .abstract, .result-card h5');
    
    results.forEach(element => {
        let html = element.innerHTML;
        terms.forEach(term => {
            const regex = new RegExp(`(${escapeRegex(term)})`, 'gi');
            html = html.replace(regex, '<span class="highlight">$1</span>');
        });
        element.innerHTML = html;
    });
}

/**
 * Экранирование спецсимволов для регулярного выражения
 */
function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * API поиск (для AJAX-запросов)
 */
function apiSearch(query, page = 1, filters = {}) {
    const loadingEl = document.getElementById('searchLoading');
    const resultsEl = document.getElementById('searchResults');
    
    if (loadingEl) loadingEl.style.display = 'block';
    if (resultsEl) resultsEl.style.opacity = '0.5';
    
    fetch('/api/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            q: query,
            page: page,
            filters: filters
        })
    })
    .then(response => response.json())
    .then(data => {
        if (loadingEl) loadingEl.style.display = 'none';
        if (resultsEl) {
            resultsEl.style.opacity = '1';
            renderSearchResults(data);
        }
    })
    .catch(error => {
        console.error('Ошибка поиска:', error);
        if (loadingEl) loadingEl.style.display = 'none';
        if (resultsEl) resultsEl.style.opacity = '1';
    });
}

/**
 * Отрисовка результатов поиска
 */
function renderSearchResults(data) {
    const container = document.getElementById('searchResults');
    if (!container) return;
    
    if (!data.articles || data.articles.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-search" style="font-size: 3rem; color: #ccc;"></i>
                <p class="mt-3 text-muted">Ничего не найдено. Попробуйте изменить запрос.</p>
            </div>
        `;
        return;
    }
    
    let html = `<p class="text-muted mb-3">
        Найдено: ${data.total} результатов (${data.search_time_ms || 0} мс)
    </p>`;
    
    data.articles.forEach(article => {
        const authors = article.authors?.map(a => 
            `<a href="/author/${a.author_id}">${escapeHtml(a.name)}</a>`
        ).join(', ') || '';
        
        const year = article.published_date ? article.published_date.substring(0, 4) : 'н/д';
        const score = article.similarity_score;
        const scoreClass = score >= 0.8 ? 'similarity-high' : score >= 0.5 ? 'similarity-medium' : 'similarity-low';
        
        html += `
            <div class="result-card">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h5>
                            <a href="/article/${article.id}">${escapeHtml(article.title)}</a>
                        </h5>
                        <div class="authors">${authors}</div>
                        <div class="abstract">${escapeHtml(article.abstract || '').substring(0, 300)}${article.abstract?.length > 300 ? '...' : ''}</div>
                        <div class="meta">
                            <span class="me-3"><i class="bi bi-building"></i> ${escapeHtml(article.source || '')}</span>
                            <span class="me-3"><i class="bi bi-calendar"></i> ${year}</span>
                            <span><i class="bi bi-quote"></i> Цит: ${article.citation_count || 0}</span>
                        </div>
                    </div>
                    ${score ? `<span class="badge ${scoreClass} similarity-badge ms-2">${(score * 100).toFixed(0)}%</span>` : ''}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
    
    // Подсветка терминов
    highlightSearchTerms();
}

/**
 * Копирование ссылки на статью
 */
function copyArticleLink(articleId) {
    const url = `${window.location.origin}/article/${articleId}`;
    
    navigator.clipboard.writeText(url).then(() => {
        showToast('Ссылка скопирована!');
    }).catch(() => {
        // Fallback
        const textarea = document.createElement('textarea');
        textarea.value = url;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showToast('Ссылка скопирована!');
    });
}

/**
 * Показать уведомление
 */
function showToast(message) {
    // Создаем toast элемент
    const toast = document.createElement('div');
    toast.className = 'position-fixed bottom-0 end-0 p-3';
    toast.style.zIndex = '9999';
    toast.innerHTML = `
        <div class="toast show" role="alert">
            <div class="toast-body">
                <i class="bi bi-check-circle text-success"></i> ${message}
            </div>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

/**
 * Экранирование HTML
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Загрузка статистики
 */
function loadStats() {
    fetch('/api/stats')
        .then(r => r.json())
        .then(data => {
            const statsEl = document.getElementById('statsBar');
            if (statsEl && data.total_articles) {
                statsEl.innerHTML = `
                    <span class="me-3"><i class="bi bi-database"></i> ${data.total_articles} статей</span>
                    <span class="me-3"><i class="bi bi-people"></i> ${data.total_authors} авторов</span>
                    <span><i class="bi bi-quote"></i> ${data.total_citations} цитирований</span>
                `;
            }
        })
        .catch(err => console.error('Ошибка загрузки статистики:', err));
}

// Загружаем статистику при загрузке страницы
document.addEventListener('DOMContentLoaded', loadStats);