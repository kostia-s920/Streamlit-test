import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Заголовок сторінки
st.title("Аналіз ключових слів за конкурентами")

# Створюємо простий фільтр
competitor = st.selectbox('Оберіть конкурента:', ['Competitor 1', 'Competitor 2'])

# Підвантажуємо дані (тут можна підключити вашу базу даних)
data = {
    'Дата': ['2024-08-01', '2024-09-01'],
    'Кількість ключових слів': [120, 150]
}
df = pd.DataFrame(data)

# Фільтруємо дані за обраним конкурентом
filtered_data = df  # Тут можна реалізувати фільтрацію

# Побудова графіка
fig, ax = plt.subplots()
ax.plot(filtered_data['Дата'], filtered_data['Кількість ключових слів'], marker='o')
ax.set_title(f'Ключові слова для {competitor}')
ax.set_xlabel('Дата')
ax.set_ylabel('Кількість ключових слів')

# Виводимо графік у Streamlit
st.pyplot(fig)