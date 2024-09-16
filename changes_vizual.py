import streamlit as st
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
        .contribution-square[data-level="5"] { background-color: #0b3d13; }
        .contribution-square:hover {
            transform: scale(1.2);
            cursor: pointer;
        }
        .tooltip {
            position: absolute;
            background-color: #333;
            color: #fff;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            white-space: nowrap;
            visibility: hidden;
            z-index: 10;
            transition: visibility 0.3s, opacity 0.3s ease;
            opacity: 0;
        }
        .contribution-square:hover .tooltip {
            visibility: visible;
            opacity: 1;
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


# Функція для візуалізації змін у вигляді графіка як на GitHub
def display_contribution_graph(df):
    weeks = 53  # 52 тижні + поточний
    days = 7

    # Підрахунок кількості змін для кожного дня
    changes_by_day = df.groupby(df['change_date'].dt.date).sum()

    # Визначаємо рівень зміни для кожної дати
    max_changes = changes_by_day['changes'].max()
    changes_by_day['level'] = (changes_by_day['changes'] / max_changes * 5).apply(np.ceil).astype(int)

    # Показуємо загальну кількість змін
    total_changes = changes_by_day['changes'].sum()
    st.markdown(f"<div class='total-changes'>Total Changes: {total_changes}</div>", unsafe_allow_html=True)

    # Візуалізуємо місяці
    display_month_labels()

    # Візуалізуємо у вигляді "contribution graph"
    st.markdown("<div class='contribution-graph'>", unsafe_allow_html=True)

    for week in range(weeks):
        for day in range(days):
            date = changes_by_day.index[week * 7 + day] if (week * 7 + day) < len(changes_by_day) else None
            level = changes_by_day.loc[date]['level'] if date in changes_by_day.index else 0
            if date:
                st.markdown(f"""
                    <div class='contribution-square' data-level='{level}'>
                        <span class='tooltip'>{changes_by_day.loc[date]['changes']} changes on {date}</span>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("<div class='contribution-square'></div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


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
        display_contribution_graph(df)


if __name__ == "__main__":
    main()