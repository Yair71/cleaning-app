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
            salaries_ws = sh.worksheet("Salaries") 
            
            df_cash = pd.DataFrame(cash_ws.get_all_records())
            df_jobs = pd.DataFrame(jobs_ws.get_all_records())
            df_salaries = pd.DataFrame(salaries_ws.get_all_records())
            
            return df_cash, df_jobs, df_salaries, cash_ws, jobs_ws, salaries_ws
        except Exception as e:
            st.error("❌ Ошибка при чтении листов. Проверь, что в Google Таблице есть листы 'Cashflow', 'Jobs' и 'Salaries'.")
            st.code(traceback.format_exc())
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), None, None, None

df_cash, df_jobs, df_salaries, cash_ws, jobs_ws, salaries_ws = load_data()

# --- БОКОВОЕ МЕНЮ ---
st.sidebar.title("Cleaning OS 💎")
page = st.sidebar.radio("Навигация:", [
    "💸 Касса (Операции)", 
    "📈 Dashboard (P&L и KPI)", 
    "🧮 Smart Калькулятор",
    "📋 База заказов",
    "👷 Выплата зарплат",
    "💳 Ведомость (Зарплаты)"
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
                
                exp_category = st.selectbox("Статья расходов", [
                    "Cleaning chemicals & consumables", 
                    "Travel / fuel / parking", 
                    "Equipment & tools (buy/rent)", 
                    "Repairs & maintenance", 
                    "Marketing / ads", 
                    "Insurance", 
                    "Accountant / bookkeeping", 
                    "Phones / software", 
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
    
    # Теперь аналитика работает, даже если заказов пока нет (но есть расходы)
    if df_cash.empty and df_jobs.empty:
        st.info("Нет данных для аналитики. Добавьте заказ или расход в Кассе.")
    else:
        all_months = []
        
        if not df_cash.empty:
            df_cash['Date'] = pd.to_datetime(df_cash['Date'])
            df_cash['Month'] = df_cash['Date'].dt.to_period('M').astype(str)
            all_months.extend(df_cash['Month'].unique().tolist())
            
        if not df_jobs.empty:
            df_jobs['Date'] = pd.to_datetime(df_jobs['Date'])
            df_jobs['Month'] = df_jobs['Date'].dt.to_period('M').astype(str)
            all_months.extend(df_jobs['Month'].unique().tolist())
            
        unique_months = sorted(list(set(all_months)), reverse=True)
        
        if unique_months:
            selected_month = st.selectbox("Период (Месяц)", unique_months)
            
            c_data = df_cash[df_cash['Month'] == selected_month] if not df_cash.empty else pd.DataFrame()
            j_data = df_jobs[df_jobs['Month'] == selected_month] if not df_jobs.empty else pd.DataFrame()
            
            # P&L Расчеты
            income, expense = 0, 0
            if not c_data.empty and 'Type' in c_data.columns and 'Amount' in c_data.columns:
                c_data['Amount'] = pd.to_numeric(c_data['Amount'])
                income = c_data[c_data['Type'] == 'Income']['Amount'].sum()
                expense = c_data[c_data['Type'] == 'Expense']['Amount'].sum()
                
            profit = income - expense
            margin = (profit / income * 100) if income > 0 else 0
            
            # KPI Расчеты
            total_orders = len(j_data) if not j_data.empty else 0
            avg_ticket = income / total_orders if total_orders > 0 else 0
            
            handyman_upsell_rate, avg_rating = 0, float('nan')
            if not j_data.empty and 'HandymanUpsell' in j_data.columns and 'Rating' in j_data.columns:
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
            if not c_data.empty and 'Type' in c_data.columns:
                exp_data = c_data[c_data['Type'] == 'Expense']
                if not exp_data.empty:
                    fig_exp = px.pie(exp_data, values='Amount', names='Category', hole=0.5)
                    fig_exp.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_exp, use_container_width=True)
                else:
                    st.info("В этом месяце расходов еще нет.")
            else:
                st.info("В этом месяце расходов еще нет.")

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

# ================= СТРАНИЦА 5: ЗАРПЛАТЫ (ВВОД) =================
elif page == "👷 Выплата зарплат":
    st.title("👷 Калькулятор зарплат")
    st.markdown("Здесь ты считаешь зарплату за смену и отправляешь её в базу расходов.")

    if salaries_ws is None or cash_ws is None:
        st.warning("Нет связи с таблицами Google Sheets.")
    else:
        with st.container(border=True):
            sal_date = st.date_input("Дата работы", datetime.today())
            worker_name = st.text_input("Имя работника")
            hours_worked = st.number_input("Отработанно часов", min_value=0.0, step=0.5, value=8.0)
            
            clean_type = st.selectbox("Тип уборки", ["Тип 1 (50 ₪/час)", "Тип 2 (60 ₪/час)", "Тип 3 (70 ₪/час)"])
            
            if "Тип 1" in clean_type:
                hourly_rate = 50
            elif "Тип 2" in clean_type:
                hourly_rate = 60
            else:
                hourly_rate = 70
                
            calculated_salary = hours_worked * hourly_rate
            st.success(f"💸 К выплате: **{calculated_salary} ₪**")
            
            if st.button("📤 Опубликовать в облако", type="primary", use_container_width=True):
                if worker_name.strip() == "":
                    st.error("Пожалуйста, введи имя работника.")
                else:
                    date_str = sal_date.strftime("%Y-%m-%d")
                    salaries_ws.append_row([
                        date_str, worker_name, hours_worked, clean_type, calculated_salary
                    ])
                    cash_ws.append_row([
                        date_str, "Expense", "Payroll: Cleaning workers", calculated_salary, f"Зарплата: {worker_name} ({hours_worked}ч)"
                    ])
                    
                    st.toast(f"✅ Зарплата для {worker_name} сохранена в базе и расходах!")
                    st.rerun()

# ================= СТРАНИЦА 6: ВЕДОМОСТЬ (ИСТОРИЯ) =================
elif page == "💳 Ведомость (Зарплаты)":
    st.title("💳 Зарплатная ведомость")
    st.markdown("Сумма к выплате каждому работнику за определенный месяц.")

    if df_salaries.empty:
        st.info("В базе пока нет записей о зарплатах.")
    else:
        df_salaries['Date'] = pd.to_datetime(df_salaries['Date'])
        df_salaries['Month'] = df_salaries['Date'].dt.to_period('M').astype(str)
        df_salaries['Salary'] = pd.to_numeric(df_salaries['Salary'])
        
        # МАГИЯ ЗДЕСЬ: Убираем случайные пробелы до/после имени и делаем первую букву заглавной
        df_salaries['Worker Name'] = df_salaries['Worker Name'].astype(str).str.strip().str.title()
        
        available_months = df_salaries['Month'].unique()[::-1]
        selected_month = st.selectbox("Выберите месяц:", available_months)
        
        month_data = df_salaries[df_salaries['Month'] == selected_month]
        
        if month_data.empty:
            st.warning("Нет данных за этот месяц.")
        else:
            summary = month_data.groupby('Worker Name')[['Hours', 'Salary']].sum().reset_index()
            summary.columns = ['Имя работника', 'Всего часов', 'Итого к выплате (₪)']
            
            st.markdown(f"### Итоги за {selected_month}")
            st.dataframe(summary, use_container_width=True, hide_index=True)
            
            total_pay = summary['Итого к выплате (₪)'].sum()
            st.metric("Общий фонд оплаты труда за этот месяц", f"{total_pay:,.0f} ₪")
