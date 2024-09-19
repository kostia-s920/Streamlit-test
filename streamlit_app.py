import streamlit as st
import altair as alt
import psycopg2
import pandas as pd
import re
from datetime import datetime

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

# Функція для підсвічування ключових слів в тексті
def highlight_keywords(text, keywords):
    if not text:
        return "No content found."
    for keyword in keywords:
        escaped_keyword = re.escape(keyword)
        text = re.sub(f'({escaped_keyword})', r'<span style="color:red; font-weight:bold;">\1</span>', text, flags=re.IGNORECASE)
    return text

# Функція для побудови графіка ключових слів за допомогою Altair
def plot_keyword_trend(df, competitor_name):
    chart = alt.Chart(df).mark_line().encode(
        x='date_checked:T',
        y='keywords_count:Q',
        color='url:N',
        tooltip=['date_checked:T', 'keywords_count:Q', 'url:N']
    ).properties(
        width=800,
        height=400,
        title=f'Keyword Count Trend for {competitor_name}'
    )
    st.altair_chart(chart)

# Функція для побудови історичного графіка по ключовому слову за допомогою Altair
def plot_keyword_history(df, keyword, selected_url):
    url_data = df[df['url'] == selected_url]
    if url_data.empty:
        st.write(f"No data for URL: {selected_url}")
        return

    url_data['date_checked'] = pd.to_datetime(url_data['date_checked'], errors='coerce')

    keyword_counts = url_data['keywords_found'].apply(lambda row: extract_keywords(row).get(keyword, 0))

    chart = alt.Chart(url_data).mark_line().encode(
        x='date_checked:T',
        y=alt.Y('sum(keywords_found):Q', title='Keyword Occurrences'),
        tooltip=['date_checked:T', 'keywords_found:N']
    ).properties(
        width=800,
        height=400,
        title=f'Historical Trend for Keyword: {keyword}'
    )
    st.altair_chart(chart)

# Функція для графіка порівняння кількох конкурентів за допомогою Altair
def plot_comparison(df_list, competitor_names, selected_urls):
    combined_data = pd.concat(df_list)

    chart = alt.Chart(combined_data).mark_line().encode(
        x='date_checked:T',
        y='keywords_count:Q',
        color='url:N',
        tooltip=['date_checked:T', 'keywords_count:Q', 'url:N']
    ).properties(
        width=800,
        height=400,
        title='Keyword Count Comparison between Competitors'
    )
    st.altair_chart(chart)

# Функція для рендерингу сітки змін за місяцями (додана функція)
def render_contribution_chart_by_months(change_dates, selected_year):
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
    changes_by_date = change_dates.groupby('change_date').size()  # Групуємо зміни за датою

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
                count = changes_by_date.get(date, 0)

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

                month_html += f'<div class="{level}" title="{date} - {count} changes"></div>'

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
        st.title("Аналіз Конкурентів")

        # Візуалізація змін контенту
        with st.expander("Візуалізація змін контенту", expanded=False):
            st.subheader('Візуалізація змін контенту для конкурентів')

            competitor = st.selectbox("Виберіть конкурента",
                                      ['docebo_com', 'ispringsolutions_com', 'talentlms_com', 'paradisosolutions_com',
                                       'academyocean_com'],
                                      key="content_competitor_selectbox")

            # Перевіряємо, чи вибраний чекбокс
            view_all = st.checkbox("Показати всі зміни конкурента", key="content_view_all_checkbox")

            # Якщо вибрано чекбокс, показуємо всі зміни конкурента
            if view_all:
                query = f"SELECT change_date FROM content_changes WHERE competitor_name = '{competitor}'"
                df = pd.read_sql(query, conn)

                if not df.empty:
                    # Додаємо selectbox для вибору року
                    selected_year = st.selectbox("Оберіть рік", [2024, 2025], key="year_selectbox")
                    st.subheader(f"Загальні зміни для {competitor} у {selected_year} році")
                    render_contribution_chart_by_months(df, selected_year)
                else:
                    st.write("Немає змін для цього конкурента.")
            else:
                # Якщо чекбокс не вибраний, показуємо лише список сторінок
                page_query = f"SELECT DISTINCT url FROM content_changes WHERE competitor_name = '{competitor}'"
                pages = pd.read_sql(page_query, conn)['url'].tolist()

                if not pages:
                    st.write("Немає доступних сторінок для цього конкурента.")
                else:
                    page = st.selectbox("Виберіть сторінку", pages, key="content_page_selectbox")

                    query = f"SELECT change_date FROM content_changes WHERE competitor_name = '{competitor}' AND url = '{page}'"
                    df = pd.read_sql(query, conn)

                    if not df.empty:
                        # Додаємо selectbox для вибору року після вибору сторінки
                        selected_year = st.selectbox("Оберіть рік", [2024, 2025], key="year_selectbox")
                        st.markdown(
                            f"<p style='font-size:12px;color:gray;'>Зміни для сторінки: {page} у {selected_year} році</p>",
                            unsafe_allow_html=True)
                        render_contribution_chart_by_months(df, selected_year)
                    else:
                        st.markdown("<p style='font-size:10px;color:gray;'>Немає змін для цієї сторінки.</p>",
                                    unsafe_allow_html=True)

        # Keyword Count and Historical Analysis
        st.subheader('Аналіз Загальної кількості ключових слів конкурента')

        competitors = ['docebo_com', 'ispringsolutions_com', 'talentlms_com', 'paradisosolutions_com',
                       'academyocean_com']
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
                    if selected_page_data['keywords_found'] and isinstance(selected_page_data['keywords_found'], str):
                        keywords_dict = extract_keywords(selected_page_data['keywords_found'])

                        st.write(f"Знайдені ключові слова на {selected_url_for_keywords}:")
                        st.write(keywords_dict)

                        selected_keywords = st.multiselect('Виберіть ключові слова для аналізу історії',
                                                           list(keywords_dict.keys()), key="keyword_select_multiselect")

                        if selected_keywords:
                            for keyword in selected_keywords:
                                st.subheader(f'Історія для ключового слова: {keyword}')
                                keyword_history_df = get_keyword_history(conn, competitor_name, keyword)
                                if not keyword_history_df.empty:
                                    plot_keyword_history(keyword_history_df, keyword, selected_url_for_keywords)
                                else:
                                    st.write(f"Немає даних для ключового слова: {keyword}")

        # Порівняння конкурентів
        with st.expander("Порівняння ключових слів між конкурентами", expanded=False):
            st.subheader('Порівняння ключових слів між конкурентами')
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

        st.markdown("<hr>", unsafe_allow_html=True)

        # Контент сторінки
        with st.expander("Контент сторінки з підсвіченими ключовими словами", expanded=False):
            st.subheader('Контент сторінки з підсвіченими ключовими словами')
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


if __name__ == "__main__":
    main()