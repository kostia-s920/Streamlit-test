import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

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


# Функція для рендерингу сітки змін за місяцями
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
                                      ['docebo_com', 'ispringsolutions_com', 'talentlms_com', 'paradisosolutions_com'],
                                      key="content_competitor_selectbox")

            view_all = st.checkbox("Показати всі зміни конкурента", key="content_view_all_checkbox")

            if view_all:
                query = f"SELECT change_date FROM content_changes_temp WHERE competitor_name = '{competitor}'"
                df = pd.read_sql(query, conn)

                if not df.empty:
                    # Додаємо selectbox для вибору року після вибору сторінки
                    selected_year = st.selectbox("Оберіть рік", [2024, 2025], key="year_selectbox")

                    st.subheader(f"Загальні зміни для {competitor} у {selected_year} році")
                    render_contribution_chart_by_months(df, selected_year)
                else:
                    st.write("Немає змін для цього конкурента.")
            else:
                page_query = f"SELECT DISTINCT url FROM content_changes_temp WHERE competitor_name = '{competitor}'"
                pages = pd.read_sql(page_query, conn)['url'].tolist()

                if not pages:
                    st.write("Немає доступних сторінок для цього конкурента.")
                    return

                page = st.selectbox("Виберіть сторінку", pages, key="content_page_selectbox")

                query = f"SELECT change_date FROM content_changes_temp WHERE competitor_name = '{competitor}' AND url = '{page}'"
                df = pd.read_sql(query, conn)

                if not df.empty:
                    # Додаємо selectbox для вибору року після вибору сторінки
                    selected_year = st.selectbox("Оберіть рік", [2024, 2025], key="year_selectbox")

                    st.markdown(f"<p style='font-size:12px;color:gray;'>Зміни для сторінки: {page} у {selected_year} році</p>",
                                unsafe_allow_html=True)
                    render_contribution_chart_by_months(df, selected_year)
                else:
                    st.markdown("<p style='font-size:10px;color:gray;'>Немає змін для цієї сторінки.</p>",
                                unsafe_allow_html=True)


if __name__ == "__main__":
    main()