import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
# --- НАСТРОЙКИ UI ---
st.set_page_config(page_title="Cleaning OS Cloud", page_icon="✨", layout="centered", initial_sidebar_state="collapsed")


# --- ФУНКЦИЯ ПОДКЛЮЧЕНИЯ (ДЕТЕКТОР ОШИБОК) ---
def get_gsheet():
    try:
        creds_dict = json.loads(st.secrets["google_json"])
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(st.secrets["spreadsheet"]["id"])
        return sheet
    except gspread.exceptions.APIError as e:
        # Это вытащит точный ответ от Google!
        st.error(f"❌ Google API сказал: {e.response.text}")
        return None
    except Exception as e:
        st.error(f"❌ Системная ошибка: {repr(e)}")
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
            st.error(f"Не найдены листы 'Cashflow' или 'Jobs'. Проверь названия в Google Таблице. Ошибка: {e}")
            return pd.DataFrame(), pd.DataFrame(), None, None
    return pd.DataFrame(), pd.DataFrame(), None, None

# Инициализация данных
df_cash, df_jobs, cash_ws, jobs_ws = load_data()

# --- БОКОВОЕ МЕНЮ ---
st.sidebar.title("Cleaning OS 🛠️")
page = st.sidebar.radio("Навигация:", [
    "💸 Касса (Ввод данных)", 
    "📊 Аналитика бизнеса", 
    "🧮 Калькулятор цен",
    "📋 База заказов"
])

# ================= СТРАНИЦА 1: КАССА =================
if page == "💸 Касса (Ввод данных)":
    st.title("💸 Касса")
    
    action = st.radio("Что делаем?", ["✅ Закрыть заказ (Доход)", "🛒 Записать расход"], horizontal=True)
    
    if action == "✅ Закрыть заказ (Доход)":
        if jobs_ws is None:
            st.warning("Нет связи с таблицей")
        else:
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
                job_handyman = st.toggle("🔧 Был апсейл Handyman?")
                job_rating = st.slider("Оценка клиента", 1, 5, 5)
                job_note = st.text_input("Имя клиента / Адрес")

            if st.button("🚀 Сохранить заказ в Облако", type="primary", use_container_width=True):
                # Добавляем в лист Jobs
                jobs_ws.append_row([
                    job_date.strftime("%Y-%m-%d"), job_property, job_sqm, 
                    job_type, job_handyman, job_revenue, job_rating
                ])
                # Добавляем в лист Cashflow как доход
                cash_ws.append_row([
                    job_date.strftime("%Y-%m-%d"), "Income", f"Revenue - {job_property}", 
                    job_revenue, job_note
                ])
                st.toast("✅ Сохранено в Google Sheets!")
                st.rerun()
            
    elif action == "🛒 Записать расход":
        if cash_ws is None:
            st.warning("Нет связи с таблицей")
        else:
            with st.container(border=True):
                st.subheader("Новая покупка")
                exp_date = st.date_input("Дата", datetime.today())
                exp_amount = st.number_input("Сумма покупки (₪)", min_value=0.0, step=50.0)
                exp_category = st.selectbox("Категория расходов", [
                    "Химия и расходники", "Бензин / Парковка", "Оборудование", 
                    "Ремонт авто/техники", "Реклама", "Зарплата", "Прочее"
                ])
                exp_note = st.text_input("Что именно купили?")
                
                if st.button("💾 Записать расход", type="primary", use_container_width=True):
                    cash_ws.append_row([
                        exp_date.strftime("%Y-%m-%d"), "Expense", exp_category, 
                        exp_amount, exp_note
                    ])
                    st.toast("✅ Расход записан!")
                    st.rerun()

# ================= СТРАНИЦА 2: АНАЛИТИКА =================
elif page == "📊 Аналитика бизнеса":
    st.title("📊 P&L Отчет")
    
    if df_cash.empty:
        st.info("В Google Таблице пока нет данных.")
    else:
        df_cash['Date'] = pd.to_datetime(df_cash['Date'])
        df_cash['Month'] = df_cash['Date'].dt.to_period('M').astype(str)
        
        selected_month = st.selectbox("Выбрать месяц", df_cash['Month'].unique()[::-1])
        month_data = df_cash[df_cash['Month'] == selected_month]
        
        income = pd.to_numeric(month_data[month_data['Type'] == 'Income']['Amount']).sum()
        expense = pd.to_numeric(month_data[month_data['Type'] == 'Expense']['Amount']).sum()
        profit = income - expense
        
        with st.container(border=True):
            st.metric("💵 Выручка", f"{income:,.0f} ₪")
            st.metric("🔥 Расходы", f"{expense:,.0f} ₪")
            st.metric("💎 Чистая прибыль", f"{profit:,.0f} ₪", 
                      delta=f"{(profit/income*100):.1f}% маржа" if income>0 else "0")
        
        st.subheader("Куда ушли деньги?")
        exp_data = month_data[month_data['Type'] == 'Expense']
        if not exp_data.empty:
            fig_exp = px.pie(exp_data, values='Amount', names='Category', hole=0.5)
            fig_exp.update_layout(margin=dict(t=0, b=0, l=0, r=0))
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
            st.warning(f"Надбавка за большую площадь (>=140м²): +{big_fee}₪")
            
        total_quote = base_price + big_fee
        st.success(f"💰 Итоговая цена: {total_quote} ₪")

# ================= СТРАНИЦА 4: БАЗА =================
elif page == "📋 База заказов":
    st.title("📋 История из Google Sheets")
    if df_jobs.empty:
        st.info("Заказов пока нет.")
    else:
        st.dataframe(df_jobs[['Date', 'Property', 'Revenue', 'Rating']].sort_values(by="Date", ascending=False), use_container_width=True)
