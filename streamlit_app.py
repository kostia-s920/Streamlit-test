import streamlit as st
import matplotlib.pyplot as plt
import psycopg2
import pandas as pd


# Інші імпорти, як у вашому коді...

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
        print(f"Error connecting to database: {e}")
        return None


# Функція для отримання даних по ключовим словам із бази даних
def get_keyword_data(conn, competitor_name):
    query = f"""
        SELECT url, keywords_count, keywords_found, date_checked 
        FROM {competitor_name}_temp 
        ORDER BY date_checked ASC
    """
    df = pd.read_sql(query, conn)
    return df


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

    # Показуємо графік у Streamlit
    st.pyplot(plt)


# Функція для побудови історичного графіка по ключовому слову
def plot_keyword_history(df, keyword):
    plt.figure(figsize=(10, 6))
    for url in df['url'].unique():
        url_data = df[df['url'] == url]
        plt.plot(url_data['date_checked'], url_data['keywords_found'].str.count(keyword), label=url)

    plt.title(f'Historical Trend for Keyword: {keyword}')
    plt.xlabel('Date')
    plt.ylabel('Keyword Occurrences')
    plt.legend(loc='best', bbox_to_anchor=(1, 1))
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Показуємо графік у Streamlit
    st.pyplot(plt)


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
            start_date = st.date_input('Start Date', df['date_checked'].min())
            end_date = st.date_input('End Date', df['date_checked'].max())

            df = df[
                (df['date_checked'] >= pd.to_datetime(start_date)) & (df['date_checked'] <= pd.to_datetime(end_date))]

        # Фільтруємо дані по вибраним URL
        if selected_urls:
            df = df[df['url'].isin(selected_urls)]

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
                found_keywords = selected_page_data['keywords_found'].split(', ')
                st.write(f"Found keywords on {selected_url_for_keywords}:")
                st.write(found_keywords)

                # Вибираємо ключові слова для аналізу їх змін у часі
                selected_keywords = st.multiselect('Select keywords to analyze historical occurrences', found_keywords)

                if selected_keywords:
                    for keyword in selected_keywords:
                        st.subheader(f'Historical Trend for Keyword: {keyword}')
                        keyword_history_df = get_keyword_history(conn, competitor_name, keyword)
                        if not keyword_history_df.empty:
                            plot_keyword_history(keyword_history_df, keyword)
                        else:
                            st.write(f"No historical data found for keyword: {keyword}")
            else:
                st.write(f"No keywords found for URL: {selected_url_for_keywords}")

if __name__ == "__main__":
    main()