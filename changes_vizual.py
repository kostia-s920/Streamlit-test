import streamlit as st
import pandas as pd
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
            grid-template-columns: repeat(53, 14px); /* 53 тижні */
            grid-template-rows: repeat(7, 14px); /* 7 днів на тиждень */
            grid-gap: 3px;
            justify-content: center;
            align-items: center;
        }
        .contribution-square {
            width: 14px;
            height: 14px;
            background-color: #ebedf0;
            border-radius: 2px;
            position: relative;
        }
        .contribution-square[data-level="1"] { background-color: #c6e48b; }  /* Легкі зміни */
        .contribution-square[data-level="2"] { background-color: #7bc96f; }  /* Середні зміни */
        .contribution-square[data-level="3"] { background-color: #239a3b; }  /* Значні зміни */
        .contribution-square[data-level="4"] { background-color: #196127; }  /* Величезні зміни */
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
        </style>
    """, unsafe_allow_html=True)

# Функція для відображення графіка змін у вигляді GitHub-style contribution graph
def display_github_like_visualization(data):
    create_css_style()  # Виклик функції для додавання CSS стилів

    st.markdown("<div class='contribution-graph'>", unsafe_allow_html=True)
    for entry in data['days']:
        level = entry['level']
        changes = entry['changes']
        date = entry['date']
        if level == 0:
            st.markdown(f"""
                <div class='contribution-square' data-level='{level}'>
                    <span class='tooltip'>{date}</span>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class='contribution-square' data-level='{level}'>
                    <span class='tooltip'>{changes} changes on {date}</span>
                </div>
            """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Функція для перетворення даних у формат для візуалізації
def prepare_data_for_visualization(df):
    days = []
    max_changes = df['changes'].max() if not df.empty else 0
    start_date = pd.to_datetime(f"{pd.Timestamp.today().year}-01-01")
    end_date = pd.to_datetime(f"{pd.Timestamp.today().year}-12-31")

    all_dates = pd.date_range(start=start_date, end=end_date, freq='D')

    for date in all_dates:
        if date in df['change_date'].values:
            row = df[df['change_date'] == date].iloc[0]
            changes = row['changes']
            level = min(4, max(1, int(row['changes'] / max_changes * 4)))  # Рівень змін від 1 до 4
        else:
            changes = 0
            level = 0

        days.append({
            "date": date.strftime('%Y-%m-%d'),
            "changes": changes,
            "level": level
        })

    return {"days": days}

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

        if not df.empty:
            # Підготовка даних для візуалізації
            visualization_data = prepare_data_for_visualization(df)

            # Виводимо графік
            display_github_like_visualization(visualization_data)
        else:
            st.write("Немає змін для обраного конкурента.")
    else:
        st.error("Не вдалося підключитися до бази даних.")

if __name__ == "__main__":
    main()