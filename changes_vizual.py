import streamlit as st
import pandas as pd
import numpy as np
import psycopg2
import matplotlib.pyplot as plt



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

# Отримати дані змін по конкуренту
def get_changes_data(conn, competitor_name):
    query = f"""
        SELECT change_date, COUNT(*) as changes
        FROM content_changes_temp
        WHERE competitor_name = '{competitor_name}'
        GROUP BY change_date
        ORDER BY change_date
    """
    df = pd.read_sql(query, conn)
    df['change_date'] = pd.to_datetime(df['change_date'])
    return df

# Функція для створення CSS стилю
def create_css_style():
    st.markdown("""
        <style>
        .contribution-graph {
            display: grid;
            grid-template-columns: repeat(53, 14px);
            grid-gap: 5px;
            justify-content: center;
            align-items: center;
            position: relative;
        }
        .contribution-square {
            width: 12px;
            height: 12px;
            background-color: #ebedf0;
            border-radius: 2px;
            position: relative;
        }
        .contribution-square[data-level="1"] { background-color: #c6e48b; }
        .contribution-square[data-level="2"] { background-color: #7bc96f; }
        .contribution-square[data-level="3"] { background-color: #239a3b; }
        .contribution-square[data-level="4"] { background-color: #196127; }
        .contribution-square:hover {
            transform: scale(1.2);
            cursor: pointer;
        }
        .total-changes {
            font-size: 1.2em;
            font-weight: bold;
            color: #0b3d13;
            text-align: center;
            margin-top: 10px;
        }
        .month-label {
            text-align: center;
            font-size: 0.8em;
            color: #666;
            margin-bottom: 4px;
        }
        </style>
    """, unsafe_allow_html=True)

# Функція для відображення місяців
def display_month_labels():
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    st.markdown("<div class='contribution-graph'>", unsafe_allow_html=True)
    for month in months:
        st.markdown(f"<div class='month-label'>{month}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Функція для відображення графіка змін у вигляді GitHub-style contribution graph
def display_contribution_graph(df):
    # Групуємо дані за датою і рахуємо кількість змін
    changes_by_day = df.groupby(df['change_date'].dt.date).count()

    # Створюємо матрицю для відображення змін по днях (7 днів на тиждень і 53 тижні на рік)
    changes_matrix = np.zeros((7, 53))

    # Заповнюємо матрицю змінами
    for day, count in changes_by_day.iterrows():
        week = day.isocalendar()[1] - 1  # Отримуємо номер тижня
        weekday = day.weekday()  # Отримуємо день тижня (0 = понеділок, 6 = неділя)
        changes_matrix[weekday, week] = count['changes']  # Кількість змін

    # Створюємо графік
    fig, ax = plt.subplots(figsize=(12, 3))  # Налаштовуємо розмір графіка

    # Відображення матриці змін
    cax = ax.matshow(changes_matrix, cmap='Greens', aspect='auto')

    # Додаємо місяці як мітки по осі X
    ax.set_yticks(range(7))
    ax.set_yticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])

    # Встановлюємо правильні позиції для місяців (53 тижні, приблизно кожні 4.4 тижні = 12 місяців)
    ax.set_xticks([4.5, 8.5, 13.5, 17.5, 22.5, 26.5, 31.5, 35.5, 40.5, 44.5, 49.5])
    ax.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])

    # Прибираємо рамки для кращого вигляду
    ax.spines[:].set_visible(False)

    # Додаємо кольорову шкалу для показу кількості змін
    fig.colorbar(cax)

    # Показ загальної кількості змін
    total_changes = int(changes_by_day['changes'].sum())
    st.subheader(f"Total Changes: {total_changes}")

    st.pyplot(fig)
# Основна функція
def main():
    st.title("Візуалізація змін контенту як у GitHub")

    # Підключаємося до бази даних
    conn = connect_to_db()

    if conn:
        competitors = ['docebo_com', 'ispringsolutions_com', 'talentlms_com', 'paradisosolutions_com']

        # Дозволяємо вибрати конкурента
        competitor_name = st.selectbox("Виберіть конкурента", competitors)

        # Отримуємо дані змін
        df = get_changes_data(conn, competitor_name)

        # Додаємо кастомний CSS стиль
        create_css_style()

        # Виводимо графік
        if not df.empty:
            display_contribution_graph(df)
        else:
            st.write("Немає змін для обраного конкурента.")
    else:
        st.error("Не вдалося підключитися до бази даних.")

if __name__ == "__main__":
    main()