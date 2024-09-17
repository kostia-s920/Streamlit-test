import streamlit as st
import matplotlib.pyplot as plt
import psycopg2
import pandas as pd
import re
import matplotlib.dates as mdates
from datetime import datetime, timedelta

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

# Функція для отримання даних по ключовим словам із бази даних
def get_keyword_data(conn, competitor_name):
    query = f"""
        SELECT url, keywords_count, keywords_found, content, date_checked 
        FROM {competitor_name}_temp
        ORDER BY date_checked ASC
    """
    df = pd.read_sql(query, conn)
    return df

# Функція для вилучення ключових слів і кількості їх повторень, ігноруючи значення в дужках
def extract_keywords(row):
    pattern = re.findall(r'([\w\s-]+?)\s*-\s*(\d+)\s*разів', row)
    keywords_dict = {match[0].strip(): int(match[1]) for match in pattern}
    return keywords_dict

# Функція для отримання історичних даних по вибраному ключовому слову
def get_keyword_history(conn, competitor_name, keyword):
    query = f"""
        SELECT url, date_checked, keywords_found
        FROM {competitor_name}_temp
        WHERE keywords_found ILIKE %s
        ORDER BY date_checked ASC
    """
    df = pd.read_sql(query, conn, params=[f'%{keyword}%'])
    return df

# Функція для побудови графіка ключових слів
def plot_keyword_trend(df, competitor_name):
    plt.figure(figsize=(10, 6))
    for url in df['url'].unique():
        url_data = df[df['url'] == url]
        plt.plot(url_data['date_checked'], url_data['keywords_count'], label=url)

    plt.title(f'Keyword Count Trend for {competitor_name}')
    plt.xlabel('Date')
    plt.ylabel('Keyword Count')
    plt.legend(loc='best', bbox_to_anchor=(1, 1))
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(plt)

# Функція для побудови історичного графіка по ключовому слову
def plot_keyword_history(df, keyword, selected_url, chart_type):
    plt.figure(figsize=(10, 6))

    # Фільтруємо дані по обраному URL
    url_data = df[df['url'] == selected_url]
    if url_data.empty:
        st.write(f"No data for URL: {selected_url}")
        return

    # Перетворення дат на datetime
    url_data['date_checked'] = pd.to_datetime(url_data['date_checked'], errors='coerce')

    # Використовуємо функцію для вилучення кількості ключових слів
    keyword_counts = url_data['keywords_found'].apply(lambda row: extract_keywords(row).get(keyword, 0))

    # Додаємо графік в залежності від обраного типу графіка
    if chart_type == 'Line Chart':
        plt.plot(url_data['date_checked'], keyword_counts, label=selected_url)
    elif chart_type == 'Bar Chart':
        plt.bar(url_data['date_checked'], keyword_counts)
    elif chart_type == 'Scatter Plot':
        plt.scatter(url_data['date_checked'], keyword_counts)
    elif chart_type == 'Area Chart':
        plt.fill_between(url_data['date_checked'], keyword_counts, label=selected_url, alpha=0.5)
    elif chart_type == 'Step Chart':
        plt.step(url_data['date_checked'], keyword_counts, label=selected_url, where='mid')

    plt.title(f'Historical Trend for Keyword: {keyword}')
    plt.xlabel('Date')
    plt.ylabel('Keyword Occurrences')

    # Форматування осі дати
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.gcf().autofmt_xdate()
    plt.legend(loc='best', bbox_to_anchor=(1, 1))
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(plt)

# Функція для графіка порівняння кількох конкурентів
def plot_comparison(df_list, competitor_names, selected_urls):
    plt.figure(figsize=(10, 6))

    # Проходимо по всім обраним конкурентам та їх сторінкам
    for df, competitor, url in zip(df_list, competitor_names, selected_urls):
        url_data = df[df['url'] == url]
        if not url_data.empty:
            plt.plot(url_data['date_checked'], url_data['keywords_count'], label=f'{competitor}: {url}')
        else:
            st.write(f"No data for {competitor}: {url}")

    plt.title('Keyword Count Comparison')
    plt.xlabel('Date')
    plt.ylabel('Keyword Count')
    plt.legend(loc='best', bbox_to_anchor=(1, 1))
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    st.pyplot(plt)

# Функція для відображення контенту сторінки з підсвічуванням ключових слів
def highlight_keywords(text, keywords):
    if not text:
        return "No content found."
    for keyword in keywords:
        escaped_keyword = re.escape(keyword)  # Захист від спеціальних символів
        text = re.sub(f'({escaped_keyword})', r'<span style="color:red; font-weight:bold;">\1</span>', text, flags=re.IGNORECASE)
    return text


# Додаємо місяці над сіткою
def render_month_labels():
    months = {
        'Jan': 4, 'Feb': 4, 'Mar': 5, 'Apr': 4, 'May': 4, 'Jun': 4,
        'Jul': 5, 'Aug': 4, 'Sep': 4, 'Oct': 5, 'Nov': 4, 'Dec': 5
    }

    months_html = '<div style="display: grid; grid-template-columns: repeat(52, 14px); grid-gap: 2px;">'

    for month, span in months.items():
        months_html += f'<div style="grid-column: span {span}; text-align: center;">{month}</div>'

    months_html += '</div>'

    return months_html


# Основний блок для рендерингу візуалізації
def render_contribution_chart(change_dates):
    st.markdown(
        "<style>.contribution-box{display: inline-block;width: 12px;height: 12px;margin: 2px;background-color: #ebedf0;}.contribution-level-1{background-color: #c6e48b;}.contribution-level-2{background-color: #7bc96f;}.contribution-level-3{background-color: #239a3b;}.contribution-level-4{background-color: #196127;}</style>",
        unsafe_allow_html=True
    )

    change_dates['change_date'] = pd.to_datetime(change_dates['change_date']).dt.date
    changes_by_date = change_dates.groupby('change_date').size()

    start_of_year = pd.to_datetime(f'{datetime.now().year}-01-01').date()
    end_of_year = pd.to_datetime(f'{datetime.now().year}-12-31').date()

    total_days = (end_of_year - start_of_year).days + 1
    days = [start_of_year + timedelta(days=i) for i in range(total_days)]

    week_days = ['Mon', 'Wed', 'Fri']

    chart = []
    for day in days:
        count = changes_by_date.get(day, 0)
        if count == 0:
            level = 'contribution-box'
        elif count <= 1:
            level = 'contribution-box contribution-level-1'
        elif count <= 3:
            level = 'contribution-box contribution-level-2'
        elif count <= 5:
            level = 'contribution-box contribution-level-3'
        else:
            level = 'contribution-box contribution-level-4'
        chart.append(f'<div class="{level}" title="{day} - {count} changes"></div>')

    grid_html = ''
    for week in range(52):
        week_html = '<div style="display: grid; grid-template-rows: repeat(7, 14px); grid-gap: 2px;">'
        for day_index in range(7):
            index = week * 7 + day_index
            if index < len(chart):
                week_html += chart[index]
        week_html += '</div>'
        grid_html += week_html

    week_days_html = '<div style="display: grid; grid-template-rows: repeat(7, 14px); grid-gap: 2px;">'
    for i in range(7):
        if i in [0, 2, 4]:
            week_days_html += f'<div>{week_days[[0, 2, 4].index(i)]}</div>'
        else:
            week_days_html += '<div></div>'
    week_days_html += '</div>'

    st.markdown(render_month_labels(), unsafe_allow_html=True)
    st.markdown(
        f'<div style="display: flex;">{week_days_html}<div style="display: grid; grid-template-columns: repeat(52, 14px); grid-gap: 2px;">{grid_html}</div></div>',
        unsafe_allow_html=True)

# Основна функція для відображення даних у Streamlit
def main():

    # Підключаємося до бази даних
    conn = connect_to_db()

    # Візуалізація змін контенту
    st.title('Візуалізація змін контенту')
    # Крок 1: Вибір конкурента
    competitor = st.selectbox("Виберіть конкурента",
                              ['docebo_com', 'ispringsolutions_com', 'talentlms_com',
                               'paradisosolutions_com'])

    # Додатковий перемикач для вибору режиму перегляду
    view_all = st.checkbox("Показати всі зміни конкурента")

    if view_all:
        # Якщо обрано перегляд всіх змін, виконуємо запит для всіх змін конкурента
        query = f"SELECT change_date FROM content_changes_temp WHERE competitor_name = '{competitor}'"
        df = pd.read_sql(query, conn)

        if not df.empty:
            st.subheader(f"Загальні зміни для {competitor}")
            render_contribution_chart(df)
        else:
            st.write("Немає змін для цього конкурента.")
    else:
        # Якщо перегляд змін для окремих сторінок
        page_query = f"SELECT DISTINCT url FROM content_changes_temp WHERE competitor_name = '{competitor}'"
        pages = pd.read_sql(page_query, conn)['url'].tolist()

        if not pages:
            st.write("Немає доступних сторінок для цього конкурента.")
            return

        page = st.selectbox("Виберіть сторінку", pages)

        # Отримання даних змін для вибраної сторінки
        query = f"SELECT change_date FROM content_changes_temp WHERE competitor_name = '{competitor}' AND url = '{page}'"
        df = pd.read_sql(query, conn)

        if not df.empty:
            # Відображення заголовка сторінки та візуалізація змін, стилізовані для компактного відображення
            st.markdown(f"<p style='font-size:12px;color:gray;'>Зміни для сторінки: {page}</p>",
                        unsafe_allow_html=True)
            render_contribution_chart(df)
        else:
            # Повідомлення про відсутність змін, відображене дрібним шрифтом
            st.markdown("<p style='font-size:10px;color:gray;'>Немає змін для цієї сторінки.</p>",
                        unsafe_allow_html=True)

    st.write("")
    st.markdown("<div style='background-color: lightgray; height: 2px;'></div>", unsafe_allow_html=True)
    st.write("")

    # Keyword Count and Historical Analysis for Competitors
    st.title('Keyword Count and Historical Analysis for Competitors')
    if conn:
        competitors = ['docebo_com', 'ispringsolutions_com', 'talentlms_com', 'paradisosolutions_com']

        # Дозволяємо користувачеві вибрати конкурента для аналізу
        competitor_name = st.selectbox("Select Competitor", competitors, key="competitor_select_1")

        # Отримуємо дані по ключовим словам для вибраного конкурента
        df = get_keyword_data(conn, competitor_name)

        # Фільтр по URL (дозволяємо вибрати 1-5 URL)
        selected_urls = st.multiselect('Select URLs', df['url'].unique(), max_selections=5, key="url_select")

        # Фільтр по датах
        if not df.empty:
            start_date = pd.to_datetime(st.date_input('Start Date', df['date_checked'].min(), key="start_date")).date()
            end_date = pd.to_datetime(st.date_input('End Date', df['date_checked'].max(), key="end_date")).date()

            # Перетворення дати без часу
            df['date_checked'] = pd.to_datetime(df['date_checked']).dt.date

            # Фільтрація за діапазоном дат
            df = df[(df['date_checked'] >= start_date) & (df['date_checked'] <= end_date)]

            if df.empty:
                st.write("No data available for the selected date range.")

        # Фільтруємо дані по вибраним URL
        if selected_urls:
            df = df[df['url'].isin(selected_urls)]
            if df.empty:
                st.write("No data available for the selected URLs.")

        # Додаємо можливість згорнути/розгорнути таблицю
        with st.expander("Click to expand/collapse the data table", expanded=True):
            # Відображаємо таблицю з даними
            st.write(df)

        # Відображаємо графік на основі даних
        if not df.empty:
            st.subheader(f'Keyword Trend for {competitor_name}')
            plot_keyword_trend(df, competitor_name)

        # Вибираємо URL для аналізу знайдених ключових слів
        selected_url_for_keywords = st.selectbox('Select URL to view found keywords', df['url'].unique(), key="keyword_url_select")

        # Показуємо знайдені ключові слова для обраного URL
        if selected_url_for_keywords:
            selected_page_data = df[df['url'] == selected_url_for_keywords].iloc[0]

            # Перевіряємо, чи є ключові слова в записі
            if selected_page_data['keywords_found'] and isinstance(selected_page_data['keywords_found'], str):
                # Витягуємо ключові слова і кількість повторень, ігноруючи значення в дужках
                keywords_dict = extract_keywords(selected_page_data['keywords_found'])

                st.write(f"Found keywords on {selected_url_for_keywords}:")
                st.write(keywords_dict)

                # Вибираємо ключові слова для аналізу їх змін у часі
                selected_keywords = st.multiselect('Select keywords to analyze historical occurrences',
                                                   list(keywords_dict.keys()), key="keyword_multiselect")

                if selected_keywords:
                    # Додамо вибір типу графіка нижче
                    chart_type = st.selectbox(
                        "Select Chart Type",
                        ['Line Chart', 'Bar Chart', 'Scatter Plot', 'Area Chart', 'Step Chart'],
                        key="chart_select"
                    )

                    for keyword in selected_keywords:
                        st.subheader(f'Historical Trend for Keyword: {keyword}')
                        keyword_history_df = get_keyword_history(conn, competitor_name, keyword)
                        if not keyword_history_df.empty:
                            plot_keyword_history(keyword_history_df, keyword, selected_url_for_keywords, chart_type)
                        else:
                            st.write(f"No historical data found for keyword: {keyword}")
            else:
                st.write(f"No keywords found for URL: {selected_url_for_keywords}")

        st.write("")
        st.markdown("<div style='background-color: lightgray; height: 2px;'></div>", unsafe_allow_html=True)
        st.write("")

        # Додаємо можливість порівняння конкурентів
        st.subheader('Comparison of Keywords Between Competitors')

        # Вибір кількох конкурентів
        selected_competitors = st.multiselect("Select Competitors for Comparison", competitors, default=competitors[:2], key="competitors_multiselect")

        # Отримуємо дані для кожного конкурента
        df_list = [get_keyword_data(conn, competitor) for competitor in selected_competitors]

        # Вибір URL для кожного конкурента
        selected_urls_for_comparison = []
        for competitor, df in zip(selected_competitors, df_list):
            selected_url = st.selectbox(f'Select URL for {competitor}', df['url'].unique(), key=f"url_select_{competitor}")
            selected_urls_for_comparison.append(selected_url)

        # Побудова графіка порівняння
        if len(selected_urls_for_comparison) == len(selected_competitors):
            plot_comparison(df_list, selected_competitors, selected_urls_for_comparison)

        st.write("")
        st.markdown("<div style='background-color: lightgray; height: 2px;'></div>", unsafe_allow_html=True)
        st.write("")

        # Додаємо блок для відображення контенту сторінки
        with st.expander("Click to expand/collapse page content", expanded=False):
            st.subheader("Page Content with Highlighted Keywords")

            # Спочатку вибір конкурента
            competitor_name_content = st.selectbox("Select Competitor", competitors, key="competitor_content_select")

            # Отримуємо дані по ключовим словам для вибраного конкурента
            df_content = get_keyword_data(conn, competitor_name_content)

            # Якщо конкурент вибраний, дозволяємо вибрати сторінку
            if not df_content.empty:
                selected_url_for_content = st.selectbox('Select URL to view content', df_content['url'].unique(), key="url_content_select")

                # Додаємо вибір дати
                selected_date_for_content = st.selectbox(
                    'Select Date to view content',
                    df_content[df_content['url'] == selected_url_for_content]['date_checked'].dt.date.unique(),
                    key="date_select"
                )

                # Фільтруємо контент за датою
                if selected_date_for_content:
                    page_content_data = df_content[(df_content['url'] == selected_url_for_content) &
                                                   (df_content['date_checked'].dt.date == selected_date_for_content)]
                    page_content = page_content_data['content'].values[0]
                    keywords_found = page_content_data['keywords_found'].values[0]

                    # Автоматичне вилучення знайдених ключових слів
                    keywords_dict = extract_keywords(keywords_found)
                    found_keywords = list(keywords_dict.keys())

                    # Виділяємо знайдені ключові слова у тексті
                    highlighted_content = highlight_keywords(page_content, found_keywords)

                    # Відображаємо текст з полями, пробілами та відступами
                    st.markdown(f"<div style='white-space: pre-wrap; padding: 15px;'>{highlighted_content}</div>",
                                unsafe_allow_html=True)

if __name__ == "__main__":
    main()