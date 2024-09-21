import tempfile
import base64
import plotly.graph_objects as go
import re
import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# Функція для підключення до бази даних PostgreSQL
def connect_to_db():
    try:
        # Декодуємо сертифікат із Base64
        ssl_cert_decoded = base64.b64decode(st.secrets["db_ssl_root_cert"])

        # Створюємо тимчасовий файл для зберігання сертифіката
        with tempfile.NamedTemporaryFile(delete=False) as cert_file:
            cert_file.write(ssl_cert_decoded)
            cert_file_path = cert_file.name

        # Підключаємося до бази даних за допомогою секретів
        connection = psycopg2.connect(
            host=st.secrets["db_host"],
            database=st.secrets["db_name"],
            user=st.secrets["db_username"],
            password=st.secrets["db_password"],
            port=st.secrets["db_port"],
            sslmode=st.secrets["ssl_mode"],
            sslrootcert=cert_file_path  # Передаємо шлях до тимчасового файлу з сертифікатом
        )
        return connection
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return None

#Функція для отримання списку конкурентів
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


# Функція для отримання даних по ключовим словам із бази даних
def get_keyword_data(conn, competitor_name):
    query = f"""
        SELECT url, keywords_count, keywords_found, content, date_checked 
        FROM {competitor_name}
        ORDER BY date_checked ASC
    """
    df = pd.read_sql(query, conn)
    return df

# Функція для отримання історичних даних по вибраному ключовому слову
def get_keyword_history(conn, competitor_name, keyword):
    query = f"""
        SELECT url, date_checked, keywords_found
        FROM {competitor_name}
        WHERE keywords_found ILIKE %s
        ORDER BY date_checked ASC
    """
    df = pd.read_sql(query, conn, params=[f'%{keyword}%'])
    return df

# Функція для побудови графіка ключових слів
def plot_keyword_trend(df, competitor_name):
    fig = go.Figure()

    # Проходимо по всім унікальним URL
    for url in df['url'].unique():
        url_data = df[df['url'] == url]
        fig.add_trace(go.Scatter(x=url_data['date_checked'], y=url_data['keywords_count'], mode='lines', name=url))

    fig.update_layout(
        title=f'Keyword Count Trend for {competitor_name}',
        xaxis_title='Date',
        yaxis_title='Keyword Count',
        legend_title='URL',
        xaxis=dict(tickformat='%Y-%m-%d', tickangle=45)
    )

    st.plotly_chart(fig)

# Функція для побудови історичного графіка по ключовому слову
def plot_keyword_history(df, keyword, selected_url, chart_type):
    # Фільтруємо дані по обраному URL
    url_data = df[df['url'] == selected_url]
    if url_data.empty:
        st.write(f"No data for URL: {selected_url}")
        return

    # Перетворення дат на datetime
    url_data['date_checked'] = pd.to_datetime(url_data['date_checked'], errors='coerce')

    # Використовуємо функцію для вилучення кількості ключових слів
    keyword_counts = url_data['keywords_found'].apply(lambda row: extract_keywords(row).get(keyword, 0))

    fig = go.Figure()

    # Додаємо графік в залежності від обраного типу графіка
    if chart_type == 'Line Chart':
        fig.add_trace(go.Scatter(x=url_data['date_checked'], y=keyword_counts, mode='lines', name=selected_url))
    elif chart_type == 'Bar Chart':
        fig.add_trace(go.Bar(x=url_data['date_checked'], y=keyword_counts, name=selected_url))
    elif chart_type == 'Scatter Plot':
        fig.add_trace(go.Scatter(x=url_data['date_checked'], y=keyword_counts, mode='markers', name=selected_url))
    elif chart_type == 'Area Chart':
        fig.add_trace(go.Scatter(x=url_data['date_checked'], y=keyword_counts, fill='tozeroy', name=selected_url))
    elif chart_type == 'Step Chart':
        fig.add_trace(go.Scatter(x=url_data['date_checked'], y=keyword_counts, mode='lines', line_shape='hv', name=selected_url))

    fig.update_layout(
        title=f'Historical Trend for Keyword: {keyword}',
        xaxis_title='Date',
        yaxis_title='Keyword Occurrences',
        xaxis=dict(tickformat='%Y-%m-%d', tickangle=45)
    )

    st.plotly_chart(fig)

# Функція для графіка порівняння кількох конкурентів
def plot_comparison(df_list, competitor_names, selected_urls):
    fig = go.Figure()

    # Проходимо по всім обраним конкурентам та їх сторінкам
    for df, competitor, url in zip(df_list, competitor_names, selected_urls):
        url_data = df[df['url'] == url]
        if not url_data.empty:
            fig.add_trace(go.Scatter(x=url_data['date_checked'], y=url_data['keywords_count'],
                                     mode='lines', name=f'{competitor}: {url}'))
        else:
            st.write(f"No data for {competitor}: {url}")

    fig.update_layout(
        title='Keyword Count Comparison',
        xaxis_title='Date',
        yaxis_title='Keyword Count',
        xaxis=dict(tickformat='%Y-%m-%d', tickangle=45),
        legend_title="Competitor: URL"
    )

    st.plotly_chart(fig)

# Функція для відображення контенту сторінки з підсвічуванням ключових слів
def highlight_keywords(text, keywords):
    if not text:
        return "No content found."
    for keyword in keywords:
        escaped_keyword = re.escape(keyword)  # Захист від спеціальних символів
        text = re.sub(f'({escaped_keyword})', r'<span style="color:red; font-weight:bold;">\1</span>', text, flags=re.IGNORECASE)
    return text

# Функція для рендерингу сітки змін за місяцями
def render_contribution_chart_by_months(change_dates, selected_year, conn, competitor, selected_page=None):
    st.markdown(
        """
        <style>
        .contribution-box {
            width: 12px;
            height: 12px;
            margin: 2px;
            display: inline-block;
            background-color: #ebedf0;
        }
        .contribution-level-1 { background-color: #c6e48b; }
        .contribution-level-2 { background-color: #7bc96f; }
        .contribution-level-3 { background-color: #239a3b; }
        .contribution-level-4 { background-color: #196127; }
        .contribution-box-container {
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            max-width: 900px;  /* Обмежуємо ширину */
        }
        .month-column {
            display: grid;
            grid-template-rows: repeat(7, 14px);  /* 7 днів на рядок */
            grid-auto-flow: column;  /* Заповнення по колонках */
            gap: 4px;
            margin-right: 20px;
            text-align: center;
        }
        .month-title {
            text-align: center;
            margin-bottom: 10px;
            font-weight: bold;
            font-size: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Фільтруємо дати за обраним роком
    change_dates['change_date'] = pd.to_datetime(change_dates['change_date']).dt.date
    change_dates = change_dates[change_dates['change_date'].apply(lambda x: x.year) == selected_year]

    def render_month_labels():
        months = {
            'Jan': 31, 'Feb': 28, 'Mar': 31, 'Apr': 30, 'May': 31, 'Jun': 30,
            'Jul': 31, 'Aug': 31, 'Sep': 30, 'Oct': 31, 'Nov': 30, 'Dec': 31
        }

        months_html = '<div style="display: flex; flex-wrap: wrap; gap: 20px;">'

        for month, days in months.items():
            month_html = f'<div style="text-align: center;"><div style="margin-bottom: 5px;">{month}</div>'
            month_html += f'<div style="display: grid; grid-template-columns: repeat(7, 14px); grid-gap: 2px;">'

            for day in range(1, days + 1):
                date = datetime(selected_year, list(months.keys()).index(month) + 1, day).date()

                # Змінюємо запит в залежності від того, вибрано конкретну сторінку чи всі зміни конкурента
                if selected_page:
                    query = f"""
                    SELECT change_date 
                    FROM content_changes 
                    WHERE competitor_name = '{competitor}'
                    AND url = '{selected_page}'
                    AND change_date::date = '{date}'
                    """
                    result = pd.read_sql(query, conn)
                    pages = result['change_date'].tolist() if not result.empty else []
                else:
                    query = f"""
                    SELECT url 
                    FROM content_changes 
                    WHERE competitor_name = '{competitor}'
                    AND change_date::date = '{date}'
                    """
                    pages = pd.read_sql(query, conn)['url'].tolist()

                # Визначаємо рівень для відображення кольору
                if not pages:
                    level = 'contribution-box'
                    tooltip = f"{date} - немає змін"
                else:
                    if len(pages) <= 1:
                        level = 'contribution-box contribution-level-1'
                    elif len(pages) <= 3:
                        level = 'contribution-box contribution-level-2'
                    elif len(pages) <= 5:
                        level = 'contribution-box contribution-level-3'
                    else:
                        level = 'contribution-box contribution-level-4'

                    # Формуємо список сторінок для відображення в спливаючому вікні
                    if selected_page:
                        tooltip = f"{date} - зміни на цій сторінці"
                    else:
                        tooltip = f"{date} - зміни:\n" + "\n".join(pages)

                month_html += f'<div class="{level}" title="{tooltip}"></div>'

            month_html += '</div>'
            months_html += f'{month_html}</div>'

        months_html += '</div>'
        return months_html

    # Викликаємо рендеринг місяців
    st.markdown(render_month_labels(), unsafe_allow_html=True)

# Основна функція для відображення даних у Streamlit
def main():
    # Підключаємося до бази даних
    conn = connect_to_db()

    if conn:
        # Додаємо бічну панель для навігації між сторінками
        st.sidebar.title("Навігація")

        # Отримуємо список конкурентів
        competitors = get_competitors(conn)

        # Список сторінок
        pages = ["Візуалізація змін контенту",
                 "Загальна кількість ключових слів",
                 "Порівняння ключових слів між конкурентами",
                 "Контент сторінки з підсвіченими ключовими словами",
                 "Порівняння контенту"]

        # Вибір сторінки через кнопки на бічній панелі
        page_selection = st.sidebar.radio("Оберіть сторінку", pages)

        # Відображення контенту в залежності від вибору сторінки
        if page_selection == "Візуалізація змін контенту":
            render_content_change_visualization(conn)
        elif page_selection == "Загальна кількість ключових слів":
            render_keyword_count(conn)
        elif page_selection == "Порівняння ключових слів між конкурентами":
            render_keyword_comparison(conn, competitors)
        elif page_selection == "Контент сторінки з підсвіченими ключовими словами":
            render_page_content_with_keywords(conn, competitors)
        elif page_selection == "Порівняння контенту":
            render_content_comparison(conn)


# Функції для кожної сторінки
def render_content_change_visualization(conn):
    st.title("Візуалізація змін контенту")


    # Отримуємо список конкурентів
    competitors = get_competitors(conn)

    competitor = st.selectbox("Виберіть конкурента", competitors, key="content_competitor_selectbox")

    # Перевіряємо, чи вибраний чекбокс
    view_all = st.checkbox("Показати всі зміни конкурента", key="content_view_all_checkbox")

    if view_all:
        # Показуємо всі зміни конкурента
        query = f"SELECT change_date FROM content_changes WHERE competitor_name = '{competitor}'"
        df = pd.read_sql(query, conn)

        if not df.empty:
            selected_year = st.selectbox("Оберіть рік", [2024, 2025], key="year_selectbox")
            st.subheader(f"Загальні зміни для {competitor} у {selected_year} році")
            render_contribution_chart_by_months(df, selected_year, conn, competitor)
        else:
            st.write("Немає змін для цього конкурента.")
    else:
        # Якщо не вибрано "Показати всі зміни конкурента", вибираємо сторінку
        page_query = f"SELECT DISTINCT url FROM content_changes WHERE competitor_name = '{competitor}'"
        pages = pd.read_sql(page_query, conn)['url'].tolist()

        if not pages:
            st.write("Немає доступних сторінок для цього конкурента.")
        else:
            selected_page = st.selectbox("Виберіть сторінку", pages, key="content_page_selectbox")

            # Показуємо зміни для вибраної сторінки
            query = f"SELECT change_date FROM content_changes WHERE competitor_name = '{competitor}' AND url = '{selected_page}'"
            df = pd.read_sql(query, conn)

            if not df.empty:
                selected_year = st.selectbox("Оберіть рік", [2024, 2025], key="year_selectbox")
                render_contribution_chart_by_months(df, selected_year, conn, competitor, selected_page)
            else:
                st.write("Немає змін для цієї сторінки.")


def render_keyword_count(conn):
    st.title("Загальна кількість ключових слів")
    competitors = ['docebo_com', 'ispringsolutions_com', 'talentlms_com', 'paradisosolutions_com', 'academyocean_com']
    competitor_name = st.selectbox("Виберіть конкурента", competitors, key="keyword_competitor_selectbox")
    df = get_keyword_data(conn, competitor_name)

    if not df.empty:
        selected_urls = st.multiselect('Виберіть URL', df['url'].unique(), max_selections=5,
                                       key="keyword_url_multiselect")

        # Фільтр по датах
        start_date = pd.to_datetime(
            st.date_input('Початкова дата', df['date_checked'].min(), key="keyword_start_date")).date()
        end_date = pd.to_datetime(
            st.date_input('Кінцева дата', df['date_checked'].max(), key="keyword_end_date")).date()
        df['date_checked'] = pd.to_datetime(df['date_checked']).dt.date
        df = df[(df['date_checked'] >= start_date) & (df['date_checked'] <= end_date)]

        if selected_urls:
            df = df[df['url'].isin(selected_urls)]

            st.subheader(f'Тренд кількості ключових слів для {competitor_name}')
            plot_keyword_trend(df, competitor_name)

            selected_url_for_keywords = st.selectbox('Виберіть URL для перегляду знайдених ключових слів',
                                                     df['url'].unique(), key="keyword_url_selectbox")

            if selected_url_for_keywords:
                selected_page_data = df[df['url'] == selected_url_for_keywords].iloc[0]
                if selected_page_data['keywords_found'] and isinstance(selected_page_data['keywords_found'],
                                                                       str):
                    keywords_dict = extract_keywords(selected_page_data['keywords_found'])

                    st.write(f"Знайдені ключові слова на {selected_url_for_keywords}:")
                    st.write(keywords_dict)

                    selected_keywords = st.multiselect('Виберіть ключові слова для аналізу історії',
                                                       list(keywords_dict.keys()),
                                                       key="keyword_select_multiselect")

                    if selected_keywords:
                        chart_type = st.selectbox("Тип графіка",
                                                  ['Line Chart', 'Bar Chart', 'Scatter Plot', 'Area Chart',
                                                   'Step Chart'], key="keyword_chart_type_selectbox")
                        for keyword in selected_keywords:
                            st.subheader(f'Історія для ключового слова: {keyword}')
                            keyword_history_df = get_keyword_history(conn, competitor_name, keyword)
                            if not keyword_history_df.empty:
                                plot_keyword_history(keyword_history_df, keyword, selected_url_for_keywords,
                                                     chart_type)
                            else:
                                st.write(f"Немає даних для ключового слова: {keyword}")


def render_keyword_comparison(conn, competitors):
    st.title("Порівняння ключових слів між конкурентами")
    selected_competitors = st.multiselect("Виберіть конкурентів для порівняння", competitors,
                                          default=competitors[:2], key="comparison_competitors_multiselect")
    df_list = [get_keyword_data(conn, competitor) for competitor in selected_competitors]

    selected_urls_for_comparison = []
    for competitor, df in zip(selected_competitors, df_list):
        selected_url = st.selectbox(f'Виберіть URL для {competitor}', df['url'].unique(),
                                    key=f"comparison_url_selectbox_{competitor}")
        selected_urls_for_comparison.append(selected_url)

    if len(selected_urls_for_comparison) == len(selected_competitors):
        plot_comparison(df_list, selected_competitors, selected_urls_for_comparison)


def render_page_content_with_keywords(conn, competitors):
    st.title("Контент сторінки з підсвіченими ключовими словами")
    competitor_name_content = st.selectbox("Виберіть конкурента для перегляду контенту", competitors,
                                           key="content_competitor_selectbox_2")
    df_content = get_keyword_data(conn, competitor_name_content)

    if not df_content.empty:
        selected_url_for_content = st.selectbox('Виберіть URL для перегляду контенту',
                                                df_content['url'].unique(), key="content_url_selectbox_2")
        selected_date_for_content = st.selectbox('Виберіть дату',
                                                 df_content[df_content['url'] == selected_url_for_content][
                                                     'date_checked'].dt.date.unique(),
                                                 key="content_date_selectbox")

        if selected_date_for_content:
            page_content_data = df_content[(df_content['url'] == selected_url_for_content) & (
                    df_content['date_checked'].dt.date == selected_date_for_content)]
            page_content = page_content_data['content'].values[0]
            keywords_found = page_content_data['keywords_found'].values[0]
            keywords_dict = extract_keywords(keywords_found)
            highlighted_content = highlight_keywords(page_content, list(keywords_dict.keys()))

            st.markdown(f"<div style='white-space: pre-wrap; padding: 15px;'>{highlighted_content}</div>",
                        unsafe_allow_html=True)


def render_content_comparison(conn):
    st.title("Порівняння контенту")
    # Отримуємо список конкурентів
    competitors = get_competitors(conn)
    selected_competitor = st.selectbox('Виберіть конкурента', competitors)

    if selected_competitor:
        # Вибір сторінки для конкурента
        pages = get_pages_for_competitor(conn, selected_competitor)
        selected_page = st.selectbox('Виберіть сторінку', pages)

        if selected_page:
            # Вибір двох дат для порівняння
            dates = get_dates_for_page(conn, selected_competitor, selected_page)

            if dates:
                # Перетворення дат в формат datetime для віджета
                formatted_dates = [pd.to_datetime(date).date() for date in dates]

                # Вибір дат через календар
                selected_date1 = st.date_input('Виберіть першу дату', min_value=min(formatted_dates),
                                               max_value=max(formatted_dates),
                                               value=min(formatted_dates),
                                               key="date1")
                selected_date2 = st.date_input('Виберіть другу дату', min_value=min(formatted_dates),
                                               max_value=max(formatted_dates),
                                               value=max(formatted_dates),
                                               key="date2")

                # Перевіряємо, чи вибрано дві різні дати
                if selected_date1 and selected_date2 and selected_date1 != selected_date2:
                    # Перетворення обраних дат у строки для SQL-запиту
                    date1_str = pd.to_datetime(
                        [date for date in dates if pd.to_datetime(date).date() == selected_date1][0])
                    date2_str = pd.to_datetime(
                        [date for date in dates if pd.to_datetime(date).date() == selected_date2][0])

                    # Отримуємо дані для обраних дат
                    data1 = get_page_data(conn, selected_competitor, selected_page, date1_str)
                    data2 = get_page_data(conn, selected_competitor, selected_page, date2_str)

                    if not data1.empty and not data2.empty:

                        # Порівняння метаданих (Title, H1, Description)
                        metadata_changes = [
                            {'Поле': col, 'Було': data1[col].values[0], 'Стало': data2[col].values[0]}
                            for col in ['title', 'h1', 'description'] if
                            data1[col].values[0] != data2[col].values[0]
                        ]

                        if metadata_changes:
                            st.subheader("Зміни в метаданих:")
                            metadata_df = pd.DataFrame(metadata_changes)
                            visualize_metadata_changes(metadata_df)
                        else:
                            st.write("Змін у метаданих не знайдено.")

                        # Перевірка на наявність змін у контенті
                        if data1['content'].values[0] != data2['content'].values[0]:
                            st.subheader("Зміни в контенті:")
                            visualize_content_changes(data1['content'].values[0], data2['content'].values[0])
                        else:
                            st.write("Змін у контенті не знайдено.")

                        # Порівняння ключових слів
                        if data1['keywords_found'].values[0] and data2['keywords_found'].values[0]:
                            keywords_comparison = compare_keywords(data1['keywords_found'].values[0],
                                                                   data2['keywords_found'].values[0])
                            if not keywords_comparison.empty:
                                st.subheader("Зміни в ключових словах:")
                                visualize_keywords_changes(keywords_comparison)
                            else:
                                st.write("Змін у ключових словах не знайдено.")

                        # Порівняння кількості ключових слів
                        if data1['keywords_count'].values[0] != data2['keywords_count'].values[0]:
                            st.subheader("Зміни в кількості ключових слів:")
                            st.table(pd.DataFrame({
                                'Було': [data1['keywords_count'].values[0]],
                                'Стало': [data2['keywords_count'].values[0]]
                            }))
                        else:
                            st.write("Змін у кількості ключових слів не знайдено.")
                    else:
                        st.write("Для обраних дат немає даних для порівняння.")
                else:
                    st.warning("Оберіть дві різні дати для порівняння.")
            else:
                st.write("Немає доступних дат для цієї сторінки.")


if __name__ == "__main__":
    main()