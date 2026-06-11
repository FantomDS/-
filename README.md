# Russian Scholar — это интеллектуальная поисковая система для русскоязычных научных статей, аналог Google Scholar с семантическим анализом содержания.

**Иструкция по запуску**
```
# 1. Клонирование и установка
git clone https://github.com/FantomDS/russian-scholar.git
cd russian-scholar
pip install -r requirements.txt

# 2. Сбор базы данных (занимает 15-30 минут)
python scripts/build_scholar_db.py

# 3. Запуск
python app.py
```
Откройте браузер и перейдите: http://localhost:5000

