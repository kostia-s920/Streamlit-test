import streamlit as st
import matplotlib.pyplot as plt
import psycopg2
import pandas as pd
import re
import matplotlib.dates as mdates


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
    for keyword in keywords:
        # Виділяємо ключові слова червоним жирним шрифтом
        text = re.sub(f'({keyword})', r'<span style="color:red; font-weight:bold;">\1</span>', text, flags=re.IGNORECASE)
    return text


# Основна функція для відображення даних у Streamlit
def main():
    st.title('Keyword Count and Historical Analysis for Competitors')

    # Підключаємося до бази даних
    conn = connect_to_db()

    if conn:
        competitors = ['docebo_com', 'ispringsolutions_com', 'talentlms_com', 'paradisosolutions_com']

        # Дозволяємо користувачеві вибрати конкурента для аналізу
        competitor_name = st.selectbox("Select Competitor", competitors)

        # Отримуємо дані по ключовим словам для вибраного конкурента
        df = get_keyword_data(conn, competitor_name)

        # Фільтр по URL (дозволяємо вибрати 1-5 URL)
        selected_urls = st.multiselect('Select URLs', df['url'].unique(), max_selections=5)

        # Фільтр по датах
        if not df.empty:
            start_date = pd.to_datetime(st.date_input('Start Date', df['date_checked'].min())).date()
            end_date = pd.to_datetime(st.date_input('End Date', df['date_checked'].max())).date()

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
        selected_url_for_keywords = st.selectbox('Select URL to view found keywords', df['url'].unique())

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
                                                   list(keywords_dict.keys()))

                if selected_keywords:
                    # Додамо вибір типу графіка нижче
                    chart_type = st.selectbox(
                        "Select Chart Type",
                        ['Line Chart', 'Bar Chart', 'Scatter Plot', 'Area Chart', 'Step Chart']
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

        # Додаємо можливість порівняння конкурентів
        st.subheader('Comparison of Keywords Between Competitors')

        # Вибір кількох конкурентів
        selected_competitors = st.multiselect("Select Competitors for Comparison", competitors, default=competitors[:2])

        # Отримуємо дані для кожного конкурента
        df_list = [get_keyword_data(conn, competitor) for competitor in selected_competitors]

        # Вибір URL для кожного конкурента
        selected_urls_for_comparison = []
        for competitor, df in zip(selected_competitors, df_list):
            selected_url = st.selectbox(f'Select URL for {competitor}', df['url'].unique(), key=competitor)
            selected_urls_for_comparison.append(selected_url)

        # Побудова графіка порівняння
        if len(selected_urls_for_comparison) == len(selected_competitors):
            plot_comparison(df_list, selected_competitors, selected_urls_for_comparison)

        # Додаємо блок для відображення контенту сторінки
        with st.expander("Click to expand/collapse page content", expanded=False):
            st.subheader("Page Content with Highlighted Keywords")

            # Вибір URL для відображення контенту
            selected_url_for_content = st.selectbox('Select URL to view content', df['url'].unique())

            # Показуємо контент сторінки з підсвіченими ключовими словами
            if selected_url_for_content:
                # Витягуємо контент для обраного URL
                page_content = df[df['url'] == selected_url_for_content]['content'].values[0]
                keywords_found = df[df['url'] == selected_url_for_content]['keywords_found'].values[0]

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