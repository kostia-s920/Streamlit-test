import tempfile
import base64
import plotly.graph_objects as go
import re
import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import difflib
import streamlit.components.v1 as components
import requests
from bs4 import BeautifulSoup
import json
import logging

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
                text="Цей графік показує, як змінюється загальна кількість ключових слів на сторінках конкурента з часом.",
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
                text="Цей графік показує, як змінювалася кількість використань ключового слова на сторінці з часом.",
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

# Новий функціонал пошук в гугл та додавання АРІ ChatGPT
#
# Логування для відстеження запитів і відповідей
logging.basicConfig(filename='api_usage.log', level=logging.INFO)


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

# Функція для отримання тегу для обраного ключового слова
def get_tag_for_keyword(connection, keyword):
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT tag FROM keywords WHERE keyword = %s', (keyword,))
        result = cursor.fetchone()
        cursor.close()
        if result:
            return result[0]
        else:
            return None
    except Exception as e:
        st.error(f"Помилка при отриманні тегу для ключового слова '{keyword}': {e}")
        return None

# Функція для отримання ключових слів за тегом
def get_keywords_by_tag(connection, tag):
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT keyword FROM keywords WHERE tag = %s', (tag,))
        keywords = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return keywords
    except Exception as e:
        st.error(f"Помилка при отриманні ключових слів за тегом '{tag}': {e}")
        return []

# Функція для отримання використання API
def get_api_usage(connection, today_str):
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT count FROM api_usage WHERE date = %s', (today_str,))
        result = cursor.fetchone()
        if result:
            cursor.close()
            return result[0]
        else:
            # Якщо запису немає, створити його з count=0
            cursor.execute('INSERT INTO api_usage (date, count) VALUES (%s, %s)', (today_str, 0))
            connection.commit()
            cursor.close()
            return 0
    except Exception as e:
        st.error(f"Помилка при отриманні використання API: {e}")
        return 0

# Функція для оновлення використання API
def update_api_usage(connection, today_str, increment=1):
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT count FROM api_usage WHERE date = %s', (today_str,))
        result = cursor.fetchone()
        if result:
            new_count = result[0] + increment
            cursor.execute('UPDATE api_usage SET count = %s WHERE date = %s', (new_count, today_str))
        else:
            cursor.execute('INSERT INTO api_usage (date, count) VALUES (%s, %s)', (today_str, increment))
        connection.commit()
        cursor.close()
    except Exception as e:
        st.error(f"Помилка при оновленні використання API: {e}")

# Функція для отримання історії використання API
def get_api_usage_history(connection):
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT date, count FROM api_usage ORDER BY date ASC')
        data = cursor.fetchall()
        cursor.close()
        return data
    except Exception as e:
        st.error(f"Помилка при отриманні історії використання API: {e}")
        return []

# Функція для виконання пошуку
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

# Функція для отримання контенту сторінки
def fetch_page_content(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        st.warning(f"Не вдалося завантажити сторінку {url}: {e}")
        return ""

# Функція для аналізу контенту сторінки
def analyze_page_content(html_content, related_keywords):
    soup = BeautifulSoup(html_content, 'html.parser')

    # Отримання тексту з Title
    title = soup.title.string if soup.title and soup.title.string else ''

    # Отримання тексту з метатегу Description
    meta_description = ''
    meta = soup.find('meta', attrs={'name': 'description'})
    if meta and meta.get('content'):
        meta_description = meta.get('content')

    # Отримання тексту з заголовків H1, H2, H3
    headers_text = ''
    for header_tag in ['h1', 'h2', 'h3']:
        headers = soup.find_all(header_tag)
        headers_text += ' '.join([header.get_text(separator=' ', strip=True) for header in headers])

    # Отримання основного тексту сторінки
    body_text = soup.get_text(separator=' ', strip=True)

    # Функція для підрахунку кількості входжень ключових слів
    def count_occurrences(text, keyword):
        if not text:
            return 0
        return len(re.findall(r'\b' + re.escape(keyword.lower()) + r'\b', text.lower()))

    # Підрахунок кількості ключових слів у різних секціях
    counts_title = {kw: count_occurrences(title, kw) for kw in related_keywords if count_occurrences(title, kw) > 0}
    counts_description = {kw: count_occurrences(meta_description, kw) for kw in related_keywords if count_occurrences(meta_description, kw) > 0}
    counts_headers = {kw: count_occurrences(headers_text, kw) for kw in related_keywords if count_occurrences(headers_text, kw) > 0}
    counts_content = {kw: count_occurrences(body_text, kw) for kw in related_keywords if count_occurrences(body_text, kw) > 0}

    # Підсумкова кількість ключових слів
    total_keyword_count = sum(counts_title.values()) + sum(counts_description.values()) + sum(counts_headers.values()) + sum(counts_content.values())

    # Формування результатів аналізу
    analysis_results = {
        'title': title,
        'description': meta_description,
        'headers': headers_text,
        'body': body_text,
        'counts_title': counts_title,
        'counts_description': counts_description,
        'counts_headers': counts_headers,
        'counts_content': counts_content,
        'total_keywords': total_keyword_count
    }

    return analysis_results

# Ініціалізація session_state
if 'search_results' not in st.session_state:
    st.session_state['search_results'] = []
if 'related_keywords' not in st.session_state:
    st.session_state['related_keywords'] = []

# Функція для перевірки наявності таблиці та її створення, якщо вона відсутня
def create_page_analysis_table_if_not_exists(connection):
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'page_analysis'
            );
        """)
        table_exists = cursor.fetchone()[0]

        if not table_exists:
            cursor.execute('''
                CREATE TABLE page_analysis (
                    id SERIAL PRIMARY KEY,
                    url TEXT NOT NULL,
                    title TEXT,
                    description TEXT,
                    headers TEXT,
                    body TEXT,
                    keyword_counts JSONB,
                    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            connection.commit()
            st.success("Таблиця 'page_analysis' успішно створена.")
        else:
            st.info("Таблиця 'page_analysis' вже існує, пропускаємо створення.")
        cursor.close()
    except Exception as e:
        st.error(f"Помилка при створенні або перевірці таблиці: {e}")

# Функція для збереження результатів аналізу в базу даних
def save_analysis_results_to_db(connection, url, analysis_results):
    try:
        cursor = connection.cursor()
        cursor.execute('''
            INSERT INTO page_analysis (url, title, description, headers, body, keyword_counts, analyzed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (
            url,
            analysis_results['title'],
            analysis_results['description'],
            analysis_results['headers'],
            analysis_results['body'],
            json.dumps({
                'counts_title': analysis_results['counts_title'],
                'counts_description': analysis_results['counts_description'],
                'counts_headers': analysis_results['counts_headers'],
                'counts_content': analysis_results['counts_content']
            }),
            datetime.now()
        ))
        connection.commit()
        cursor.close()
        st.success(f"Результати для сторінки {url} успішно збережені в базі даних.")
    except Exception as e:
        st.error(f"Помилка при збереженні результатів аналізу: {e}")


# Функція для отримання всіх збережених результатів аналізу з бази даних
def get_all_saved_results_from_db(connection):
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT title, description, headers, body, keyword_counts FROM page_analysis')
        results = cursor.fetchall()
        cursor.close()
        return results
    except Exception as e:
        st.error(f"Помилка при отриманні результатів аналізу з бази даних: {e}")
        return []



# Функція для виконання запиту до OpenAI API через requests
def get_openai_response(api_key, model, prompt):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model,  # Використовуємо модель, вибрану користувачем
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)

    if response.status_code == 200:
        return response.json()
    else:
        return f"Error: {response.status_code}, {response.text}"

# Функція для генерації промпту для OpenAI API
def generate_api_prompt_for_single_page(user_page_results, competitor_pages, keyword_group):
    """
    Генерує промпт для OpenAI для покращення сторінки користувача на основі аналізу конкурентів.

    :param user_page_results: результати аналізу сторінки користувача
    :param competitor_pages: результати аналізу конкурентних сторінок
    :param keyword_group: ключові слова для різних секцій
    :return: промпт для OpenAI
    """
    prompt = """
    Terms of reference for SEO optimization based on page analysis. Focus on the following aspects: 
    meta description, headings (H1, H2, H3), main content, and FAQ section. Use the following group of keywords 
    for each section to improve the user's page.
    """

    # Дані сторінки користувача
    title = user_page_results['title']
    description = user_page_results['description']
    headers = user_page_results['headers']
    total_keywords = user_page_results['total_keywords']

    # Формуємо промпт для оптимізації сторінки користувача
    prompt += f"""
    1. **Page Title**:
    {title}

    Use these keywords to optimize your title: {keyword_group['title']}.
    Make it more attractive to search engines by considering the keyword group.

    2. **Meta Description**:
    {description}

    Use these keywords to improve your meta description: {keyword_group['description']}.
    Make it more informative, taking into account the keywords, and add a more detailed description of the page.

    3. **H1, H2, H3 headings**:
    {headers}

    Use these keywords to optimize your headings: {keyword_group['headers']}.
    Consider adding keywords to your headers to increase relevance. Describe how they can be changed or improved 
    to increase search engine visibility.

    4. **FAQ**:
    {'FAQ not found' if 'faq' not in user_page_results else user_page_results['faq']}

    Use these keywords to optimize your FAQ block: {keyword_group.get('faq', 'No FAQ keywords provided')}.
    Suggest how the FAQ can be expanded or improved to cover more questions and answers related to the keywords.

    5. **Total number of keywords on the page**: {total_keywords}
    """

    # Враховуємо порівняльний аналіз з конкурентами
    prompt += "\nBased on the competitor analysis, improve the user's page with the following insights:\n\n"

    # Проходимо по всіх конкурентних сторінках і додаємо інформацію
    for idx, competitor in enumerate(competitor_pages, 1):
        competitor_title = competitor['title']
        competitor_description = competitor['description']
        competitor_headers = competitor['headers']
        competitor_body = competitor['body'][:500]  # Перші 500 символів контенту для порівняння
        competitor_total_keywords = competitor['total_keywords']

        prompt += f"""
        **Competitor {idx}:**
        - Title: {competitor_title}
        - Meta Description: {competitor_description}
        - Headers: {competitor_headers}
        - Main Content: {competitor_body}...
        - Total Keywords: {competitor_total_keywords}
        \n"""

    prompt += "\nBased on this analysis, prepare a technical task for SEO optimization of the user's page. Use keywords in each section to achieve the best SEO results."

    return prompt

#
#


# Основна функція для відображення даних у Streamlit
def main():
    # Налаштування сторінки
    st.set_page_config(page_title="SEO та Аналіз Змін Контенту", page_icon="🔍", layout="wide")

    # Логування для відстеження запитів і відповідей
    logging.basicConfig(filename='api_usage.log', level=logging.INFO)

    # Підключення до бази даних
    conn = connect_to_db()
    if conn is None:
        st.stop()

    # Бічна панель для навігації
    st.sidebar.title("Навігація")
    pages = [
        "Візуалізація змін контенту",
        "Загальна кількість ключових слів",
        "Порівняння ключових слів між конкурентами",
        "Контент сторінки з підсвіченими ключовими словами",
        "Порівняння контенту",
        "Google Custom Search Аналізатор"
    ]
    page_selection = st.sidebar.radio("Оберіть сторінку", pages)

    # Відображення контенту залежно від вибору сторінки
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
    elif page_selection == "Google Custom Search Аналізатор":
        render_google_custom_search_analyzer(conn)

# Функції для кожної сторінки
def render_content_change_visualization(conn):
    st.title("Візуалізація змін контенту")

    # Отримуємо список конкурентів
    with st.spinner('Завантаження списку конкурентів...'):
        competitors = get_competitors_from_content_changes(conn)

    competitor = st.selectbox("Виберіть конкурента", competitors, key="content_competitor_selectbox")

    # Перевіряємо, чи вибраний чекбокс
    view_all = st.checkbox("Показати всі зміни конкурента", key="content_view_all_checkbox")

    if view_all:
        # Показуємо всі зміни конкурента
        with st.spinner('Завантаження даних про зміни...'):
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
            page_query = "SELECT DISTINCT url FROM content_changes WHERE competitor_name = %s"
            pages = pd.read_sql(page_query, conn, params=[competitor])['url'].tolist()

        if not pages:
            st.info("Немає доступних сторінок для цього конкурента.")
        else:
            selected_page = st.selectbox("Виберіть сторінку", pages, key="content_page_selectbox")

            # Показуємо зміни для вибраної сторінки
            with st.spinner('Завантаження даних про зміни...'):
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
# Функція для сторінки Google Custom Search Аналізатор
def render_google_custom_search_analyzer(conn):
    st.title("Google Custom Search Аналізатор")

    # Ліве меню для налаштування
    with st.sidebar:
        st.header("Налаштування API та Бази Даних")
        api_key = st.text_input("API ключ Google", type="password")
        cx = st.text_input("Custom Search Engine ID (CX)")
        openai_api_key = st.text_input("OpenAI API Key", type="password")

        # Вибір моделі OpenAI
        st.subheader("Налаштування OpenAI")
        models = ["gpt-4o-mini", "gpt-4o"]  # Додайте інші моделі за потреби
        selected_model = st.selectbox("Оберіть модель OpenAI", options=models, index=0)

        st.markdown("---")

        # Вибір регіону пошуку
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
        }
        selected_region = st.selectbox("Оберіть регіон пошуку", options=list(regions.keys()), index=0)
        region_code = regions[selected_region]
        st.markdown("---")

    if not api_key or not cx or not openai_api_key:
        st.warning("Будь ласка, введіть ваші API ключі та CX у бічному меню.")
        st.stop()

    # Перевірка та створення таблиці, якщо вона не існує
    create_page_analysis_table_if_not_exists(conn)

    # Отримання поточної дати
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Отримання використання API
    current_usage = get_api_usage(conn, today_str)
    api_limit = 100

    # Відображення використання API
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Використано API-запитів сьогодні", f"{current_usage}/{api_limit}")

    # Отримання ключових слів
    keywords = get_keywords(conn)

    # Додамо змінну для відстеження введеного ключового слова
    manual_search = False

    # Поле для введення ключового слова від користувача
    st.subheader("Введіть своє ключове слово для пошуку")
    user_keyword = st.text_input("Ключове слово", "")

    if st.button("Виконати пошук за введеним ключовим словом"):
        manual_search = True  # Виконаний ручний пошук
        if current_usage >= api_limit:
            st.error("Ви досягли ліміту використання API на сьогодні. Спробуйте завтра.")
            st.stop()

        if not user_keyword:
            st.warning("Введіть ключове слово для пошуку.")
            st.stop()

        # Виконання пошуку за введеним ключовим словом
        search_results = perform_search(user_keyword, api_key, cx, region=region_code)
        if not search_results:
            st.info("Не вдалося знайти результати за цим ключовим словом.")
            st.stop()

        # Збереження результатів у session_state
        st.session_state['search_results'] = search_results

        # Оновлення використання API
        update_api_usage(conn, today_str, increment=1)
        current_usage += 1

        # Відображення результатів пошуку
        results_data = []
        for idx, item in enumerate(search_results, 1):
            url = item.get('link')
            title = item.get('title') if item.get('title') else ''
            snippet = item.get('snippet') if item.get('snippet') else ''
            results_data.append({
                '№': idx,
                'Назва': title,
                'Посилання': url,
                'Опис': snippet,
            })

        # Збереження результатів у session_state
        st.session_state['search_results'] = results_data

    if not keywords:
        st.info("Таблиця 'keywords' порожня. Додайте ключові слова до бази даних.")
        conn.close()
        st.stop()

    # Вибір ключового слова
    selected_keyword = st.selectbox("Оберіть ключове слово для пошуку", keywords)

    # Кнопка для запуску пошуку за вибраним ключовим словом
    if st.button("Виконати пошук"):
        if current_usage >= api_limit:
            st.error("Ви досягли ліміту використання API на сьогодні. Спробуйте завтра.")
            st.stop()

        # Отримання тегу для обраного ключового слова
        tag = get_tag_for_keyword(conn, selected_keyword)
        if not tag:
            st.error(f"Не вдалося знайти тег для ключового слова '{selected_keyword}'.")
            st.stop()

        # Отримання пов'язаних ключових слів за тегом
        related_keywords = get_keywords_by_tag(conn, tag)
        if not related_keywords:
            st.error(f"Не вдалося знайти пов'язані ключові слова для тегу '{tag}'.")
            st.stop()

        # Збереження related_keywords у session_state
        st.session_state['related_keywords'] = related_keywords

        with st.spinner('Виконується пошук...'):
            # Виконання пошуку
            search_results = perform_search(selected_keyword, api_key, cx, region=region_code)
            if not search_results:
                st.info("Не вдалося знайти результати за цим ключовим словом.")
                st.stop()

            # Оновлення використання API
            update_api_usage(conn, today_str, increment=1)
            current_usage += 1

        # Аналіз результатів пошуку
        results_data = []
        all_analysis_results = []
        for idx, item in enumerate(search_results, 1):
            url = item.get('link')
            title = item.get('title') if item.get('title') else ''
            snippet = item.get('snippet') if item.get('snippet') else ''

            # Отримання контенту сторінки
            html_content = fetch_page_content(url)
            if not html_content:
                analysis_results = {
                    'counts_title': {},
                    'counts_description': {},
                    'counts_headers': {},
                    'counts_content': {},
                    'total_keywords': 0
                }
            else:
                analysis_results = analyze_page_content(html_content, related_keywords)

            all_analysis_results.append(analysis_results)

            counts_title = analysis_results['counts_title']
            counts_description = analysis_results['counts_description']
            counts_headers = analysis_results['counts_headers']
            counts_content = analysis_results['counts_content']
            total_keywords = analysis_results['total_keywords']

            # Додавання даних до списку
            results_data.append({
                '№': idx,
                'Назва': title,
                'Посилання': url,
                'Опис': snippet,
                'Кількість в Title': sum(counts_title.values()),
                'Кількість в Description': sum(counts_description.values()),
                'Кількість в H1/H2/H3': sum(counts_headers.values()),
                'Кількість в Content': sum(counts_content.values()),
                'Загальна кількість ключових слів': total_keywords
            })

        # Збереження результатів у session_state
        st.session_state['search_results'] = results_data

    # Перевірка, чи є пошукові результати в session_state
    if 'search_results' in st.session_state:
        search_results = st.session_state['search_results']
    else:
        search_results = []

    # Відображення результатів пошуку
    if st.session_state['search_results']:
        results_data = st.session_state['search_results']

        df_results = pd.DataFrame(results_data)
        # Переміщення № до першого стовпця
        cols = df_results.columns.tolist()
        cols = [cols[0]] + sorted(cols[1:], key=lambda x: (x != 'Посилання', x))
        df_results = df_results[cols]

        st.success(f"Знайдено {len(results_data)} результатів:")
        st.dataframe(df_results, use_container_width=True)

        # Додавання можливості вибору сторінки для детального перегляду
        if not manual_search:
            st.markdown("---")
            st.subheader("Детальний перегляд сторінки")
            selected_result = st.selectbox("Оберіть сторінку для детального перегляду", df_results['Посилання'])

            if selected_result:
                # Знаходимо відповідний запис
                selected_record = next((item for item in results_data if item['Посилання'] == selected_result), None)
                if selected_record:
                    st.markdown(f"### {selected_record['Назва']}")
                    st.markdown(f"**Посилання:** [Перейти]({selected_result})")
                    st.markdown(f"**Опис:** {selected_record['Опис']}")
                    st.markdown("---")

                    # Отримання та аналіз контенту сторінки
                    html_content = fetch_page_content(selected_result)
                    if not html_content:
                        st.warning("Не вдалося завантажити контент сторінки.")
                    else:
                        # Перевірка наявності related_keywords у session_state
                        if 'related_keywords' in st.session_state and st.session_state['related_keywords']:
                            related_keywords = st.session_state['related_keywords']
                            analysis_results = analyze_page_content(html_content, related_keywords)

                            counts_title = analysis_results['counts_title']
                            counts_description = analysis_results['counts_description']
                            counts_headers = analysis_results['counts_headers']
                            counts_content = analysis_results['counts_content']
                            total_keywords = analysis_results['total_keywords']

                            # Створення таблиці з ключовими словами та їх кількістю у різних секціях
                            st.subheader("Кількість ключових слів на сторінці")
                            data = {
                                'Секція': [],
                                'Ключове слово': [],
                                'Кількість': []
                            }
                            for kw, count in counts_title.items():
                                data['Секція'].append('Title')
                                data['Ключове слово'].append(kw)
                                data['Кількість'].append(count)
                            for kw, count in counts_description.items():
                                data['Секція'].append('Description')
                                data['Ключове слово'].append(kw)
                                data['Кількість'].append(count)
                            for kw, count in counts_headers.items():
                                data['Секція'].append('H1/H2/H3')
                                data['Ключове слово'].append(kw)
                                data['Кількість'].append(count)
                            for kw, count in counts_content.items():
                                data['Секція'].append('Content')
                                data['Ключове слово'].append(kw)
                                data['Кількість'].append(count)

                            if any(data['Секція']):
                                df_keyword_counts = pd.DataFrame(data)
                                st.table(df_keyword_counts)
                                st.markdown(f"**Загальна кількість ключових слів:** {total_keywords}")
                            else:
                                st.info("Не знайдено ключових слів на цій сторінці.")
                        else:
                            st.error("Пов'язані ключові слова не збережені. Виконайте пошук спочатку.")
                            st.stop()

                # Додавання можливості введення основного URL для порівняння
                st.subheader("Введіть основне посилання для порівняння")
                main_url = st.text_input("Основне посилання", "")

                if st.button("Зберегти результати та виконати API запит"):
                    if not main_url:
                        st.error("Будь ласка, введіть основне посилання для порівняння.")
                        st.stop()

                    # Отримання контенту основної сторінки
                    main_html_content = fetch_page_content(main_url)
                    if not main_html_content:
                        st.error(f"Не вдалося завантажити контент для основної сторінки: {main_url}")
                    else:
                        # Аналіз контенту основної сторінки
                        related_keywords = st.session_state.get('related_keywords', [])
                        main_analysis_results = analyze_page_content(main_html_content, related_keywords)

                        # Порівняння з конкурентами
                        competitor_pages = []
                        for result in search_results:
                            url = result.get('Посилання')
                            html_content = fetch_page_content(url)
                            if html_content:
                                analysis_results = analyze_page_content(html_content, related_keywords)
                                competitor_pages.append(analysis_results)

                        # Генерація промпту для OpenAI API
                        keyword_group = {
                            'title': related_keywords,
                            'description': related_keywords,
                            'headers': related_keywords,
                            'body': related_keywords,
                            'faq': related_keywords
                        }

                        # Генерація промпту
                        prompt = generate_api_prompt_for_single_page(main_analysis_results, competitor_pages, keyword_group)

                        # Виклик функції для виконання запиту до OpenAI API
                        response = get_openai_response(openai_api_key, selected_model, prompt)

                        # Виведення відповіді
                        st.subheader("Відповідь OpenAI:")
                        if isinstance(response, dict):
                            st.write(response.get('choices', [{}])[0].get('message', {}).get('content', 'Немає відповіді'))
                        else:
                            st.error(response)


if __name__ == "__main__":
    main()