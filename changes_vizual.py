import streamlit as st
import pandas as pd
from datetime import datetime
import psycopg2
from calendar import monthrange


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


# Функція для отримання кількості днів у кожному місяці
def get_month_days():
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    days_in_months = [monthrange(datetime.now().year, i + 1)[1] for i in range(12)]
    return list(zip(months, days_in_months))

# Оновлюємо функцію рендерингу сітки змін
def render_contribution_chart_by_months(change_dates):
    st.markdown(
        """
        <style>
        .contribution-box {
            width: 10px;
            height: 10px;
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
        }
        .month-column {
            display: grid;
            grid-template-rows: repeat(31, 12px); /* Максимум 31 день */
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

    change_dates['change_date'] = pd.to_datetime(change_dates['change_date']).dt.date
    changes_by_date = change_dates.groupby('change_date').size()

    months_data = get_month_days()

    # Початок HTML для візуалізації
    st.markdown('<div class="contribution-box-container">', unsafe_allow_html=True)

    # Генеруємо сітку для кожного місяця
    for month, days in months_data:
        month_html = f'<div class="month-column"><div class="month-title">{month}</div>'

        for day in range(1, days + 1):
            date = datetime(datetime.now().year, months_data.index((month, days)) + 1, day).date()
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

            # Додаємо квадратик для кожного дня
            month_html += f'<div class="{level}" title="{date} - {count} changes"></div>'

        month_html += '</div>'

        # Додаємо сітку для кожного місяця
        st.markdown(month_html, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# Основна функція
def main():
    st.title('Візуалізація змін контенту за місяцями')

    # Підключення до бази даних або використання заглушки
    conn = connect_to_db()
    if conn:
        competitor = st.selectbox("Виберіть конкурента", ['docebo_com', 'ispringsolutions_com', 'talentlms_com', 'paradisosolutions_com'])

        # Перевіряємо, чи обрано всі зміни конкурента
        view_all = st.checkbox("Показати всі зміни конкурента")

        if view_all:
            query = f"SELECT change_date FROM content_changes WHERE competitor_name = '{competitor}'"
            df = pd.read_sql(query, conn)

            if not df.empty:
                st.subheader(f"Загальні зміни для {competitor}")
                render_contribution_chart_by_months(df)
            else:
                st.write("Немає змін для цього конкурента.")
        else:
            # Якщо перегляд змін для окремих сторінок
            page_query = f"SELECT DISTINCT url FROM content_changes WHERE competitor_name = '{competitor}'"
            pages = pd.read_sql(page_query, conn)['url'].tolist()

            if not pages:
                st.write("Немає доступних сторінок для цього конкурента.")
                return

            page = st.selectbox("Виберіть сторінку", pages)

            # Отримання даних змін для вибраної сторінки
            query = f"SELECT change_date FROM content_changes WHERE competitor_name = '{competitor}' AND url = '{page}'"
            df = pd.read_sql(query, conn)

            if not df.empty:
                st.markdown(f"<p style='font-size:12px;color:gray;'>Зміни для сторінки: {page}</p>",
                            unsafe_allow_html=True)
                render_contribution_chart_by_months(df)
            else:
                st.markdown("<p style='font-size:10px;color:gray;'>Немає змін для цієї сторінки.</p>",
                            unsafe_allow_html=True)


if __name__ == "__main__":
    main()