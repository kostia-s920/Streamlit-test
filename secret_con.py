import streamlit as st
import pandas as pd
import psycopg2
from difflib import HtmlDiff
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
    query = f"SELECT DISTINCT url FROM {competitor_name}"
    return pd.read_sql(query, conn)['url'].tolist()


# Функція для отримання дат для сторінки
def get_dates_for_page(conn, competitor_name, page_url):
    query = f"""
        SELECT DISTINCT date_checked
        FROM {competitor_name}
        WHERE url = '{page_url}'
        ORDER BY date_checked ASC
    """
    return pd.read_sql(query, conn)['date_checked'].tolist()


# Функція для отримання даних для конкретної сторінки на обрану дату
def get_page_data(conn, competitor_name, page_url, date):
    query = f"""
        SELECT title, h1, description, content, keywords_found, keywords_count
        FROM {competitor_name}
        WHERE url = '{page_url}' AND date_checked = '{date}'
    """
    return pd.read_sql(query, conn)


# Функція для підсвічування змін у контенті
def highlight_changes(old_value, new_value):
    diff = HtmlDiff()
    html_diff = diff.make_file(old_value.splitlines(), new_value.splitlines(), context=True)
    return html_diff


# Функція для вилучення ключових слів і кількості їх повторень
def extract_keywords(row):
    pattern = re.findall(r'([\w\s-]+?)\s*-\s*(\d+)\s*разів', row)
    keywords_dict = {match[0].strip(): int(match[1]) for match in pattern}
    return keywords_dict


# Функція для порівняння keywords_found
def compare_keywords(old_keywords, new_keywords):
    old_dict = extract_keywords(old_keywords)
    new_dict = extract_keywords(new_keywords)

    # Визначаємо додані, видалені і змінені ключові слова
    added = {k: new_dict[k] for k in new_dict if k not in old_dict}
    removed = {k: old_dict[k] for k in old_dict if k not in new_dict}
    changed = {k: (old_dict[k], new_dict[k]) for k in old_dict if k in new_dict and old_dict[k] != new_dict[k]}

    result = []
    for k, v in added.items():
        result.append((k, 'Додано', '-', f"{v} разів", 'green'))
    for k, v in removed.items():
        result.append((k, 'Видалено', f"{v} разів", '-', 'red'))
    for k, (old_v, new_v) in changed.items():
        result.append((k, 'Змінено', f"{old_v} разів", f"{new_v} разів", 'yellow'))

    return pd.DataFrame(result, columns=['Ключове слово', 'Зміна', 'Було', 'Стало', 'Колір'])

# Функція для відображення легенди кольорів
def show_color_legend():
    st.markdown(
        """
        **Пояснення кольорів:**
        - 🟢 **Додано** — Ключове слово було додано.
        - 🔴 **Видалено** — Ключове слово було видалено.
        - 🟡 **Змінено** — Кількість згадувань ключового слова була змінена.
        """
    )


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
                # Вибір двох дат для порівняння
                dates = get_dates_for_page(conn, selected_competitor, selected_page)
                selected_date1 = st.selectbox('Виберіть першу дату', dates, key="date1")
                selected_date2 = st.selectbox('Виберіть другу дату', dates, key="date2")

                if selected_date1 and selected_date2:
                    # Отримуємо дані для обраних дат
                    data1 = get_page_data(conn, selected_competitor, selected_page, selected_date1)
                    data2 = get_page_data(conn, selected_competitor, selected_page, selected_date2)

                    if not data1.empty and not data2.empty:
                        st.write(f"Порівняння для сторінки {selected_page} між {selected_date1} та {selected_date2}:")

                        # Порівняння Title, H1, Description
                        metadata_changes = []
                        for col in ['title', 'h1', 'description']:
                            if data1[col].values[0] != data2[col].values[0]:
                                metadata_changes.append({
                                    'Поле': col,
                                    'Було': data1[col].values[0],
                                    'Стало': data2[col].values[0]
                                })

                        if metadata_changes:
                            st.subheader("Зміни в метаданих:")
                            metadata_df = pd.DataFrame(metadata_changes)
                            st.table(metadata_df)

                        # Порівняння контенту з підсвічуванням
                        st.subheader("Зміни в контенті:")
                        content_diff = highlight_changes(data1['content'].values[0], data2['content'].values[0])
                        components.html(content_diff, height=400, scrolling=True)

                        # Порівняння keywords_found у головній функції
                        if data1['keywords_found'].values[0] and data2['keywords_found'].values[0]:
                            keywords_comparison = compare_keywords(data1['keywords_found'].values[0],
                                                                   data2['keywords_found'].values[0])
                            if not keywords_comparison.empty:
                                st.subheader("Зміни в ключових словах:")
                                st.table(keywords_comparison.style.applymap(lambda val: f'background-color: {val}',
                                                                            subset=['Колір']))

                        # Порівняння keywords_count
                        if data1['keywords_count'].values[0] != data2['keywords_count'].values[0]:
                            st.subheader("Зміни в кількості ключових слів:")
                            st.table(pd.DataFrame({
                                'Було': [data1['keywords_count'].values[0]],
                                'Стало': [data2['keywords_count'].values[0]]
                            }))

                        # Показуємо легенду
                        show_color_legend()

                    else:
                        st.write("Для обраних дат немає даних для порівняння.")

    conn.close()


if __name__ == "__main__":
    main()