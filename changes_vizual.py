import streamlit as st
import pandas as pd
from datetime import datetime
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


# Основний блок для рендерингу візуалізації
def render_contribution_chart(change_dates):
    st.markdown(
        """
        <style>
        .contribution-box {
            display: inline-block;
            width: 12px;
            height: 12px;
            margin: 2px;
            background-color: #ebedf0;
            border-radius: 2px;
            position: relative;
        }
        .contribution-level-1 { background-color: #c6e48b; }
        .contribution-level-2 { background-color: #7bc96f; }
        .contribution-level-3 { background-color: #239a3b; }
        .contribution-level-4 { background-color: #196127; }
        .contribution-box:hover .tooltip {
            visibility: visible;
            opacity: 1;
        }
        .tooltip {
            visibility: hidden;
            opacity: 0;
            position: absolute;
            background-color: #333;
            color: #fff;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            white-space: nowrap;
            z-index: 10;
            transition: visibility 0.3s, opacity 0.3s ease;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Підрахунок кількості змін за день
    change_dates['change_date'] = pd.to_datetime(change_dates['change_date']).dt.date
    changes_by_date = change_dates.groupby('change_date').size()

    days_in_year = pd.date_range(start=f'{datetime.now().year}-01-01', end=datetime.now(), freq='D')
    chart = []

    # Місяці для відображення
    months = days_in_year.to_series().dt.strftime('%b').unique()

    # Додавання місяців як підписів
    st.markdown("<div style='display: flex; justify-content: space-between; width: 750px;'>"
                + ''.join([f'<span>{month}</span>' for month in months])
                + "</div>", unsafe_allow_html=True)

    for day in days_in_year:
        count = changes_by_date.get(day.date(), 0)
        if count == 0:
            level = 'contribution-box'
            tooltip = f'{day.strftime("%d %b %Y")}'
        elif count <= 1:
            level = 'contribution-box contribution-level-1'
            tooltip = f'{day.strftime("%d %b %Y")} - {count} change'
        elif count <= 3:
            level = 'contribution-box contribution-level-2'
            tooltip = f'{day.strftime("%d %b %Y")} - {count} changes'
        elif count <= 5:
            level = 'contribution-box contribution-level-3'
            tooltip = f'{day.strftime("%d %b %Y")} - {count} changes'
        else:
            level = 'contribution-box contribution-level-4'
            tooltip = f'{day.strftime("%d %b %Y")} - {count} changes'

        chart.append(f"""
            <div class="{level}">
                <div class='tooltip'>{tooltip}</div>
            </div>
        """)

    # Виведення сітки, схожої на GitHub
    st.markdown(
        '<div style="display: grid; grid-template-columns: repeat(52, 14px); grid-gap: 2px;">'
        + ''.join(chart)
        + '</div>',
        unsafe_allow_html=True
    )


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
            st.write("Немає змін для цього конкуре нта")


if __name__ == "__main__":
    main()