import streamlit as st
import pandas as pd
import psycopg2
import re
import streamlit.components.v1 as components
from difflib import HtmlDiff

# Функція для підключення до бази даних PostgreSQL
def connect_to_db():
    try:
        connection = psycopg2.connect(
            host="localhost",
            database="competitor_content",
            user="kostia.s920",
            password="1502"
        )
        return connection
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return None

# Функція для отримання списку конкурентів
def get_competitors(conn):
    query = "SELECT DISTINCT competitor_name FROM content_changes"
    return pd.read_sql(query, conn)['competitor_name'].tolist()

# Функція для отримання списку URL для обраного конкурента
def get_pages_for_competitor(conn, competitor_name):
    query = f"SELECT DISTINCT url FROM content_changes WHERE competitor_name = '{competitor_name}'"
    return pd.read_sql(query, conn)['url'].tolist()

# Функція для отримання дат для обраної сторінки та конкурента
def get_dates_for_page(conn, competitor_name, page_url):
    query = f"""
        SELECT DISTINCT change_date
        FROM content_changes
        WHERE competitor_name = '{competitor_name}' AND url = '{page_url}'
        ORDER BY change_date ASC
    """
    return pd.read_sql(query, conn)['change_date'].tolist()

# Функція для отримання змін для порівняння за обраною сторінкою і датою
def get_changes(conn, competitor_name, page_url, date):
    query = f"""
        SELECT field_changed, old_value, new_value, change_date
        FROM content_changes
        WHERE competitor_name = '{competitor_name}'
        AND url = '{page_url}'
        AND change_date = '{date}'
    """
    return pd.read_sql(query, conn)

# Функція для вилучення ключових слів і кількості їх повторень
def extract_keywords(row):
    pattern = re.findall(r'([\w\s-]+?)\s*-\s*(\d+)\s*разів', row)
    keywords_dict = {match[0].strip(): int(match[1]) for match in pattern}
    return keywords_dict

# Функція для застосування стилів до таблиці
def apply_table_styles():
    st.markdown(
        """
        <style>
        .styled-table {
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 1.0em;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-width: 400px;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
        }
        .styled-table thead tr {
            background-color: #009879;
            color: #ffffff;
            text-align: left;
        }
        .styled-table th,
        .styled-table td {
            padding: 12px 15px;
        }
        .styled-table tbody tr {
            border-bottom: 1px solid #dddddd;
        }
        .styled-table tbody tr:nth-of-type(even) {
            background-color: #f3f3f3;
        }
        .styled-table tbody tr:last-of-type {
            border-bottom: 2px solid #009879;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# Основна функція для інтерфейсу користувача
def main():
    st.title("Візуалізація змін конкурентів")

    conn = connect_to_db()

    if conn:
        # Вибір конкурента
        competitors = get_competitors(conn)
        selected_competitor = st.selectbox('Виберіть конкурента', competitors)

        if selected_competitor:
            # Вибір сторінки для конкурента
            pages = get_pages_for_competitor(conn, selected_competitor)
            selected_page = st.selectbox('Виберіть сторінку', pages)

            if selected_page:
                # Вибір дати для порівняння змін
                dates = get_dates_for_page(conn, selected_competitor, selected_page)
                selected_date = st.selectbox('Виберіть дату для порівняння', dates)

                if selected_date:
                    # Отримання змін для обраної сторінки та дати
                    changes = get_changes(conn, selected_competitor, selected_page, selected_date)

                    if not changes.empty:
                        st.write(f"Зміни для {selected_page} на дату {selected_date}:")

                        # Перевірка, якщо змінилось поле keywords_count
                        for index, row in changes.iterrows():
                            if row['field_changed'] == 'keywords_count':
                                apply_table_styles()
                                count_table = pd.DataFrame({
                                    'Було': [row['old_value']],
                                    'Стало': [row['new_value']]
                                })
                                st.markdown(f"<b>Поле змінено: {row['field_changed']}</b>", unsafe_allow_html=True)
                                st.markdown(count_table.to_html(classes='styled-table', index=False), unsafe_allow_html=True)

                            # Перевірка, якщо змінилось поле keywords_found
                            if row['field_changed'] == 'keywords_found':
                                st.subheader(f"Поле змінено: {row['field_changed']}")
                                old_keywords = extract_keywords(row['old_value'] or '')
                                new_keywords = extract_keywords(row['new_value'] or '')

                                keyword_changes = []
                                for keyword in set(old_keywords.keys()).union(set(new_keywords.keys())):
                                    old_count = old_keywords.get(keyword, 0)
                                    new_count = new_keywords.get(keyword, 0)
                                    if old_count != new_count:
                                        keyword_changes.append({
                                            'Ключове слово': keyword,
                                            'Зміна': 'Змінено',
                                            'Кількість': f'Було: {old_count} разів, Стало: {new_count} разів'
                                        })

                                if keyword_changes:
                                    # Застосовуємо стилі до таблиці
                                    apply_table_styles()

                                    # Показуємо таблицю з ключовими словами
                                    df_changes = pd.DataFrame(keyword_changes)
                                    st.markdown(df_changes.to_html(classes='styled-table', index=False), unsafe_allow_html=True)
                                else:
                                    st.write("Немає змін у ключових словах.")
                    else:
                        st.write(f"Зміни для сторінки {selected_page} відсутні.")

    conn.close()

if __name__ == "__main__":
    main()