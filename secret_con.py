import base64
import streamlit as st

def test_secrets():
    # Отримання секретів із середовища
    DB_USERNAME = st.secrets["db_username"]
    DB_PASSWORD = st.secrets["db_password"]
    DB_HOST = st.secrets["db_host"]
    DB_NAME = st.secrets["db_name"]
    DB_PORT = st.secrets["db_port"]
    SSL_MODE = st.secrets["ssl_mode"]
    DB_SSL_ROOT_CERT_BASE64 = st.secrets["db_ssl_root_cert"]

    # Виведення значень для тестування
    st.write("DB_USERNAME:", DB_USERNAME)
    st.write("DB_PASSWORD:", DB_PASSWORD)
    st.write("DB_HOST:", DB_HOST)
    st.write("DB_NAME:", DB_NAME)
    st.write("DB_PORT:", DB_PORT)
    st.write("SSL_MODE:", SSL_MODE)

    # Тест декодування сертифікату з Base64
    try:
        ssl_cert_decoded = base64.b64decode(DB_SSL_ROOT_CERT_BASE64)
        st.write("SSL Root Certificate decoded successfully!")
        # Виведемо перші 100 символів сертифікату для підтвердження
        st.write(ssl_cert_decoded[:100])
    except Exception as e:
        st.write("Error decoding SSL Root Certificate:", str(e))

# Запустити функцію тестування
if __name__ == "__main__":
    st.title("Test Streamlit Secrets")
    test_secrets()