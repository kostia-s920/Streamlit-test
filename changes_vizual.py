import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import psycopg2


# Підключення до бази даних PostgreSQL
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


# Додаємо місяці над сіткою
def render_month_labels():
    # Місяці та кількість тижнів, які вони покривають
    months = {
        'Jan': 4, 'Feb': 4, 'Mar': 5, 'Apr': 4, 'May': 4, 'Jun': 4,
        'Jul': 5, 'Aug': 4, 'Sep': 4, 'Oct': 5, 'Nov': 4, 'Dec': 5
    }

    months_html = '<div style="display: grid; grid-template-columns: repeat(52, 14px); grid-gap: 2px;">'

    # Проходимо по кожному місяцю і додаємо відповідні блоки
    for month, span in months.items():
        # Кожен місяць отримує свій grid column span відповідно до кількості тижнів
        months_html += f'<div style="grid-column: span {span}; text-align: center;">{month}</div>'

    months_html += '</div>'

    return months_html


# Основний блок для рендерингу візуалізації
def render_contribution_chart(change_dates):
    st.markdown(
        "<style>.contribution-box{display: inline-block;width: 12px;height: 12px;margin: 2px;background-color: #ebedf0;}.contribution-level-1{background-color: #c6e48b;}.contribution-level-2{background-color: #7bc96f;}.contribution-level-3{background-color: #239a3b;}.contribution-level-4{background-color: #196127;}</style>",
        unsafe_allow_html=True
    )

    # Підрахунок кількості змін за день
    change_dates['change_date'] = pd.to_datetime(change_dates['change_date']).dt.date
    changes_by_date = change_dates.groupby('change_date').size()

    # Визначаємо початок і кінець року
    start_of_year = pd.to_datetime(f'{datetime.now().year}-01-01').date()
    end_of_year = pd.to_datetime(f'{datetime.now().year}-12-31').date()

    # Створюємо сітку із 52 тижнів та 7 днів на кожен тиждень
    total_days = (end_of_year - start_of_year).days + 1
    days = [start_of_year + timedelta(days=i) for i in range(total_days)]

    # Підписи для осі Y (понеділок, середа, п'ятниця)
    week_days = ['Mon', 'Wed', 'Fri']

    # Генеруємо порожні квадратики зі змінами
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

    # Розбиваємо квадратики на 52 тижні по 7 днів
    grid_html = ''
    for week in range(52):
        week_html = '<div style="display: grid; grid-template-rows: repeat(7, 14px); grid-gap: 2px;">'
        for day_index in range(7):
            index = week * 7 + day_index
            if index < len(chart):
                week_html += chart[index]
        week_html += '</div>'
        grid_html += week_html

    # Додаємо дні тижня зліва від сітки
    week_days_html = '<div style="display: grid; grid-template-rows: repeat(7, 14px); grid-gap: 2px;">'
    for i in range(7):
        if i in [0, 2, 4]:  # Понеділок, середа, п'ятниця
            week_days_html += f'<div>{week_days[[0, 2, 4].index(i)]}</div>'
        else:
            week_days_html += '<div></div>'
    week_days_html += '</div>'

    # Виводимо підписи місяців, дні тижня та основну сітку
    st.markdown(render_month_labels(), unsafe_allow_html=True)
    st.markdown(
        f'<div style="display: flex;">{week_days_html}<div style="display: grid; grid-template-columns: repeat(52, 14px); grid-gap: 2px;">{grid_html}</div></div>',
        unsafe_allow_html=True)


# Основна функція
def main():
    st.title('Візуалізація змін контенту як у GitHub')

    conn = connect_to_db()
    if conn:
        competitor = st.selectbox("Виберіть конкурента", ['docebo_com', 'talentlms_com'])

        # Запит даних змін для конкурента
        query = f"SELECT change_date FROM content_changes_temp WHERE competitor_name = '{competitor}'"
        df = pd.read_sql(query, conn)

        if not df.empty:
            render_contribution_chart(df)
        else:
            st.write("Немає змін для цього конкурента")


if __name__ == "__main__":
    main()