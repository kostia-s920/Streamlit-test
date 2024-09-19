import streamlit as st
import pandas as pd
import psycopg2
import re
import plotly.graph_objects as go


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


# Функція для побудови Plotly таблиці для змін у метаданих
def visualize_metadata_changes(metadata_changes):
    fig = go.Figure(data=[go.Table(
        header=dict(values=["Поле", "Було", "Стало"],
                    fill_color='paleturquoise',
                    align='left'),
        cells=dict(values=[metadata_changes['Поле'], metadata_changes['Було'], metadata_changes['Стало']],
                   fill_color='lavender',
                   align='left'))
    ])
    fig.update_layout(width=800, height=400)
    st.plotly_chart(fig)


# Функція для побудови Plotly таблиці для ключових слів
def visualize_keywords_changes(keywords_changes):
    fig = go.Figure(data=[go.Table(
        header=dict(values=["Ключове слово", "Зміна", "Було", "Стало"],
                    fill_color='paleturquoise',
                    align='left'),
        cells=dict(values=[keywords_changes['Ключове слово'], keywords_changes['Зміна'],
                           keywords_changes['Було'], keywords_changes['Стало']],
                   fill_color='lavender',
                   align='left'))
    ])
    fig.update_layout(width=800, height=400)
    st.plotly_chart(fig)


# Функція для порівняння контенту і візуалізації змін за допомогою Plotly
def visualize_content_changes(content_before, content_after):
    before_lines = content_before.splitlines()
    after_lines = content_after.splitlines()

    # Визначаємо кольори для кожного рядка
    line_colors = []
    for old_line, new_line in zip(before_lines, after_lines):
        if old_line == new_line:
            line_colors.append('white')  # Немає змін
        else:
            line_colors.append('yellow')  # Зміна у рядку

    # Створюємо таблицю Plotly
    fig = go.Figure(data=[go.Table(
        header=dict(values=["Рядок до", "Рядок після"],
                    fill_color='paleturquoise',
                    align='left'),
        cells=dict(values=[before_lines, after_lines],
                   fill_color=[['white'] * len(before_lines), line_colors],
                   align='left'))
    ])

    fig.update_layout(width=800, height=400)
    st.plotly_chart(fig)


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
        result.append((k, 'Додано', '-', f"{v} разів"))
    for k, v in removed.items():
        result.append((k, 'Видалено', f"{v} разів", '-'))
    for k, (old_v, new_v) in changed.items():
        result.append((k, 'Змінено', f"{old_v} разів", f"{new_v} разів"))

    return pd.DataFrame(result, columns=['Ключове слово', 'Зміна', 'Було', 'Стало'])


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
                            visualize_metadata_changes(metadata_df)

                        # Перевірка на наявність змін у контенті
                        if data1['content'].values[0] != data2['content'].values[0]:
                            st.subheader("Зміни в контенті:")
                            visualize_content_changes(data1['content'].values[0], data2['content'].values[0])

                        # Порівняння keywords_found у головній функції
                        if data1['keywords_found'].values[0] and data2['keywords_found'].values[0]:
                            keywords_comparison = compare_keywords(data1['keywords_found'].values[0],
                                                                   data2['keywords_found'].values[0])
                            if not keywords_comparison.empty:
                                st.subheader("Зміни в ключових словах:")
                                visualize_keywords_changes(keywords_comparison)

                        # Порівняння keywords_count
                        if data1['keywords_count'].values[0] != data2['keywords_count'].values[0]:
                            st.subheader("Зміни в кількості ключових слів:")
                            st.table(pd.DataFrame({
                                'Було': [data1['keywords_count'].values[0]],
                                'Стало': [data2['keywords_count'].values[0]]
                            }))

                    else:
                        st.write("Для обраних дат немає даних для порівняння.")

    conn.close()


if __name__ == "__main__":
    main()