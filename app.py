import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import traceback

# --- НАСТРОЙКИ UI ---
st.set_page_config(page_title="Cleaning OS Premium", page_icon="💎", layout="centered", initial_sidebar_state="collapsed")

# --- ПОДКЛЮЧЕНИЕ ---
def get_gsheet():
    try:
        creds_dict = json.loads(st.secrets["google_json"])
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(st.secrets["spreadsheet"]["id"])
        return sheet
    except Exception as e:
        st.error("❌ Ошибка при подключении к Google:")
        st.code(traceback.format_exc())
        return None

# --- ЗАГРУЗКА ДАННЫХ ---
def load_data():
    sh = get_gsheet()
    if sh:
        try:
            cash_ws = sh.worksheet("Cashflow")
            jobs_ws = sh.worksheet("Jobs")
            
            df_cash = pd.DataFrame(cash_ws.get_all_records())
            df_jobs = pd.DataFrame(jobs_ws.get_all_records())
            
            return df_cash, df_jobs, cash_ws, jobs_ws
        except Exception as e:
            st.error("❌ Ошибка при чтении листов. Проверь, что в Google Таблице есть листы 'Cashflow' и 'Jobs'.")
            st.code(traceback.format_exc())
    return pd.DataFrame(), pd.DataFrame(), None, None

df_cash, df_jobs, cash_ws, jobs_ws = load_data()

# --- БОКОВОЕ МЕНЮ ---
st.sidebar.title("Cleaning OS 💎")
page = st.sidebar.radio("Навигация:", [
    "💸 Касса (Операции)", 
    "📈 Dashboard (P&L и KPI)", 
    "🧮 Smart Калькулятор",
    "📋 База заказов"
])

# ================= СТРАНИЦА 1: КАССА =================
if page == "💸 Касса (Операции)":
    st.title("💸 Касса")
    
    action = st.radio("Тип операции:", ["✅ Закрыть заказ (Доход)", "🛒 Записать расход"], horizontal=True)
    
    if action == "✅ Закрыть заказ (Доход)":
        if jobs_ws is None:
            st.warning("Нет связи с таблицей")
        else:
            with st.container(border=True):
                st.subheader("1. Детали объекта")
                job_date = st.date_input("Дата заказа", datetime.today())
                job_property = st.selectbox("Категория (Line of Business)", ["Apartments", "Villas", "Handyman / Construction"])
                job_sqm = st.number_input("Площадь (м²)", min_value=0, step=10, value=100)
                job_type = st.radio("Пакет (Сложность)", ["Light (Basic)", "Deep", "Post-Reno / Move-In"], horizontal=True)
                
            with st.container(border=True):
                st.subheader("2. Финансы и KPI")
                job_revenue = st.number_input("Итоговая выручка (₪)", min_value=0.0, step=50.0, value=1000.0)
                job_handyman = st.toggle("🔧 Был ли апсейл Handyman (доп. услуги)?")
                job_rating = st.slider("Оценка клиента (для KPI)", 1, 5, 5)
                job_note = st.text_input("Клиент / Комментарий")

            if st.button("🚀 Сохранить заказ в Облако", type="primary", use_container_width=True):
                jobs_ws.append_row([
                    job_date.strftime("%Y-%m-%d"), job_property, job_sqm, 
                    job_type, job_handyman, job_revenue, job_rating
                ])
                cash_ws.append_row([
                    job_date.strftime("%Y-%m-%d"), "Income", f"{job_property} revenue", 
                    job_revenue, job_note
                ])
                st.toast("✅ Заказ проведен! Данные в Google Sheets.")
                st.rerun()
            
    elif action == "🛒 Записать расход":
        if cash_ws is None:
            st.warning("Нет связи с таблицей")
        else:
            with st.container(border=True):
                st.subheader("Новый расход")
                exp_date = st.date_input("Дата", datetime.today())
                exp_amount = st.number_input("Сумма (₪)", min_value=0.0, step=50.0)
                
                # Полный список расходов из бизнес-модели
                exp_category = st.selectbox("Статья расходов", [
                    "Cleaning chemicals & consumables", 
                    "Travel / fuel / parking", 
                    "Equipment & tools (buy/rent)", 
                    "Repairs & maintenance", 
                    "Marketing / ads", 
                    "Insurance", 
                    "Accountant / bookkeeping", 
                    "Phones / software", 
                    "Payroll: Cleaning workers",
                    "Payroll: Handyman / construction",
                    "Payroll: Director salary",
                    "Other expenses"
                ])
                exp_note = st.text_input("Детали (что именно?)")
                
                if st.button("💾 Провести расход", type="primary", use_container_width=True):
                    cash_ws.append_row([
                        exp_date.strftime("%Y-%m-%d"), "Expense", exp_category, 
                        exp_amount, exp_note
                    ])
                    st.toast("✅ Расход зафиксирован!")
                    st.rerun()

# ================= СТРАНИЦА 2: АНАЛИТИКА =================
elif page == "📈 Dashboard (P&L и KPI)":
    st.title("📈 Бизнес-Аналитика")
    
    if df_cash.empty or df_jobs.empty:
        st.info("Недостаточно данных для аналитики.")
    else:
        df_cash['Date'] = pd.to_datetime(df_cash['Date'])
        df_jobs['Date'] = pd.to_datetime(df_jobs['Date'])
        
        df_cash['Month'] = df_cash['Date'].dt.to_period('M').astype(str)
        df_jobs['Month'] = df_jobs['Date'].dt.to_period('M').astype(str)
        
        selected_month = st.selectbox("Период (Месяц)", df_cash['Month'].unique()[::-1])
        
        c_data = df_cash[df_cash['Month'] == selected_month]
        j_data = df_jobs[df_jobs['Month'] == selected_month]
        
        # P&L Расчеты
        c_data['Amount'] = pd.to_numeric(c_data['Amount'])
        income = c_data[c_data['Type'] == 'Income']['Amount'].sum()
        expense = c_data[c_data['Type'] == 'Expense']['Amount'].sum()
        profit = income - expense
        margin = (profit / income * 100) if income > 0 else 0
        
        # KPI Расчеты
        total_orders = len(j_data)
        avg_ticket = income / total_orders if total_orders > 0 else 0
        j_data['HandymanUpsell'] = j_data['HandymanUpsell'].astype(str).str.upper() == 'TRUE'
        handyman_upsell_rate = (j_data['HandymanUpsell'].sum() / total_orders * 100) if total_orders > 0 else 0
        avg_rating = pd.to_numeric(j_data['Rating']).mean()

        st.markdown("### 📊 P&L (Прибыли и Убытки)")
        with st.container(border=True):
            m1, m2, m3 = st.columns(3)
            m1.metric("Выручка (Revenue)", f"{income:,.0f} ₪")
            m2.metric("Расходы (Expenses)", f"{expense:,.0f} ₪")
            m3.metric("Чистая прибыль", f"{profit:,.0f} ₪", delta=f"{margin:.1f}% Margin")
            
        st.markdown("### 🎯 Weekly / Monthly KPI")
        with st.container(border=True):
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Заказов (Orders)", total_orders)
            k2.metric("Средний чек", f"{avg_ticket:,.0f} ₪")
            k3.metric("Handyman Upsell", f"{handyman_upsell_rate:.0f}%")
            k4.metric("Avg Rating", f"⭐ {avg_rating:.1f}" if pd.notna(avg_rating) else "N/A")

        st.markdown("### 📉 Структура расходов")
        exp_data = c_data[c_data['Type'] == 'Expense']
        if not exp_data.empty:
            fig_exp = px.pie(exp_data, values='Amount', names='Category', hole=0.5)
            fig_exp.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_exp, use_container_width=True)

# ================= СТРАНИЦА 3: КАЛЬКУЛЯТОР =================
elif page == "🧮 Smart Калькулятор":
    st.title("🧮 Оценка стоимости")
    st.markdown("Модель ценообразования: базовая ставка + модификаторы")
    
    with st.container(border=True):
        calc_sqm = st.number_input("Площадь (м²)", 0, 500, 100)
        calc_type = st.radio("Сложность (Task Menu)", ["Light (17 ₪/м²)", "Deep (24 ₪/м²)", "Post-Reno (30 ₪/м²)"], horizontal=True)
        
        st.markdown("#### Доп. задачи (Task Menu)")
        c1, c2 = st.columns(2)
        with c1:
            add_oven = st.checkbox("Духовка / Холодильник (+150 ₪)")
            add_windows = st.checkbox("Окна детально (+200 ₪)")
        with c2:
            add_mold = st.checkbox("Удаление плесени/извести (+100 ₪)")
            add_balcony = st.checkbox("Сложный балкон (+100 ₪)")
        
        rate = 17 if "Light" in calc_type else 24 if "Deep" in calc_type else 30
        base_price = calc_sqm * rate
        
        # Модификаторы
        big_fee = 200 if calc_sqm >= 140 else 0
        task_menu_fee = (150 if add_oven else 0) + (200 if add_windows else 0) + (100 if add_mold else 0) + (100 if add_balcony else 0)
        
        total_quote = base_price + big_fee + task_menu_fee
        
        if big_fee > 0:
            st.warning(f"Применена надбавка за большую площадь (>=140м²): +{big_fee}₪")
        if task_menu_fee > 0:
            st.info(f"Доп. задачи по Task Menu: +{task_menu_fee}₪")
            
        st.success(f"💰 Итоговая цена для клиента: {total_quote} ₪")

# ================= СТРАНИЦА 4: БАЗА =================
elif page == "📋 База заказов":
    st.title("📋 База данных (Google Sheets)")
    if df_jobs.empty:
        st.info("Заказов пока нет.")
    else:
        st.dataframe(df_jobs.sort_values(by="Date", ascending=False), use_container_width=True)
