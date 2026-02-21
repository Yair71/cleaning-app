import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# Настройки для мобилок: свернутое меню, иконка
st.set_page_config(page_title="Cleaning OS", page_icon="✨", layout="centered", initial_sidebar_state="collapsed")

DB_FILE = "cleaning_db.xlsx"

# Загрузка базы данных
def load_data():
    if not os.path.exists(DB_FILE):
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

# --- БОКОВОЕ МЕНЮ (Мобильная навигация) ---
st.sidebar.title("Меню управления")
page = st.sidebar.radio("Навигация:", [
    "💸 Касса (Ввод данных)", 
    "📊 Аналитика бизнеса", 
    "🧮 Калькулятор цен",
    "📋 База заказов"
])

# ================= СТРАНИЦА 1: КАССА =================
if page == "💸 Касса (Ввод данных)":
    st.title("💸 Касса")
    
    # Главный переключатель
    action = st.radio("Что делаем?", ["✅ Закрыть заказ (Доход)", "🛒 Записать расход"], horizontal=True)
    
    if action == "✅ Закрыть заказ (Доход)":
        with st.container(border=True):
            st.subheader("1. Детали объекта")
            job_date = st.date_input("Дата заказа", datetime.today())
            job_property = st.selectbox("Тип объекта", ["Квартира (Apartment)", "Вилла (Villa)", "Только Handyman"])
            job_sqm = st.number_input("Площадь (м²)", min_value=0, step=10, value=100)
            
            st.markdown("Уровень сложности:")
            job_type = st.radio("Уровень сложности", ["Light", "Deep", "Post-Reno"], horizontal=True, label_visibility="collapsed")
            
        with st.container(border=True):
            st.subheader("2. Финансы и Клиент")
            job_revenue = st.number_input("Итоговый чек (₪)", min_value=0.0, step=50.0, value=1000.0)
            job_handyman = st.toggle("🔧 Был апсейл Handyman?") # Удобный тумблер
            job_rating = st.slider("Оценка клиента", 1, 5, 5)
            job_note = st.text_input("Имя клиента / Адрес (необязательно)")

        if st.button("🚀 Сохранить заказ", type="primary", use_container_width=True):
            new_job = pd.DataFrame([{"Date": job_date, "Property": job_property, "SqMeters": job_sqm, "CleanType": job_type, "HandymanUpsell": job_handyman, "Revenue": job_revenue, "Rating": job_rating}])
            df_jobs = pd.concat([df_jobs, new_job], ignore_index=True)
            
            new_income = pd.DataFrame([{"Date": job_date, "Type": "Income", "Category": f"Revenue - {job_property}", "Amount": job_revenue, "Note": job_note}])
            df_cash = pd.concat([df_cash, new_income], ignore_index=True)
            
            save_data(df_cash, df_jobs)
            st.toast("✅ Заказ закрыт, деньги в кассе!") # Всплывашка снизу
            
    elif action == "🛒 Записать расход":
        with st.container(border=True):
            st.subheader("Новая покупка")
            exp_date = st.date_input("Дата", datetime.today())
            exp_amount = st.number_input("Сумма покупки (₪)", min_value=0.0, step=50.0)
            exp_category = st.selectbox("Категория расходов", [
                "Химия и расходники", "Бензин / Парковка", "Оборудование", 
                "Ремонт авто/техники", "Реклама", "Зарплата", "Прочее"
            ])
            exp_note = st.text_input("Что именно купили? (Например: 5л доместоса)")
            
            if st.button("💾 Записать расход", type="primary", use_container_width=True):
                new_expense = pd.DataFrame([{"Date": exp_date, "Type": "Expense", "Category": exp_category, "Amount": exp_amount, "Note": exp_note}])
                df_cash = pd.concat([df_cash, new_expense], ignore_index=True)
                save_data(df_cash, df_jobs)
                st.toast("✅ Расход успешно добавлен!") # Всплывашка снизу

# ================= СТРАНИЦА 2: АНАЛИТИКА =================
elif page == "📊 Аналитика бизнеса":
    st.title("📊 P&L Отчет")
    
    if df_cash.empty:
        st.info("Пока нет данных. Внесите заказы или расходы в Кассе.")
    else:
        df_cash['Date'] = pd.to_datetime(df_cash['Date'])
        df_cash['Month'] = df_cash['Date'].dt.to_period('M').astype(str)
        
        selected_month = st.selectbox("Выбрать месяц", df_cash['Month'].unique()[::-1])
        month_data = df_cash[df_cash['Month'] == selected_month]
        
        income = month_data[month_data['Type'] == 'Income']['Amount'].sum()
        expense = month_data[month_data['Type'] == 'Expense']['Amount'].sum()
        profit = income - expense
        
        # Крупные цифры для мобилки
        with st.container(border=True):
            st.metric("💵 Выручка", f"{income:,.0f} ₪")
            st.metric("🔥 Расходы", f"{expense:,.0f} ₪")
            st.metric("💎 Чистая прибыль", f"{profit:,.0f} ₪", delta=f"{(profit/income*100):.1f}% маржа" if income>0 else "0")
        
        st.subheader("Куда ушли деньги?")
        exp_data = month_data[month_data['Type'] == 'Expense']
        if not exp_data.empty:
            fig_exp = px.pie(exp_data, values='Amount', names='Category', hole=0.5)
            fig_exp.update_layout(margin=dict(t=0, b=0, l=0, r=0)) # Убираем лишние отступы для телефона
            st.plotly_chart(fig_exp, use_container_width=True)

# ================= СТРАНИЦА 3: КАЛЬКУЛЯТОР =================
elif page == "🧮 Калькулятор цен":
    st.title("🧮 Калькулятор")
    
    with st.container(border=True):
        st.subheader("Оценка стоимости")
        calc_sqm = st.number_input("Площадь (м²)", 0, 500, 100)
        calc_type = st.radio("Тип уборки", ["Light (17 ₪/м²)", "Deep (24 ₪/м²)", "Post-Reno (30 ₪/м²)"])
        
        rate = 17 if "Light" in calc_type else 24 if "Deep" in calc_type else 30
        base_price = calc_sqm * rate
        
        big_fee = 200 if calc_sqm >= 140 else 0
        if big_fee > 0:
            st.warning(f"Надбавка за большую площадь: +{big_fee}₪")
            
        total_quote = base_price + big_fee
        
        st.success(f"💰 Итоговая цена: {total_quote} ₪")

# ================= СТРАНИЦА 4: БАЗА =================
elif page == "📋 База заказов":
    st.title("📋 История заказов")
    if df_jobs.empty:
        st.info("Заказов пока нет.")
    else:
        # Показываем только важные колонки на узком экране
        st.dataframe(df_jobs[['Date', 'Property', 'Revenue', 'Rating']].sort_values(by="Date", ascending=False), use_container_width=True)
