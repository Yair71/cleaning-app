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

# --- ПОДКЛЮЧЕНИЕ К GOOGLE (КЭШИРУЕМ, ЧТОБЫ НЕ ТРАТИТЬ ЛИМИТЫ) ---
@st.cache_resource
def get_worksheets():
    try:
        creds_dict = json.loads(st.secrets["google_json"])
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(st.secrets["spreadsheet"]["id"])
        
        cash_ws = sheet.worksheet("Cashflow")
        jobs_ws = sheet.worksheet("Jobs")
        salaries_ws = sheet.worksheet("Salaries")
        
        return cash_ws, jobs_ws, salaries_ws
    except Exception as e:
        st.error("❌ Ошибка при подключении к Google:")
        st.code(traceback.format_exc())
        return None, None, None

# --- ЗАГРУЗКА ДАННЫХ (КЭШИРУЕМ САМИ ДАННЫЕ) ---
@st.cache_data(ttl=600) # Данные хранятся в памяти 10 минут, пока не добавим новые
def load_dataframes():
    cash_ws, jobs_ws, salaries_ws = get_worksheets()
    if cash_ws and jobs_ws and salaries_ws:
        try:
            df_cash = pd.DataFrame(cash_ws.get_all_records())
            df_jobs = pd.DataFrame(jobs_ws.get_all_records())
            df_salaries = pd.DataFrame(salaries_ws.get_all_records())
            return df_cash, df_jobs, df_salaries
        except Exception as e:
            st.error("❌ Ошибка при чтении данных.")
            st.code(traceback.format_exc())
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# Получаем объекты для записи
cash_ws, jobs_ws, salaries_ws = get_worksheets()
# Получаем данные для аналитики
df_cash, df_jobs, df_salaries = load_dataframes()

# --- БОКОВОЕ МЕНЮ ---
st.sidebar.title("Cleaning OS 💎")
page = st.sidebar.radio("Навигация:", [
    "🛒 Оформление заказа", 
    "💸 Расходы",            
    "📈 Dashboard (P&L и KPI)", 
    "📋 База заказов",
    "👷 Выплата зарплат",
    "💳 Ведомость (Зарплаты)"
])

# ================= СТРАНИЦА 1: ОФОРМЛЕНИЕ ЗАКАЗА =================
if page == "🛒 Оформление заказа":
    st.title("🛒 Оформление заказа")
    st.markdown("Здесь калькулятор автоматически считает стоимость уборки, и данные сразу идут в базу.")
    
    if jobs_ws is None or cash_ws is None:
        st.warning("Нет связи с таблицами Google Sheets.")
    else:
        with st.container(border=True):
            st.subheader("1. Детали объекта и расчет уборки")
            job_date = st.date_input("Дата заказа", datetime.today())
            job_property = st.selectbox("Категория объекта", ["Apartments", "Villas", "Handyman / Construction"])
            
            calc_sqm = st.number_input("Площадь (м²)", 0, 1000, 100, step=10)
            calc_type = st.radio("Пакет (Сложность)", ["Light (17 ₪/м²)", "Deep (24 ₪/м²)", "Post-Reno (30 ₪/м²)"], horizontal=True)
            
            st.markdown("**Доп. задачи (Task Menu):**")
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
            
            cleaning_price = base_price + big_fee + task_menu_fee
            
            if big_fee > 0:
                st.caption(f"*Включена надбавка за площадь >=140м² (+{big_fee}₪)*")
                
        with st.container(border=True):
            st.subheader("2. Услуги Handyman")
            is_handyman = st.toggle("Были ли услуги Handyman на этом заказе?")
            handyman_price = 0.0
            if is_handyman:
                handyman_price = st.number_input("Выручка за услуги Handyman (₪)", min_value=0.0, step=50.0, value=200.0)

        with st.container(border=True):
            st.subheader("3. Итоги и KPI")
            total_quote = cleaning_price + handyman_price
            
            st.success(f"💰 **Итого к оплате клиентом: {total_quote} ₪** \n\n*(Уборка: {cleaning_price} ₪ | Handyman: {handyman_price} ₪)*")
            
            job_rating = st.slider("Оценка клиента (для KPI)", 1, 5, 5)
            job_note = st.text_input("Имя клиента / Комментарий")

            if st.button("🚀 Сохранить заказ в Облако", type="primary", use_container_width=True):
                date_str = job_date.strftime("%Y-%m-%d")
                
                jobs_ws.append_row([
                    date_str, job_property, calc_sqm, 
                    calc_type, is_handyman, total_quote, job_rating
                ])
                
                if cleaning_price > 0:
                    cash_ws.append_row([
                        date_str, "Income", "Cleaning revenue", cleaning_price, f"Уборка: {job_note}"
                    ])
                    
                if is_handyman and handyman_price > 0:
                    cash_ws.append_row([
                        date_str, "Income", "Handyman revenue", handyman_price, f"Handyman: {job_note}"
                    ])
                    
                st.toast("✅ Заказ успешно сохранен и разделен по доходам!")
                load_dataframes.clear() # СБРАСЫВАЕМ КЭШ, ЧТОБЫ ДАШБОРД ОБНОВИЛСЯ
                st.rerun()

# ================= СТРАНИЦА 2: РАСХОДЫ =================
elif page == "💸 Расходы":
    st.title("💸 Фиксация расходов")
    
    if cash_ws is None:
        st.warning("Нет связи с таблицей")
    else:
        with st.container(border=True):
            exp_date = st.date_input("Дата расхода", datetime.today())
            exp_amount = st.number_input("Сумма (₪)", min_value=0.0, step=50.0)
            
            exp_category = st.selectbox("Статья расходов", [
                "Cleaning chemicals & consumables", 
                "Equipment & tools (buy/rent)", 
                "Travel / fuel / parking",
                "Marketing / ads", 
                "Insurance / Accountant", 
                "Phones / software", 
                "Handyman materials / tools",
                "Payroll: Handyman / construction", 
                "Payroll: Director salary",
                "Other expenses"
            ])
            exp_note = st.text_input("Детали (на что именно ушли деньги?)")
            
            if st.button("💾 Записать расход", type="primary", use_container_width=True):
                cash_ws.append_row([
                    exp_date.strftime("%Y-%m-%d"), "Expense", exp_category, 
                    exp_amount, exp_note
                ])
                st.toast("✅ Расход добавлен в базу!")
                load_dataframes.clear() # СБРАСЫВАЕМ КЭШ
                st.rerun()

# ================= СТРАНИЦА 3: АНАЛИТИКА =================
elif page == "📈 Dashboard (P&L и KPI)":
    st.title("📈 Бизнес-Аналитика")
    
    if df_cash.empty and df_jobs.empty:
        st.info("Нет данных для аналитики. Добавьте заказ или расход.")
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
            
            income_clean, income_handy, expense = 0, 0, 0
            if not c_data.empty and 'Type' in c_data.columns and 'Amount' in c_data.columns:
                c_data['Amount'] = pd.to_numeric(c_data['Amount'], errors='coerce').fillna(0)
                
                income_clean = c_data[(c_data['Type'] == 'Income') & (c_data['Category'] == 'Cleaning revenue')]['Amount'].sum()
                income_handy = c_data[(c_data['Type'] == 'Income') & (c_data['Category'] == 'Handyman revenue')]['Amount'].sum()
                total_income = income_clean + income_handy
                
                expense = c_data[c_data['Type'] == 'Expense']['Amount'].sum()
            else:
                total_income = 0
                
            profit = total_income - expense
            margin = (profit / total_income * 100) if total_income > 0 else 0
            
            total_orders = len(j_data) if not j_data.empty else 0
            avg_ticket = total_income / total_orders if total_orders > 0 else 0
            
            handyman_upsell_rate, avg_rating = 0, float('nan')
            if not j_data.empty and 'HandymanUpsell' in j_data.columns and 'Rating' in j_data.columns:
                j_data['HandymanUpsell'] = j_data['HandymanUpsell'].astype(str).str.upper() == 'TRUE'
                handyman_upsell_rate = (j_data['HandymanUpsell'].sum() / total_orders * 100) if total_orders > 0 else 0
                avg_rating = pd.to_numeric(j_data['Rating']).mean()

            st.markdown("### 📊 Финансовые итоги (P&L)")
            with st.container(border=True):
                m1, m2, m3 = st.columns(3)
                m1.metric("Общая выручка", f"{total_income:,.0f} ₪")
                m2.metric("Все расходы", f"{expense:,.0f} ₪")
                m3.metric("Чистая прибыль", f"{profit:,.0f} ₪", delta=f"{margin:.1f}% Margin")
            
            st.markdown("**Структура доходов:**")
            c1, c2 = st.columns(2)
            c1.info(f"🧹 Выручка Уборка: **{income_clean:,.0f} ₪**")
            c2.warning(f"🔧 Выручка Handyman: **{income_handy:,.0f} ₪**")
                
            st.markdown("### 🎯 Операционные KPI")
            with st.container(border=True):
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Всего заказов", total_orders)
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

# ================= СТРАНИЦА 4: БАЗА ЗАКАЗОВ =================
elif page == "📋 База заказов":
    st.title("📋 База данных (Google Sheets)")
    if df_jobs.empty:
        st.info("Заказов пока нет.")
    else:
        st.dataframe(df_jobs.sort_values(by="Date", ascending=False), use_container_width=True)

# ================= СТРАНИЦА 5: ЗАРПЛАТЫ (ВВОД) =================
elif page == "👷 Выплата зарплат":
    st.title("👷 Калькулятор зарплат")
    st.markdown("Считаем зарплату клинеров и отправляем в базу.")

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
                    
                    st.toast(f"✅ Зарплата для {worker_name} сохранена!")
                    load_dataframes.clear() # СБРАСЫВАЕМ КЭШ
                    st.rerun()

# ================= СТРАНИЦА 6: ВЕДОМОСТЬ (ИСТОРИЯ) =================
elif page == "💳 Ведомость (Зарплаты)":
    st.title("💳 Зарплатная ведомость")
    st.markdown("Сумма к выплате каждому клинеру за выбранный месяц.")

    if df_salaries.empty:
        st.info("В базе пока нет записей о зарплатах.")
    else:
        df_salaries['Date'] = pd.to_datetime(df_salaries['Date'])
        df_salaries['Month'] = df_salaries['Date'].dt.to_period('M').astype(str)
        df_salaries['Salary'] = pd.to_numeric(df_salaries['Salary'])
        
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
            st.metric("Общий фонд оплаты труда (клинеры) за месяц", f"{total_pay:,.0f} ₪")
