import streamlit as st
import base64
from PIL import Image
import io
import re


def load_template():
    return """
    <!DOCTYPE html>
    <html lang="nl-BE">
    <head>
        <title>{title}</title>
        <meta name="description" content="{meta_description}">
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                margin: 0;
                padding-top: 70px;
                font-family: {font_family};
                background-color: {body_bg_color};
                color: {body_text_color};
            }}

            header {{
                background-color: {header_bg_color};
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px 20px;
                position: fixed;
                width: 100%;
                top: 0;
                left: 0;
                z-index: 1000;
                box-sizing: border-box;
            }}

            .logo img {{
                height: 50px;
            }}

            .hero-banner {{
                width: 100%;
                height: 100vh;
                background-image: url('{hero_bg_image}');
                background-size: cover;
                background-position: center;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            }}

            .hero h1 {{
                color: {hero_title_color};
                font-size: 3em;
                margin: 0.5em 0;
            }}

            .hero h3 {{
                color: {hero_subtitle_color};
                font-size: 1.5em;
                margin: 0.5em 0 1em 0;
            }}

            .cta-button {{
                background: {cta_button_bg};
                color: {cta_button_text_color};
                border: none;
                padding: 15px 30px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 1.2em;
                transition: transform 0.3s;
            }}

            {custom_css}
        </style>
    </head>
    <body>
        <header>
            <div class="logo">
                <a href="#">
                    <img src="{logo_url}" alt="Logo">
                </a>
            </div>
            <nav>
                {navigation_links}
            </nav>
        </header>

        <section class="hero">
            <div class="hero-banner">
                <h1>{hero_title}</h1>
                <h3>{hero_subtitle}</h3>
                <button class="cta-button">{cta_button_text}</button>
            </div>
        </section>

        <main>
            <article>
                {main_content}
            </article>
        </main>

        <footer>
            {footer_content}
        </footer>
    </body>
    </html>
    """


def main():
    st.title("Конструктор веб-сторінки SGCasino")

    # Основні налаштування
    with st.expander("Основні налаштування"):
        title = st.text_input("Заголовок сторінки (title)", "SGCasino - Ervaar het Beste van Live Casino")
        meta_description = st.text_area("Meta Description",
                                        "Ontdek SGCasino, jouw bestemming voor top casinospellen...")
        font_family = st.selectbox(
            "Шрифт",
            ["Arial, sans-serif", "Helvetica, sans-serif", "Times New Roman, serif", "Georgia, serif"]
        )

    # Налаштування кольорів
    with st.expander("Кольорова схема"):
        body_bg_color = st.color_picker("Колір фону сторінки", "#f6fafb")
        body_text_color = st.color_picker("Колір тексту", "#0c0e1f")
        header_bg_color = st.color_picker("Колір фону шапки", "#f3f3f3")
        hero_title_color = st.color_picker("Колір заголовка Hero секції", "#fea488")
        hero_subtitle_color = st.color_picker("Колір підзаголовка Hero секції", "#ffffff")

    # Hero секція
    with st.expander("Hero Секція"):
        hero_title = st.text_input("Заголовок Hero", "SGCasino: Geniet van Uw Welkomstbonus!")
        hero_subtitle = st.text_input("Підзаголовок Hero", "100% tot €500 + 200FS")
        hero_bg_image = st.text_input("URL фонового зображення Hero", "https://example.com/image.jpg")

    # Кнопка CTA
    with st.expander("Налаштування CTA кнопки"):
        cta_button_text = st.text_input("Текст кнопки", "NU LID WORDEN")
        cta_button_bg = st.color_picker("Фон кнопки", "#1be4bf")
        cta_button_text_color = st.color_picker("Колір тексту кнопки", "#ffffff")

    # Логотип
    with st.expander("Логотип"):
        logo_url = st.text_input("URL логотипу", "https://i.imgur.com/GnsXE1q.png")

    # Навігація
    with st.expander("Навігація"):
        nav_links = st.text_area(
            "Посилання навігації (кожне з нової строки у форматі 'текст|url')",
            "Casino|https://sgcasino.be\nLive Casino|https://sgcasino.be\nSport|https://sgcasino.be"
        )

    # Основний контент
    with st.expander("Основний контент"):
        main_content = st.text_area(
            "HTML контент сторінки",
            "<h2>Welkom bij SGCasino</h2><p>Uw beste keuze voor online casino entertainment...</p>"
        )

    # Футер
    with st.expander("Футер"):
        footer_content = st.text_area(
            "HTML контент футера",
            """
            <div class="footer-text">
                <p>2024 © SGCasino.be. Alle rechten voorbehouden.</p>
                <p>Gokken kan verslavend zijn. Speel verantwoord.</p>
            </div>
            """
        )

    # Додаткові CSS стилі
    with st.expander("Додаткові CSS стилі"):
        custom_css = st.text_area(
            "Користувацький CSS",
            """
            .footer-text {
                text-align: center;
                padding: 20px;
            }
            """
        )

    # Формування навігаційних лінків
    navigation_links = ""
    for line in nav_links.split("\n"):
        if "|" in line:
            text, url = line.split("|")
            navigation_links += f'<a href="{url.strip()}">{text.strip()}</a>\n'

    # Генерація HTML
    html_output = load_template().format(
        title=title,
        meta_description=meta_description,
        font_family=font_family,
        body_bg_color=body_bg_color,
        body_text_color=body_text_color,
        header_bg_color=header_bg_color,
        hero_title_color=hero_title_color,
        hero_subtitle_color=hero_subtitle_color,
        hero_title=hero_title,
        hero_subtitle=hero_subtitle,
        hero_bg_image=hero_bg_image,
        cta_button_text=cta_button_text,
        cta_button_bg=cta_button_bg,
        cta_button_text_color=cta_button_text_color,
        logo_url=logo_url,
        navigation_links=navigation_links,
        main_content=main_content,
        footer_content=footer_content,
        custom_css=custom_css
    )

    # Попередній перегляд
    if st.button("Показати попередній перегляд"):
        st.components.v1.html(html_output, height=800, scrolling=True)

    # Збереження HTML
    if st.button("Завантажити HTML"):
        st.download_button(
            label="Зберегти HTML файл",
            data=html_output,
            file_name="sgcasino.html",
            mime="text/html"
        )


if __name__ == "__main__":
    main()