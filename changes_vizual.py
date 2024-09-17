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
    months = {
        'Jan': 4, 'Feb': 4, 'Mar': 5, 'Apr': 4, 'May': 4, 'Jun': 4,
        'Jul': 5, 'Aug': 4, 'Sep': 4, 'Oct': 5, 'Nov': 4, 'Dec': 5
    }

    months_html = '<div style="display: grid; grid-template-columns: repeat(52, 10px); grid-gap: 2px;">'

    for month, span in months.items():
        months_html += f'<div style="grid-column: span {span}; text-align: center;">{month}</div>'

    months_html += '</div>'

    return months_html


# Основний блок для рендерингу візуалізації
def render_contribution_chart(change_dates):
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
            overflow-x: auto;
            max-width: 100%;
            white-space: nowrap;
        }
        .contribution-box-container-inner {
            display: grid;
            grid-template-columns: repeat(52, 10px);
            grid-gap: 2px;
        }
        @media (max-width: 600px) {
            .contribution-box {
                width: 8px;
                height: 8px;
            }
            .contribution-box-container-inner {
                grid-template-columns: repeat(52, 8px);
            }
        }
        </style>
        """,
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
        week_html = '<div style="display: grid; grid-template-rows: repeat(7, 10px); grid-gap: 2px;">'
        for day_index in range(7):
            index = week * 7 + day_index
            if index < len(chart):
                week_html += chart[index]
        week_html += '</div>'
        grid_html += week_html

    week_days_html = '<div style="display: grid; grid-template-rows: repeat(7, 10px); grid-gap: 2px;">'
    for i in range(7):
        if i in [0, 2, 4]:
            week_days_html += f'<div>{week_days[[0, 2, 4].index(i)]}</div>'
        else:
            week_days_html += '<div></div>'
    week_days_html += '</div>'

    # Додаємо горизонтальний скрол з підтримкою адаптації для мобільних
    st.markdown('<div class="contribution-box-container">', unsafe_allow_html=True)
    st.markdown(render_month_labels(), unsafe_allow_html=True)
    st.markdown(
        f'<div style="display: flex;">{week_days_html}<div class="contribution-box-container-inner">{grid_html}</div></div>',
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)


# Основна функція
def main():
    st.title('Візуалізація змін контенту')

    conn = connect_to_db()
    if conn:
        # Крок 1: Вибір конкурента
        competitor = st.selectbox("Виберіть конкурента",
                                  ['docebo_com', 'ispringsolutions_com', 'talentlms_com', 'paradisosolutions_com'])

        # Додатковий перемикач для вибору режиму перегляду
        view_all = st.checkbox("Показати всі зміни конкурента")

        if view_all:
            # Якщо обрано перегляд всіх змін, виконуємо запит для всіх змін конкурента
            query = f"SELECT change_date FROM content_changes WHERE competitor_name = '{competitor}'"
            df = pd.read_sql(query, conn)

            if not df.empty:
                st.subheader(f"Загальні зміни для {competitor}")
                render_contribution_chart(df)
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
                # Відображення заголовка сторінки та візуалізація змін
                st.markdown(f"<p style='font-size:12px;color:gray;'>Зміни для сторінки: {page}</p>",
                            unsafe_allow_html=True)
                render_contribution_chart(df)
            else:
                # Повідомлення про відсутність змін
                st.markdown("<p style='font-size:10px;color:gray;'>Немає змін для цієї сторінки.</p>",
                            unsafe_allow_html=True)


if __name__ == "__main__":
    main()