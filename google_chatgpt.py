import streamlit as st
import requests
import psycopg2
from bs4 import BeautifulSoup
import re
import json
import pandas as pd
from datetime import datetime
import logging

# Логування для відстеження запитів і відповідей
logging.basicConfig(filename='api_usage.log', level=logging.INFO)

# Налаштування сторінки
st.set_page_config(page_title="Google Custom Search Аналізатор", layout="wide")

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

# Основна функція Streamlit
def main():
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

    # Підключення до бази даних
    conn = connect_to_db()
    if conn is None:
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
                        prompt = generate_api_prompt_for_single_page(main_analysis_results, competitor_pages,
                                                                     keyword_group)

                        # Виклик функції для виконання запиту до OpenAI API
                        response = get_openai_response(openai_api_key, selected_model, prompt)

                        # Виведення відповіді
                        st.subheader("Відповідь OpenAI:")
                        if isinstance(response, dict):
                            st.write(
                                response.get('choices', [{}])[0].get('message', {}).get('content', 'Немає відповіді'))
                        else:
                            st.error(response)

    # Закриття з'єднання з базою даних
    conn.close()


# Запуск програми
if __name__ == '__main__':
    main()