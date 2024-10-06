import streamlit as st
import requests
import psycopg2
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup
import re
from dotenv import load_dotenv
import os
import schedule
import time
import threading

# Завантаження змінних середовища з файлу .env
load_dotenv()

# Отримання змінних середовища
API_KEY = os.getenv('GOOGLE_API_KEY')
CX = os.getenv('GOOGLE_CX')
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

# Налаштування сторінки
st.set_page_config(page_title="Rank Tracker", layout="wide")


# Функція для підключення до бази даних PostgreSQL
def connect_to_db():
    try:
        connection = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return connection
    except Exception as e:
        st.error(f"Помилка при підключенні до бази даних: {e}")
        return None


# Функція для додавання нового ключового слова до бази даних
def add_keyword_to_db(keyword, tag, url, connection):
    try:
        cursor = connection.cursor()
        cursor.execute('''
            INSERT INTO keywords (keyword, tag, url) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (keyword) DO NOTHING;
        ''', (keyword, tag, url))
        connection.commit()
        cursor.close()
        if cursor.rowcount:
            st.success(f"Ключове слово '{keyword}' додано успішно.")
        else:
            st.warning(f"Ключове слово '{keyword}' вже існує.")
    except Exception as e:
        st.error(f"Помилка при додаванні ключового слова: {e}")


# Функція для створення таблиці для нового проекту
def create_project_table(domain, region, connection):
    table_name = f"Rank_tracker_{domain}_{region}"
    try:
        cursor = connection.cursor()
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                keyword TEXT NOT NULL,
                tag TEXT NOT NULL,
                url TEXT NOT NULL,
                region TEXT NOT NULL,
                date DATE NOT NULL,
                position INTEGER NOT NULL
            );
        ''')
        connection.commit()
        cursor.close()
        st.success(f"Таблиця '{table_name}' створена або вже існує.")
    except Exception as e:
        st.error(f"Помилка при створенні таблиці: {e}")


# Функція для виконання пошуку та визначення позиції URL
def get_position(query, url, api_key, cx, region):
    search_results = perform_search(query, api_key, cx, region)
    position = None
    for idx, item in enumerate(search_results, 1):
        if item.get('link') == url:
            position = idx
            break
    return position


# Функція для виконання пошуку за допомогою Google Custom Search API
def perform_search(query, api_key, cx, region=None):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'q': query,
        'key': api_key,
        'cx': cx,
        'num': 10  # Максимум 10 результатів
    }
    if region:
        params['gl'] = region  # Додавання параметра регіону

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        results = response.json()
        return results.get('items', [])
    except requests.exceptions.RequestException as e:
        st.error(f"Помилка при отриманні результатів пошуку: {e}")
        return []


# Функція для отримання ключових слів з таблиці "keywords"
def get_keywords(connection):
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT keyword FROM keywords ORDER BY keyword ASC')
        keywords = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return keywords
    except Exception as e:
        st.error(f"Помилка при отриманні ключових слів: {e}")
        return []


# Функція для отримання тегу та URL для обраного ключового слова
def get_tag_and_url(connection, keyword):
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT tag, url FROM keywords WHERE keyword = %s', (keyword,))
        result = cursor.fetchone()
        cursor.close()
        if result:
            return result[0], result[1]
        else:
            return None, None
    except Exception as e:
        st.error(f"Помилка при отриманні тегу та URL для ключового слова '{keyword}': {e}")
        return None, None


# Функція для додавання позиції до таблиці проекту
def add_position_to_project(domain, region, keyword, tag, url, date, position, connection):
    table_name = f"Rank_tracker_{domain}_{region}"
    try:
        cursor = connection.cursor()
        cursor.execute(f'''
            INSERT INTO {table_name} (keyword, tag, url, region, date, position)
            VALUES (%s, %s, %s, %s, %s, %s);
        ''', (keyword, tag, url, region, date, position))
        connection.commit()
        cursor.close()
    except Exception as e:
        st.error(f"Помилка при додаванні позиції до таблиці: {e}")


# Функція для відстеження позицій ключових слів
def track_positions(domain, region, connection):
    table_name = f"Rank_tracker_{domain}_{region}"
    try:
        cursor = connection.cursor()
        cursor.execute(f'''
            SELECT keyword, tag, url FROM keywords;
        ''')
        keywords_data = cursor.fetchall()
        cursor.close()

        if not keywords_data:
            st.info("Таблиця 'keywords' порожня. Додайте ключові слова до бази даних.")
            return

        today_str = datetime.now().strftime("%Y-%m-%d")
        date_obj = datetime.strptime(today_str, "%Y-%m-%d").date()

        for keyword, tag, url in keywords_data:
            position = get_position(keyword, url, API_KEY, CX, region)
            if position:
                add_position_to_project(domain, region, keyword, tag, url, date_obj, position, connection)
                st.success(f"Ключове слово '{keyword}' має позицію {position} за запитом '{keyword}'.")
            else:
                st.warning(f"Ключове слово '{keyword}' не знайдено у видачі.")
    except Exception as e:
        st.error(f"Помилка при відстеженні позицій: {e}")


# Функція для створення нового проекту
def create_new_project(domain, region, connection):
    create_project_table(domain, region, connection)


# Функція для планування автоматичного відстеження
def schedule_tracking(domain, region, connection):
    def job():
        st.write(f"Автоматичний запуск відстеження для домену {domain} у регіоні {region}.")
        track_positions(domain, region, connection)

    schedule.every().monday.do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)


# Основна функція Streamlit
def main():
    st.title("Rank Tracker - Відстеження Позицій Ключових Слів у Google")

    # Ліве меню для налаштування
    with st.sidebar:
        st.header("Налаштування")

        # Введення Домену та Регіону
        domain = st.text_input("Введіть домен", value="example.com")
        regions = {
            "США": "us",
            "Велика Британія": "uk",
            "Канада": "ca",
            "Австралія": "au",
            "Німеччина": "de",
            "Франція": "fr",
            "Іспанія": "es",
            "Італія": "it",
            "Україна": "ua",
            "Росія": "ru",
            # Додайте більше країн за потребою
        }
        selected_region = st.selectbox("Оберіть регіон пошуку", options=list(regions.keys()), index=0)
        region_code = regions[selected_region]

        # Створення нового проекту
        if st.button("Створити/Оновити проект"):
            if domain and selected_region:
                conn = connect_to_db()
                if conn:
                    create_new_project(domain, region_code, conn)
                    conn.close()
            else:
                st.error("Будь ласка, введіть домен та оберіть регіон.")

        st.markdown("---")

        # Форма для додавання нового ключового слова
        st.header("Додати ключове слово")
        with st.form(key='add_keyword_form'):
            new_keyword = st.text_input("Ключове слово")
            new_tag = st.text_input("Тег")
            new_url = st.text_input("URL сторінки")
            submit_button = st.form_submit_button(label='Додати')

        if submit_button:
            if new_keyword and new_tag and new_url:
                conn = connect_to_db()
                if conn:
                    add_keyword_to_db(new_keyword, new_tag, new_url, conn)
                    conn.close()
            else:
                st.error("Будь ласка, заповніть всі поля форми.")

        st.markdown("---")

        # Можливість автоматичного відстеження
        st.header("Автоматичне відстеження")
        auto_track = st.checkbox("Ввімкнути автоматичне відстеження раз на тиждень")
        if auto_track:
            if domain and selected_region:
                conn = connect_to_db()
                if conn:
                    # Запуск планувальника у окремому потоці
                    threading.Thread(target=schedule_tracking, args=(domain, region_code, conn), daemon=True).start()
                    st.success("Автоматичне відстеження запущено.")
            else:
                st.error("Будь ласка, створіть проект перед увімкненням автоматичного відстеження.")

    # Основний контент
    if st.sidebar.button("Відстежити позиції зараз"):
        conn = connect_to_db()
        if conn:
            track_positions(domain, region_code, conn)
            conn.close()

    # Відображення історії відстеження
    st.markdown("---")
    st.subheader("Історія відстеження позицій")
    with st.expander("Переглянути історію"):
        conn = connect_to_db()
        if conn:
            table_name = f"Rank_tracker_{domain}_{region_code}"
            try:
                cursor = conn.cursor()
                cursor.execute(f'''
                    SELECT keyword, tag, url, date, position FROM {table_name} ORDER BY date DESC;
                ''')
                data = cursor.fetchall()
                cursor.close()
                if data:
                    df_history = pd.DataFrame(data, columns=['Ключове слово', 'Тег', 'URL', 'Дата', 'Позиція'])
                    st.dataframe(df_history)
                else:
                    st.info("Історія відстеження порожня.")
            except Exception as e:
                st.error(f"Помилка при отриманні історії: {e}")
            conn.close()


if __name__ == "__main__":
    main()