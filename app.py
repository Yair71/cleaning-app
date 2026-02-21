import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# Настройки страницы
st.set_page_config(page_title="Cleaning Business Manager", layout="wide")

DB_FILE = "cleaning_db.xlsx"

# Функция для инициализации или загрузки базы данных
def load_data():
    if not os.path.exists(DB_FILE):
        # Если файла нет, создаем с правильной структурой
        df_cash = pd.DataFrame(columns=["Date", "Type", "Category", "Amount", "Note"])
        df_jobs = pd.DataFrame(columns=["Date", "Property", "SqMeters", "CleanType", "HandymanUpsell", "Revenue", "Rating"])
        with pd.ExcelWriter(DB_FILE) as writer:
            df_cash.to_excel(writer, sheet_name="Cashflow", index=False)
            df_jobs.to_excel(writer, sheet_name="Jobs", index=False)
    
    cashflow = pd.read_excel(DB_FILE, sheet_name="Cashflow")
    jobs = pd.read_excel(DB_FILE, sheet_name="Jobs")
    return cashflow, jobs

def save_data(cashflow, jobs):
    with pd.ExcelWriter(DB_FILE) as writer:
        cashflow.to_excel(writer, sheet_name="Cashflow", index=False)
        jobs.to_excel(writer, sheet_name="Jobs", index=False)

df_cash, df_jobs = load_data()

st.title("✨ Cleaning Business OS (Caesarea)")
st.markdown("---")

# Создаем вкладки для удобства (Уровень 10/10)
tab1, tab2, tab3, tab4 = st.tabs(["💰 Добавить Расход", "✅ Новый Заказ", "📊 Аналитика (P&L)", "🧮 Калькулятор Цен"])

# ================= TAB 1: РАСХОДЫ =================
with tab1:
    st.header("Записать расход")
    col1, col2 = st.columns(2)
    with col1:
        exp_date = st.date_input("Дата расхода", datetime.today())
        exp_category = st.selectbox("Категория", [
            "Химия и расходники", "Топливо / Парковка", "Оборудование (покупка/аренда)", 
            "Ремонт авто/инструмента", "Маркетинг / Реклама", "Зарплата клинерам", 
            "Зарплата Handyman", "Налоги/Бухгалтерия", "Прочее"
        ])
    with col2:
        exp_amount = st.number_input("Сумма (₪)", min_value=0.0, step=50.0)
        exp_note = st.text_input("Комментарий (что именно купили?)")
        
    if st.button("💾 Сохранить расход", use_container_width=True):
        new_expense = pd.DataFrame([{
            "Date": exp_date, "Type": "Expense", "Category": exp_category, 
            "Amount": exp_amount, "Note": exp_note
        }])
        df_cash = pd.concat([df_cash, new_expense], ignore_index=True)
        save_data(df_cash, df_jobs)
        st.success("Расход успешно добавлен!")
        st.rerun()

# ================= TAB 2: ЗАКАЗЫ (ДОХОД) =================
with tab2:
    st.header("Закрыть заказ (Добавить доход)")
    col1, col2, col3 = st.columns(3)
    with col1:
        job_date = st.date_input("Дата заказа", datetime.today())
        job_property = st.selectbox("Тип объекта", ["Apartment", "Villa", "Handyman Only"])
        job_sqm = st.number_input("Площадь (м²)", min_value=0, step=10, value=100)
    with col2:
        job_type = st.selectbox("Уровень сложности", ["1 - Light", "2 - Deep", "3 - Post-Reno"])
        job_handyman = st.checkbox("Был апсейл Handyman?")
        job_rating = st.slider("Оценка клиента (1-5)", 1, 5, 5)
    with col3:
        job_revenue = st.number_input("Итоговая сумма чека (₪)", min_value=0.0, step=100.0)
        job_note = st.text_input("Имя клиента / Адрес")

    if st.button("🚀 Сохранить заказ", type="primary", use_container_width=True):
        # Пишем в Jobs
        new_job = pd.DataFrame([{
            "Date": job_date, "Property": job_property, "SqMeters": job_sqm, 
            "CleanType": job_type, "HandymanUpsell": job_handyman, "Revenue": job_revenue, "Rating": job_rating
        }])
        df_jobs = pd.concat([df_jobs, new_job], ignore_index=True)
        
        # Пишем в Cashflow как Доход
        rev_category = f"Revenue - {job_property}"
        new_income = pd.DataFrame([{
            "Date": job_date, "Type": "Income", "Category": rev_category, 
            "Amount": job_revenue, "Note": job_note
        }])
        df_cash = pd.concat([df_cash, new_income], ignore_index=True)
        
        save_data(df_cash, df_jobs)
        st.success("Заказ закрыт, деньги в кассе!")
        st.rerun()

# ================= TAB 3: АНАЛИТИКА =================
with tab3:
    st.header("Бизнес Аналитика (Авто-счет)")
    
    if df_cash.empty:
        st.info("Пока нет данных для аналитики. Добавьте расходы или доходы.")
    else:
        df_cash['Date'] = pd.to_datetime(df_cash['Date'])
        
        # Фильтр по месяцам
        df_cash['Month'] = df_cash['Date'].dt.to_period('M').astype(str)
        selected_month = st.selectbox("Выберите месяц", df_cash['Month'].unique()[::-1])
        month_data = df_cash[df_cash['Month'] == selected_month]
        
        # Считаем P&L
        income = month_data[month_data['Type'] == 'Income']['Amount'].sum()
        expense = month_data[month_data['Type'] == 'Expense']['Amount'].sum()
        profit = income - expense
        
        # Красивые метрики сверху
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Выручка (₪)", f"{income:,.0f}")
        m2.metric("Расходы (₪)", f"{expense:,.0f}")
        m3.metric("Чистая прибыль (₪)", f"{profit:,.0f}", delta=f"{(profit/income*100):.1f}% маржа" if income>0 else "0")
        
        # KPI Заказов
        if not df_jobs.empty:
            df_jobs['Date'] = pd.to_datetime(df_jobs['Date'])
            jobs_month = df_jobs[df_jobs['Date'].dt.to_period('M').astype(str) == selected_month]
            avg_rating = jobs_month['Rating'].mean()
            m4.metric("Средняя оценка", f"⭐ {avg_rating:.1f}" if pd.notnull(avg_rating) else "Нет оценок")
        
        st.markdown("---")
        
        # Графики
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Структура расходов")
            exp_data = month_data[month_data['Type'] == 'Expense']
            if not exp_data.empty:
                fig_exp = px.pie(exp_data, values='Amount', names='Category', hole=0.4)
                st.plotly_chart(fig_exp, use_container_width=True)
            else:
                st.write("Нет расходов в этом месяце")
                
        with c2:
            st.subheader("Динамика (Доходы vs Расходы)")
            grouped = month_data.groupby(['Date', 'Type'])['Amount'].sum().reset_index()
            fig_bar = px.bar(grouped, x='Date', y='Amount', color='Type', barmode='group',
                             color_discrete_map={"Income": "green", "Expense": "red"})
            st.plotly_chart(fig_bar, use_container_width=True)

# ================= TAB 4: КАЛЬКУЛЯТОР =================
with tab4:
    st.header("Быстрый калькулятор цен (для клиента по телефону)")
    st.info("Формулы настроены согласно твоей таблице Pricing.csv")
    
    calc_sqm = st.number_input("Площадь квартиры (м²)", 0, 500, 100, key="calc_sqm")
    calc_type = st.radio("Тип уборки", ["Light (11 ₪/м²)", "Deep (16 ₪/м²)", "Post-Reno (20 ₪/м²)"])
    
    rate = 11 if "Light" in calc_type else 16 if "Deep" in calc_type else 20
    base_price = calc_sqm * rate
    
    # Доплата за большую квартиру
    big_fee = 150 if calc_sqm >= 130 else 0
    if big_fee > 0:
        st.warning(f"Применена надбавка за большую площадь (>=130м²): +{big_fee}₪")
        
    total_quote = base_price + big_fee
    
    st.metric(label="Итоговая цена для клиента", value=f"{total_quote} ₪")
