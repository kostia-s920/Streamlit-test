import plotly.graph_objects as go
import re
import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import difflib
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


#Функція для отримання списку конкурентів
def get_competitors_from_content_changes(conn):
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
        WHERE url = %s AND date_checked = %s
    """
    return pd.read_sql(query, conn, params=[page_url, date])


# Функція для побудови Plotly таблиці для змін у метаданих
def visualize_metadata_changes(metadata_changes):
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=["Поле", "Було", "Стало"],
            fill_color='paleturquoise',
            align='left',
            font=dict(color='black')  # Встановлюємо колір тексту заголовка
        ),
        cells=dict(
            values=[metadata_changes['Поле'], metadata_changes['Було'], metadata_changes['Стало']],
            fill_color='lavender',
            align='left',
            font=dict(color='black')  # Встановлюємо колір тексту в клітинках
        ))
    ])
    fig.update_layout(width=800, height=400)
    st.plotly_chart(fig)


# Функція для побудови Plotly таблиці для ключових слів
def visualize_keywords_changes(keywords_changes):
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=["Ключове слово", "Зміна", "Було", "Стало"],
            fill_color='paleturquoise',
            align='left',
            font=dict(color='black')  # Встановлюємо чорний колір тексту заголовка
        ),
        cells=dict(
            values=[
                keywords_changes['Ключове слово'],
                keywords_changes['Зміна'],
                keywords_changes['Було'],
                keywords_changes['Стало']
            ],
            fill_color='lavender',
            align='left',
            font=dict(color='black')  # Встановлюємо чорний колір тексту в клітинках
        ))
    ])
    fig.update_layout(width=800, height=400)
    st.plotly_chart(fig)


# Функція для порівняння контенту і візуалізації змін за допомогою Plotly
def visualize_content_changes(content_before, content_after):

    # Розбиваємо контент на рядки
    before_lines = content_before.splitlines()
    after_lines = content_after.splitlines()

    # Створюємо об'єкт HtmlDiff
    differ = difflib.HtmlDiff(wrapcolumn=50)

    # Генеруємо HTML з підсвіченими змінами
    diff_html = differ.make_file(before_lines, after_lines, fromdesc='Було', todesc='Стало')

    # Відображаємо HTML у Streamlit
    st.subheader("Порівняння контенту:")
    components.html(diff_html, height=600,scrolling=True)


# Оновлена функція для вилучення ключових слів і кількості їх повторень
def extract_keywords(row):
    if pd.isna(row) or not row.strip():
        return {}
    entries = row.split(',')
    keywords_dict = {}
    for entry in entries:
        entry = entry.strip()
        match = re.match(r'^\s*(?P<keyword>.*?)\s*-\s*(?P<count>\d+)\s*разів', entry)
        if match:
            keyword = match.group('keyword').strip().lower()
            count = int(match.group('count'))
            if keyword in keywords_dict:
                keywords_dict[keyword] += count
            else:
                keywords_dict[keyword] = count
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
    # Перетворення 'date_checked' у формат datetime
    df['date_checked'] = pd.to_datetime(df['date_checked'])

    fig = go.Figure()

    # Проходимо по всім унікальним URL
    for url in df['url'].unique():
        url_data = df[df['url'] == url]
        fig.add_trace(go.Scatter(
            x=url_data['date_checked'],
            y=url_data['keywords_count'],
            mode='lines+markers',
            name=url,
            hoverinfo='text',
            hovertext=[
                f"Дата: {date.strftime('%Y-%m-%d')}<br>Кількість ключових слів: {count}"
                for date, count in zip(url_data['date_checked'], url_data['keywords_count'])
            ]
        ))

    # Додаємо пояснення до графіка
    fig.update_layout(
        title={
            'text': f'Тренд кількості ключових слів для {competitor_name}',
            'y':0.9,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title='Дата',
        yaxis_title='Кількість ключових слів',
        legend_title='URL',
        xaxis=dict(
            tickformat='%Y-%m-%d',
            tickangle=45
        ),
        yaxis=dict(
            tickmode='linear',
            dtick=1  # Показуємо тільки цілі числа
        ),
        hovermode='x unified',
        annotations=[
            dict(
                xref='paper',
                yref='paper',
                x=0,
                y=-0.2,
                showarrow=False,
                font=dict(size=12)
            )

        ]
    )

    st.plotly_chart(fig, use_container_width=True)


# Функція для побудови історичного графіка по ключовому слову
def plot_keyword_history(df, keyword, selected_url, chart_type):
    # Фільтруємо дані по обраному URL
    url_data = df[df['url'] == selected_url].copy()
    if url_data.empty:
        st.error(f"Немає даних для URL: {selected_url}")
        return

    # Перетворення дат на datetime
    url_data['date_checked'] = pd.to_datetime(url_data['date_checked'], errors='coerce')

    # Створюємо колонку з кількістю повторень ключового слова
    url_data['keyword_count'] = url_data['keywords_found'].apply(
        lambda row: extract_keywords(row).get(keyword.lower(), 0) if pd.notna(row) else 0
    )

    # Фільтруємо дані, залишаючи лише ті рядки, де ключове слово присутнє
    url_data = url_data[url_data['keyword_count'] > 0]

    # Якщо після фільтрації даних немає, повідомляємо користувача
    if url_data.empty:
        st.warning(f"Немає даних для ключового слова '{keyword}' на обраному URL.")
        return

    # Побудова графіка
    fig = go.Figure()

    if chart_type == 'Line Chart':
        fig.add_trace(go.Scatter(
            x=url_data['date_checked'],
            y=url_data['keyword_count'],
            mode='lines+markers',
            name=selected_url,
            hoverinfo='text',
            hovertext=[
                f"Дата: {date.strftime('%Y-%m-%d')}<br>Кількість повторень: {count}"
                for date, count in zip(url_data['date_checked'], url_data['keyword_count'])
            ]
        ))
    elif chart_type == 'Bar Chart':
        fig.add_trace(go.Bar(
            x=url_data['date_checked'],
            y=url_data['keyword_count'],
            name=selected_url,
            text=url_data['keyword_count'],
            textposition='auto',
            hoverinfo='text',
            hovertext=[
                f"Дата: {date.strftime('%Y-%m-%d')}<br>Кількість повторень: {count}"
                for date, count in zip(url_data['date_checked'], url_data['keyword_count'])
            ]
        ))

    # Додаємо пояснення до графіка
    fig.update_layout(
        title=f'Історичний тренд для ключового слова: {keyword}',
        xaxis_title='Дата',
        yaxis_title='Кількість повторень',
        xaxis=dict(tickformat='%Y-%m-%d', tickangle=45),
        annotations=[
            dict(
                xref='paper',
                yref='paper',
                x=0,
                y=-0.2,
                showarrow=False,
                font=dict(size=12)
            )
        ]
    )

    st.plotly_chart(fig, use_container_width=True)


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

# Налаштування сторінки
st.set_page_config(page_title="Change Tracker", page_icon="🔍")


def get_competitors_from_db(conn):
    query = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_name LIKE '%_com';
    """

    # Виконуємо запит і отримуємо список таблиць-конкурентів
    competitor_tables = pd.read_sql(query, conn)['table_name'].tolist()
    return competitor_tables


# Функція для отримання даних з таблиці content_changes з можливістю сортування і фільтрації
def get_content_changes(conn, selected_competitor=None, start_date=None, end_date=None):
    query = "SELECT * FROM content_changes WHERE 1=1"

    # Додаємо фільтрацію за конкурентом
    if selected_competitor:
        query += f" AND competitor_name = '{selected_competitor}'"

    # Додаємо фільтрацію за датами
    if start_date and end_date:
        query += f" AND change_date BETWEEN '{start_date}' AND '{end_date}'"

    query += " ORDER BY change_date ASC"  # Сортуємо за датою

    # Виконуємо запит до бази та перетворюємо результати у DataFrame
    df = pd.read_sql(query, conn)
    return df


# Функція для відображення таблиці змін у Streamlit
def render_content_changes_table(conn):
    st.title("Таблиця змін контенту")

    # Отримуємо список конкурентів для фільтрації
    competitors = pd.read_sql("SELECT DISTINCT competitor_name FROM content_changes", conn)['competitor_name'].tolist()

    # Вибір конкурента для фільтрації
    selected_competitor = st.selectbox("Виберіть конкурента", ["Всі конкуренти"] + competitors)

    # Фільтр по датах
    date_range = pd.read_sql("SELECT MIN(change_date) as min_date, MAX(change_date) as max_date FROM content_changes", conn).iloc[0]
    min_date, max_date = date_range['min_date'], date_range['max_date']

    start_date = st.date_input('Початкова дата', min_date, min_value=min_date, max_value=max_date)
    end_date = st.date_input('Кінцева дата', max_date, min_value=min_date, max_value=max_date)

    if start_date > end_date:
        st.error('Початкова дата не може бути пізніше кінцевої дати.')
        return

    # Якщо вибрано "Всі конкуренти", то не фільтруємо за конкурентом
    if selected_competitor == "Всі конкуренти":
        selected_competitor = None

    # Отримуємо дані з таблиці content_changes з урахуванням фільтрів
    df = get_content_changes(conn, selected_competitor, start_date, end_date)

    # Відображаємо таблицю у Streamlit
    if not df.empty:
        st.dataframe(df)
    else:
        st.warning("Немає змін для відображення.")




# Основна функція для відображення даних у Streamlit
def main():
    # Підключаємося до бази даних
    conn = connect_to_db()

    if conn:
        # Додаємо бічну панель для навігації між сторінками
        st.sidebar.title("Навігація")

        # Список сторінок
        pages = ["Візуалізація змін контенту",
                 "Загальна кількість ключових слів",
                 "Порівняння ключових слів між конкурентами",
                 "Контент сторінки з підсвіченими ключовими словами",
                 "Порівняння контенту",
                 "Таблиця змін"]

        # Вибір сторінки через кнопки на бічній панелі
        page_selection = st.sidebar.radio("Оберіть сторінку", pages)

        # Відображення контенту в залежності від вибору сторінки
        if page_selection == "Візуалізація змін контенту":
            render_content_change_visualization(conn)
        elif page_selection == "Загальна кількість ключових слів":
            render_keyword_count(conn)
        elif page_selection == "Порівняння ключових слів між конкурентами":
            render_keyword_comparison(conn)
        elif page_selection == "Контент сторінки з підсвіченими ключовими словами":
            render_page_content_with_keywords(conn)
        elif page_selection == "Порівняння контенту":
            render_content_comparison(conn)
        elif page_selection == "Таблиця змін":  # Відображаємо таблицю змін з фільтрами
            render_content_changes_table(conn)


# Функції для кожної сторінки
import time

def render_content_change_visualization(conn):
    st.title("Візуалізація змін контенту")

    # Отримуємо список конкурентів
    with st.spinner('Завантаження списку конкурентів...'):
        time.sleep(2)  # Затримка для тестування
        competitors = get_competitors_from_content_changes(conn)

    competitor = st.selectbox("Виберіть конкурента", competitors, key="content_competitor_selectbox")

    # Перевіряємо, чи вибраний чекбокс
    view_all = st.checkbox("Показати всі зміни конкурента", key="content_view_all_checkbox")

    if view_all:
        # Показуємо всі зміни конкурента
        with st.spinner('Завантаження даних про зміни...'):
            time.sleep(2)  # Затримка для тестування
            query = "SELECT change_date FROM content_changes WHERE competitor_name = %s"
            df = pd.read_sql(query, conn, params=[competitor])

        if not df.empty:
            years = sorted(pd.to_datetime(df['change_date']).dt.year.unique())
            selected_year = st.selectbox("Оберіть рік", years, key="year_selectbox")
            st.subheader(f"Загальні зміни для {competitor} у {selected_year} році")
            render_contribution_chart_by_months(df, selected_year, conn, competitor)
        else:
            st.info("Немає змін для цього конкурента.")
    else:
        # Якщо не вибрано "Показати всі зміни конкурента", вибираємо сторінку
        with st.spinner('Завантаження списку сторінок...'):
            time.sleep(2)  # Затримка для тестування
            page_query = "SELECT DISTINCT url FROM content_changes WHERE competitor_name = %s"
            pages = pd.read_sql(page_query, conn, params=[competitor])['url'].tolist()

        if not pages:
            st.info("Немає доступних сторінок для цього конкурента.")
        else:
            selected_page = st.selectbox("Виберіть сторінку", pages, key="content_page_selectbox")

            # Показуємо зміни для вибраної сторінки
            with st.spinner('Завантаження даних про зміни...'):
                time.sleep(2)  # Затримка для тестування
                query = "SELECT change_date FROM content_changes WHERE competitor_name = %s AND url = %s"
                df = pd.read_sql(query, conn, params=[competitor, selected_page])

            if not df.empty:
                years = sorted(pd.to_datetime(df['change_date']).dt.year.unique())
                selected_year = st.selectbox("Оберіть рік", years, key="year_selectbox")
                st.subheader(f"Зміни для {competitor} на сторінці {selected_page} у {selected_year} році")
                render_contribution_chart_by_months(df, selected_year, conn, competitor, selected_page)
            else:
                st.info("Немає змін для цієї сторінки.")


def render_keyword_count(conn):
    st.title("Загальна кількість ключових слів")
    # Отримуємо список конкурентів через функцію get_competitors_from_db
    competitors = get_competitors_from_db(conn)

    competitor_name = st.selectbox("Виберіть конкурента", competitors, key="keyword_competitor_selectbox")

    with st.spinner('Завантаження даних...'):
        df = get_keyword_data(conn, competitor_name)

    if not df.empty:
        df['date_checked'] = pd.to_datetime(df['date_checked'])

        # Фільтр по датах
        min_date = df['date_checked'].min().date()
        max_date = df['date_checked'].max().date()
        start_date = st.date_input('Початкова дата', min_date, min_value=min_date, max_value=max_date, key="keyword_start_date")
        end_date = st.date_input('Кінцева дата', max_date, min_value=min_date, max_value=max_date, key="keyword_end_date")

        if start_date > end_date:
            st.error('Початкова дата не може бути пізніше кінцевої дати.')
            return

        df = df[(df['date_checked'].dt.date >= start_date) & (df['date_checked'].dt.date <= end_date)]

        selected_urls = st.multiselect('Виберіть URL', df['url'].unique(), key="keyword_url_multiselect")

        if selected_urls:
            df = df[df['url'].isin(selected_urls)]

            if df.empty:
                st.warning("Немає даних для вибраних URL та дат.")
                return

            st.subheader(f'Тренд кількості ключових слів для {competitor_name}')
            plot_keyword_trend(df, competitor_name)

            selected_url_for_keywords = st.selectbox('Виберіть URL для перегляду знайдених ключових слів',
                                                     df['url'].unique(), key="keyword_url_selectbox")

            if selected_url_for_keywords:
                selected_page_data = df[df['url'] == selected_url_for_keywords].iloc[0]
                if selected_page_data['keywords_found'] and isinstance(selected_page_data['keywords_found'], str):
                    keywords_dict = extract_keywords(selected_page_data['keywords_found'])

                    st.write(f"**Знайдені ключові слова на {selected_url_for_keywords}:**")
                    st.write(keywords_dict)

                    selected_keywords = st.multiselect('Виберіть ключові слова для аналізу історії',
                                                       list(keywords_dict.keys()),
                                                       key="keyword_select_multiselect")


                    if selected_keywords:
                        chart_type = st.selectbox("Тип графіка",
                                                  ['Line Chart', 'Bar Chart'], key="keyword_chart_type_selectbox")
                        for keyword in selected_keywords:
                            st.subheader(f'Історія для ключового слова: {keyword}')
                            keyword_history_df = get_keyword_history(conn, competitor_name, keyword)
                            if not keyword_history_df.empty:
                                plot_keyword_history(keyword_history_df, keyword, selected_url_for_keywords,
                                                     chart_type)
                            else:
                                st.warning(f"Немає даних для ключового слова: {keyword}")
                else:
                    st.warning("Ключові слова не знайдено для вибраного URL.")
        else:
            st.warning("Будь ласка, оберіть хоча б один URL у фільтрах.")
    else:
        st.warning("Немає даних для вибраного конкурента.")


def render_keyword_comparison(conn):
    st.title("Порівняння ключових слів між конкурентами")
    # Отримуємо список конкурентів через функцію get_competitors_from_db
    competitors = get_competitors_from_db(conn)

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


def render_page_content_with_keywords(conn):
    st.title("Контент сторінки з підсвіченими ключовими словами")
    # Отримуємо список конкурентів через функцію get_competitors_from_db
    competitors = get_competitors_from_db(conn)

    competitor_name_content = st.selectbox("Виберіть конкурента для перегляду контенту", competitors,
                                           key="content_competitor_selectbox_2")

    df_content = get_keyword_data(conn, competitor_name_content)

    if not df_content.empty:
        # Вибір URL для перегляду контенту
        selected_url_for_content = st.selectbox('Виберіть URL для перегляду контенту',
                                                df_content['url'].unique(), key="content_url_selectbox_2")

        # Вибір дати
        selected_date_for_content = st.selectbox('Виберіть дату',
                                                 df_content[df_content['url'] == selected_url_for_content][
                                                     'date_checked'].dt.date.unique(),
                                                 key="content_date_selectbox")

        if selected_date_for_content:
            # Фільтрація даних за URL та датою
            page_content_data = df_content[(df_content['url'] == selected_url_for_content) & (
                    df_content['date_checked'].dt.date == selected_date_for_content)]

            # Отримання контенту сторінки
            page_content = page_content_data['content'].values[0]
            keywords_found = page_content_data['keywords_found'].values[0]

            # Обробка знайдених ключових слів
            keywords_dict = extract_keywords(keywords_found)
            highlighted_content = highlight_keywords(page_content, list(keywords_dict.keys()))

            # Відображення контенту з підсвіченими ключовими словами
            st.markdown(f"<div style='white-space: pre-wrap; padding: 15px;'>{highlighted_content}</div>",
                        unsafe_allow_html=True)


def render_content_comparison(conn):
    st.title("Порівняння контенту")
    # Отримуємо список конкурентів через функцію get_competitors_from_db
    competitors = get_competitors_from_db(conn)

    selected_competitor = st.selectbox('Виберіть конкурента', competitors)

    if selected_competitor:
        pages = get_pages_for_competitor(conn, selected_competitor)
        selected_page = st.selectbox('Виберіть сторінку', pages)

        if selected_page:
            # Вибір двох дат для порівняння
            dates = get_dates_for_page(conn, selected_competitor, selected_page)

            if dates:
                # Перетворення дат в формат datetime для віджета
                formatted_dates = [pd.to_datetime(date).date() for date in dates]

                # Вибір дат через основну область
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
                            st.info("Змін у метаданих не знайдено.")

                        # Перевірка на наявність змін у контенті
                        if data1['content'].values[0] != data2['content'].values[0]:
                            st.subheader("Зміни в контенті:")
                            visualize_content_changes(data1['content'].values[0], data2['content'].values[0])
                        else:
                            st.info("Змін у контенті не знайдено.")

                        # Порівняння ключових слів
                        if data1['keywords_found'].values[0] and data2['keywords_found'].values[0]:
                            keywords_comparison = compare_keywords(data1['keywords_found'].values[0],
                                                                   data2['keywords_found'].values[0])
                            if not keywords_comparison.empty:
                                st.subheader("Зміни в ключових словах:")
                                visualize_keywords_changes(keywords_comparison)
                            else:
                                st.info("Змін у ключових словах не знайдено.")

                        # Порівняння кількості ключових слів
                        if data1['keywords_count'].values[0] != data2['keywords_count'].values[0]:
                            st.subheader("Зміни в кількості ключових слів:")
                            st.table(pd.DataFrame({
                                'Було': [data1['keywords_count'].values[0]],
                                'Стало': [data2['keywords_count'].values[0]]
                            }))
                        else:
                            st.info("Змін у кількості ключових слів не знайдено.")
                    else:
                        st.warning("Для обраних дат немає даних для порівняння.")
                else:
                    st.warning("Оберіть дві різні дати для порівняння.")
            else:
                st.info("Немає доступних дат для цієї сторінки.")


if __name__ == "__main__":
    main()