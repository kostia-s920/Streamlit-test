import streamlit as st
import base64

# Отримуємо секрети з streamlit secrets
DB_USERNAME = st.secrets["DB_USERNAME"]
DB_PASSWORD = st.secrets["DB_PASSWORD"]
DB_HOST = st.secrets["DB_HOST"]
DB_PORT = st.secrets["DB_PORT"]
DB_NAME = st.secrets["DB_NAME"]
SSL_MODE = st.secrets["SSL_MODE"]
DB_SSL_ROOT_CERT = st.secrets["DB_SSL_ROOT_CERT"]

# Декодуємо SSL сертифікат
ssl_cert_decoded = base64.b64decode(DB_SSL_ROOT_CERT)

# Виведення значень для тестування
def test_secrets():
    st.write("DB_USERNAME:", DB_USERNAME)
    st.write("DB_PASSWORD:", DB_PASSWORD)
    st.write("DB_HOST:", DB_HOST)
    st.write("DB_NAME:", DB_NAME)
    st.write("DB_PORT:", DB_PORT)
    st.write("SSL_MODE:", SSL_MODE)

    # Тест декодування сертифікату з Base64
    try:
        ssl_cert_decoded = base64.b64decode(DB_SSL_ROOT_CERT)
        st.write("SSL Root Certificate decoded successfully!")
        # Виведемо перші 100 символів сертифікату для підтвердження
        st.write(ssl_cert_decoded[:100])
    except Exception as e:
        st.write("Error decoding SSL Root Certificate:", str(e))

# Запустити функцію тестування
if __name__ == "__main__":
    st.title("Test Streamlit Secrets")
    test_secrets()