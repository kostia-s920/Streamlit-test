import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import psycopg2

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

# Функція для отримання даних зі змін
def get_data_from_db(conn):
    query = """
    SELECT competitor_name, url, field_changed, old_value, new_value, change_date, old_keywords_count, new_keywords_count
    FROM content_changes_temp
    """
    df = pd.read_sql(query, conn)
    df['change_date'] = pd.to_datetime(df['change_date']).dt.normalize()  # Округлюємо час до початку дня
    return df

# Запуск Streamlit додатку
def main():
    st.title('Візуалізація змін конкурентів')

    # Підключаємося до бази даних
    conn = connect_to_db()
    if conn:
        df = get_data_from_db(conn)

        # Фільтр за конкурентом та сторінкою
        competitor = st.selectbox("Виберіть конкурента", df['competitor_name'].unique())
        filtered_df = df[df['competitor_name'] == competitor]

        url = st.selectbox("Виберіть сторінку", filtered_df['url'].unique())
        filtered_df = filtered_df[filtered_df['url'] == url]

        # Групування змін за датами для побудови графіка
        changes_by_date = filtered_df.groupby('change_date').size()

        # Створення матриці для теплової карти
        dates_range = pd.date_range(start=changes_by_date.index.min(), end=changes_by_date.index.max())
        changes_matrix = pd.DataFrame(index=dates_range, data=np.zeros(len(dates_range)), columns=['changes'])
        changes_matrix.loc[changes_by_date.index, 'changes'] = changes_by_date.values

        # Візуалізація теплової карти з градацією кольорів
        plt.figure(figsize=(10, 2))
        sns.heatmap(changes_matrix.T, cmap='Greens', cbar=False, linewidths=.5, annot=True, fmt='.0f')
        plt.title(f'Частота змін для {url}')
        plt.yticks([])

        # Відображення графіка в Streamlit
        st.pyplot(plt)

        # Виведення детальної інформації по кожній зміні
        st.subheader("Деталі змін")
        selected_date = st.selectbox("Оберіть дату", filtered_df['change_date'].unique())
        detailed_changes = filtered_df[filtered_df['change_date'] == selected_date]

        for i, row in detailed_changes.iterrows():
            st.write(f"Поле: {row['field_changed']}")
            st.write(f"Стара версія: {row['old_value']}")
            st.write(f"Нова версія: {row['new_value']}")
            if pd.notna(row['old_keywords_count']) and pd.notna(row['new_keywords_count']):
                st.write(f"Кількість ключових слів: {row['old_keywords_count']} -> {row['new_keywords_count']}")
            st.write("---")

        # Закриття з'єднання з базою даних
        conn.close()
    else:
        st.error("Не вдалося підключитися до бази даних.")

if __name__ == "__main__":
    main()