import re
import streamlit as st
import matplotlib.pyplot as plt
import psycopg2
import pandas as pd


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


# Функція для отримання історичних даних по ключовому слову
def get_keyword_history(conn, competitor_name, keyword):
    query = f"""
        SELECT url, date_checked, keywords_found
        FROM {competitor_name}_temp 
        WHERE keywords_found ILIKE %s
        ORDER BY date_checked ASC
    """
    df = pd.read_sql(query, conn, params=[f'%{keyword}%'])
    return df


# Функція для отримання кількості повторень ключового слова (ігноруючи частину в дужках)
def extract_keyword_count(keyword, text):
    try:
        # Використовуємо регулярний вираз для пошуку ключового слова без "(Content: X)"
        pattern = re.compile(rf"{keyword} - (\d+) разів")
        match = pattern.search(text)
        if match:
            return int(match.group(1))
        else:
            return 0
    except Exception as e:
        print(f"Error extracting keyword count: {e}")
        return 0


# Функція для побудови графіка
def plot_keyword_history(df, keyword):
    plt.figure(figsize=(10, 6))

    for url in df['url'].unique():
        url_data = df[df['url'] == url]
        occurrences = [extract_keyword_count(keyword, row) for row in url_data['keywords_found']]

        plt.plot(url_data['date_checked'], occurrences, label=url)

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

        # Вибираємо ключове слово для аналізу його змін у часі
        selected_keyword = st.text_input('Enter keyword to analyze', 'lms system')

        if selected_keyword:
            keyword_history_df = get_keyword_history(conn, competitor_name, selected_keyword)
            if not keyword_history_df.empty:
                plot_keyword_history(keyword_history_df, selected_keyword)
            else:
                st.write(f"No historical data found for keyword: {selected_keyword}")

if __name__ == "__main__":
    main()