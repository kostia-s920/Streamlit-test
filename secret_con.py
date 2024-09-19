import streamlit as st
import psycopg2
import pandas as pd
import streamlit.components.v1 as components
from difflib import HtmlDiff


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


# Функція для отримання списку конкурентів
def get_competitors(conn):
    query = "SELECT DISTINCT competitor_name FROM content_changes"
    return pd.read_sql(query, conn)['competitor_name'].tolist()


# Функція для отримання списку URL для обраного конкурента
def get_pages_for_competitor(conn, competitor_name):
    query = f"SELECT DISTINCT url FROM content_changes WHERE competitor_name = '{competitor_name}'"
    return pd.read_sql(query, conn)['url'].tolist()


# Функція для отримання дат для обраної сторінки та конкурента
def get_dates_for_page(conn, competitor_name, page_url):
    query = f"""
        SELECT DISTINCT change_date
        FROM content_changes
        WHERE competitor_name = '{competitor_name}' AND url = '{page_url}'
        ORDER BY change_date ASC
    """
    return pd.read_sql(query, conn)['change_date'].tolist()


# Функція для отримання змін для порівняння за обраною сторінкою і датою
def get_changes(conn, competitor_name, page_url, date):
    query = f"""
        SELECT field_changed, old_value, new_value, change_date
        FROM content_changes
        WHERE competitor_name = '{competitor_name}'
        AND url = '{page_url}'
        AND change_date = '{date}'
    """
    return pd.read_sql(query, conn)


# Функція для підсвічування змін у тексті
def highlight_changes(old_value, new_value):
    diff = HtmlDiff()
    html_diff = diff.make_file(old_value.splitlines(), new_value.splitlines(), context=True)
    return html_diff


# Функція для відображення змін у ключових словах
def visualize_keyword_changes(old_keywords, new_keywords):
    old_keyword_dict = parse_keywords(old_keywords)
    new_keyword_dict = parse_keywords(new_keywords)

    st.write("### Зміни в ключових словах")
    changes = []

    # Порівняння ключових слів, що були додані або змінені
    for keyword, count in new_keyword_dict.items():
        if keyword not in old_keyword_dict:
            changes.append({"Ключове слово": keyword, "Зміна": "Додано", "Кількість": f"{count} раз"})
        elif old_keyword_dict[keyword] != count:
            changes.append({"Ключове слово": keyword, "Зміна": "Змінено",
                            "Кількість": f"Було: {old_keyword_dict[keyword]}, Стало: {count}"})

    # Пошук видалених ключових слів
    for keyword, count in old_keyword_dict.items():
        if keyword not in new_keyword_dict:
            changes.append({"Ключове слово": keyword, "Зміна": "Видалено", "Кількість": "-"})

    # Створення таблиці змін
    if changes:
        df_changes = pd.DataFrame(changes)
        st.table(df_changes)
    else:
        st.write("Немає змін у ключових словах.")


# Функція для парсингу ключових слів у форматі 'keyword - count разів'
def parse_keywords(keywords):
    keyword_dict = {}
    if keywords:
        for entry in keywords.split(", "):
            try:
                keyword, count = entry.split(" - ")
                keyword_dict[keyword.strip()] = int(count.split()[0])
            except ValueError:
                continue
    return keyword_dict


# Основна функція для інтерфейсу користувача з візуалізацією змін контенту конкурентів
def main():
    st.title("Візуалізація змін конкурентів")

    conn = connect_to_db()

    if conn:
        # Вибір конкурента
        competitors = get_competitors(conn)
        selected_competitor = st.selectbox('Виберіть конкурента', competitors)

        if selected_competitor:
            # Вибір сторінки для конкурента
            pages = get_pages_for_competitor(conn, selected_competitor)
            selected_page = st.selectbox('Виберіть сторінку', pages)

            if selected_page:
                # Вибір дати для порівняння змін
                dates = get_dates_for_page(conn, selected_competitor, selected_page)
                selected_date = st.selectbox('Виберіть дату для порівняння', dates)

                if selected_date:
                    # Отримання змін для обраної сторінки та дати
                    changes = get_changes(conn, selected_competitor, selected_page, selected_date)

                    if not changes.empty:
                        st.write(f"Зміни для {selected_page} на дату {selected_date}:")

                        # Відображення змін з підсвічуванням
                        for index, row in changes.iterrows():
                            st.subheader(f"Поле змінено: {row['field_changed']}")
                            old_value = row['old_value'] or ''
                            new_value = row['new_value'] or ''

                            if row['field_changed'] == 'keywords_found':
                                # Якщо поле змінилося у `keywords_found`, використовуємо нову логіку
                                visualize_keyword_changes(old_value, new_value)
                            else:
                                html_diff = highlight_changes(old_value, new_value)
                                # Рендеринг HTML-коду за допомогою Streamlit components
                                components.html(html_diff, height=400, scrolling=True)

                    else:
                        st.write("Немає змін для обраної сторінки та дати.")

    conn.close()


if __name__ == "__main__":
    main()