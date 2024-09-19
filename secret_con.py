import streamlit as st
import pandas as pd
import psycopg2
import re
import streamlit.components.v1 as components


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
    query = f"SELECT DISTINCT url FROM {competitor_name}_content"
    return pd.read_sql(query, conn)['url'].tolist()


# Функція для отримання дат для сторінки з основної таблиці конкурента
def get_dates_from_main_table(conn, competitor_name, page_url):
    query = f"""
        SELECT DISTINCT date_checked
        FROM {competitor_name}_content
        WHERE url = '{page_url}'
        ORDER BY date_checked ASC
    """
    return pd.read_sql(query, conn)['date_checked'].tolist()


# Функція для отримання дат з таблиці змін content_changes
def get_dates_from_content_changes(conn, competitor_name, page_url):
    query = f"""
        SELECT DISTINCT change_date
        FROM content_changes
        WHERE competitor_name = '{competitor_name}' AND url = '{page_url}'
        ORDER BY change_date ASC
    """
    return pd.read_sql(query, conn)['change_date'].tolist()


# Функція для отримання даних з основної таблиці конкурента на обрану дату
def get_data_from_main_table(conn, competitor_name, page_url, date):
    query = f"""
        SELECT *
        FROM {competitor_name}_content
        WHERE url = '{page_url}' AND date_checked = '{date}'
    """
    return pd.read_sql(query, conn)


# Функція для отримання змін з таблиці content_changes
def get_changes_from_content_changes(conn, competitor_name, page_url, date):
    query = f"""
        SELECT *
        FROM content_changes
        WHERE competitor_name = '{competitor_name}' AND url = '{page_url}' AND change_date = '{date}'
    """
    return pd.read_sql(query, conn)


# Основна функція для інтерфейсу користувача
def main():
    st.title("Порівняння змін контенту конкурентів")

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
                # Вибір першої дати з основної таблиці конкурента
                main_dates = get_dates_from_main_table(conn, selected_competitor, selected_page)
                selected_main_date = st.selectbox('Виберіть дату з основної таблиці', main_dates)

                # Отримання дат із таблиці content_changes та підсвічування
                changes_dates = get_dates_from_content_changes(conn, selected_competitor, selected_page)
                date_colors = ['#cccccc' if date not in changes_dates else '#333333' for date in main_dates]

                # Показуємо користувачу дати із змінами (підсвічені темним)
                st.markdown(f"**Доступні дати зі змінами для {selected_page}:**")
                for i, date in enumerate(main_dates):
                    color = date_colors[i]
                    st.markdown(f"<span style='color:{color}'>{date}</span>", unsafe_allow_html=True)

                # Вибір другої дати з таблиці змін
                selected_change_date = st.selectbox('Виберіть дату зі змін', changes_dates)

                if selected_main_date and selected_change_date:
                    # Отримання даних з основної таблиці конкурента
                    main_data = get_data_from_main_table(conn, selected_competitor, selected_page, selected_main_date)

                    # Отримання змін з таблиці content_changes
                    changes_data = get_changes_from_content_changes(conn, selected_competitor, selected_page,
                                                                    selected_change_date)

                    # Порівняння та виведення результатів
                    if not main_data.empty and not changes_data.empty:
                        st.write(
                            f"Порівняння для сторінки {selected_page} між {selected_main_date} та {selected_change_date}:")
                        # Тут ти можеш додати логіку для порівняння та підсвічування змін
                        # Наприклад, використовуючи функції highlight_changes та extract_keywords для ключових слів
                        st.write(main_data)
                        st.write(changes_data)
                    else:
                        st.write(f"Зміни для сторінки {selected_page} відсутні між обраними датами.")

    conn.close()


if __name__ == "__main__":
    main()