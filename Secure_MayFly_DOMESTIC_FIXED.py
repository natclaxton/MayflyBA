import streamlit as st
import pandas as pd
import re
from datetime import datetime, timedelta
from fpdf import FPDF
import hashlib
import pytz

# === Secure Password Hashing ===
def get_hashed_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

CORRECT_PASSWORD_HASH = get_hashed_password("MayFly2025!")

# === Entrance Page – Welcome & Password ===
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def login_page():
    st.markdown(
        "<h1 style='text-align:center; color:#3e577d;'>WELCOME TO THE MAYFLY GENERATOR</h1>",
        unsafe_allow_html=True
    )
    pwd = st.text_input("ENTER PASSWORD", type="password", key="login_pwd")
    if st.button("SUBMIT"):
        if get_hashed_password(pwd) == CORRECT_PASSWORD_HASH:
            st.session_state.authenticated = True
        else:
            st.error("❌ PASSWORD INCORRECT. TRY AGAIN.")

if not st.session_state.authenticated:
    login_page()
    st.stop()

# === Page Config ===
st.set_page_config(
    page_title="BA – MayFly Generator",
    page_icon="✈️",
    layout="centered"
)

# === Dark Mode Toggle ===
dark_mode = st.checkbox("Enable Dark Mode")

# === Theming CSS ===
if dark_mode:
    st.markdown("""
    <style>
      .block-container { max-width:800px; margin:auto; }
      [data-testid="stAppViewContainer"] {
        background-color: #1a1a1a !important;
        color: #69c9ff !important;
        font-family: "Mylus Modern", sans-serif;
      }
      .stTextInput label,
      .stDateInput label,
      .stSelectbox label,
      .stRadio label,
      .stTextArea label {
        color: #69c9ff !important;
        text-transform: uppercase;
        font-family: "Mylus Modern", sans-serif;
      }
      .stButton>button {
        background-color: #327acb !important;
        color: #FFFFFF !important;
        text-transform: uppercase;
        font-family: "Mylus Modern", sans-serif;
      }
      h4 {
        font-size: 16px !important;
      }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
      .block-container { max-width:800px; margin:auto; }
      [data-testid="stAppViewContainer"] {
        background-color: #FFFFFF !important;
        color: #3e577d !important;
        font-family: "Mylus Modern", sans-serif;
      }
      .stTextInput label,
      .stDateInput label,
      .stSelectbox label,
      .stRadio label,
      .stTextArea label {
        color: #3e577d !important;
        text-transform: uppercase;
        font-family: "Mylus Modern", sans-serif;
      }
      .stButton>button {
        background-color: #69c9ff !important;
        color: #FFFFFF !important;
        text-transform: uppercase;
        font-family: "Mylus Modern", sans-serif;
      }
      h4 {
        font-size: 16px !important;
      }
    </style>
    """, unsafe_allow_html=True)

# === Header – Title Only ===
st.markdown(
    "<h1 style='text-align:center; color:#3e577d; margin-bottom:0;'>BA – MAYFLY GENERATOR</h1>",
    unsafe_allow_html=True
)
st.markdown("---")

# === Flight Lists ===
DOMESTIC_ROUTES = [
    "LHRABZ","LHRINV","LHRGLA","LHREDI","LHRBHD",
    "LHRNCL","LHRJER","LHRMAN","LHRBFS","LHRDUB"
]
T3_FLIGHTS = [
    "BA159","BA227","BA247","BA253","BA289","BA336","BA340","BA350","BA366","BA368","BA370",
    "BA372","BA374","BA376","BA378","BA380","BA382","BA386","BA408","BA416","BA418",
    "BA422","BA490","BA492","BA498","BA532","BA608","BA616","BA618","BA690","BA696","BA700",
    "BA702","BA704","BA706","BA760","BA762","BA764","BA766","BA770","BA790","BA792","BA802",
    "BA806","BA848","BA852","BA854","BA856","BA858","BA860","BA862","BA864","BA866","BA868",
    "BA870","BA872","BA874","BA882","BA884","BA886","BA892","BA896","BA918","BA920"
]
LGW_FLIGHTS = [
    'BA2640','BA2704','BA2670','BA2740','BA2624','BA2748','BA2676','BA2758','BA2784','BA2610',
    'BA2606','BA2574','BA2810','BA2666','BA2614','BA2716','BA2808','BA2660','BA2680','BA2720',
    'BA2642','BA2520','BA2161','BA2037','BA2754','BA2239','BA1480','BA2159','BA2167','BA2780',
    'BA2203','BA2702','BA2756','BA2263','BA2612','BA2794','BA2039','BA2812','BA2752','BA2273',
    'BA2602','BA2682','BA2662','BA2608','BA2644','BA2650','BA2576','BA2590','BA2722','BA2816',
    'BA2596','BA2656','BA2668','BA2672','BA2572'
]

# === PDF Styling ===
BA_BLUE   = (0, 32, 91)
GREEN     = (198, 239, 206)   # <70% LF
AMBER     = (255, 229, 153)   # 70–90% LF
LIGHT_RED = (255, 204, 204)   # >90% LF

class BA_PDF(FPDF):
    def __init__(self, date_str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.date_str = date_str

    def header(self):
        self.set_fill_color(*BA_BLUE)
        self.set_text_color(255,255,255)
        self.set_font('Arial','B',14)
        self.cell(0,10,f'MayFly {self.date_str} - British Airways',
                  ln=True,align='C',fill=True)
        self.ln(5)
        self.set_font('Arial','I',8)
        self.set_text_color(0)
        self.multi_cell(0,5,
            "Please note, Conformance times below are for landside only. "
            "For connections, add 5 minutes.",
            align='C'
        )
        self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font('Arial','I',8)
        self.set_text_color(100)
        self.cell(0,8,'Confidential © 2025 | Generated by British Airways',
                  0,0,'C')

    def flight_table(self, data):
        headers = ['Flight No','Aircraft','Route','ETD','Conformance','Load']
        widths  = [30,25,30,30,30,20]
        # header row
        self.set_font('Arial','B',8.5)
        self.set_fill_color(*BA_BLUE)
        self.set_text_color(255,255,255)
        for i,h in enumerate(headers):
            self.cell(widths[i],6,h,1,0,'C',True)
        self.ln()
        # data rows
        self.set_font('Arial','',7.5)
        self.set_text_color(0)
        for _,row in data.iterrows():
            for i,key in enumerate([
                "Flight Number","Aircraft Type","Route",
                "ETD","Conformance Time","Load Factor"
            ]):
                fill=False
                if key=="Load Factor":
                    lf=int(row["Load Factor"].rstrip('%'))
                    if lf<70:
                        self.set_fill_color(*GREEN); fill=True
                    elif lf<=90:
                        self.set_fill_color(*AMBER); fill=True
                    else:
                        self.set_fill_color(*LIGHT_RED); fill=True
                self.cell(widths[i],6,str(row[key]),1,0,'C',fill)
            self.ln()

def parse_txt(content, filter_type):
    lines=content.strip().split('\n')
    flights=[]; utc=pytz.utc; i=0
    while i<len(lines):
        if lines[i].startswith("BA"):
            try:
                fn=lines[i].strip()
                ac=lines[i+2].strip()
                rt=re.sub(r"\s+","",lines[i+3].strip().upper())
                m1=re.search(r"STD: \d{2} \w+ - (\d{2}:\d{2})z",lines[i+4])
                m2=re.search(r"(\d{1,3})%Status",lines[i+8])
                if m1 and m2:
                    t,lf=m1.group(1),int(m2.group(1))
                    dt=datetime.strptime(t,"%H:%M"); dt=utc.localize(dt)
                    etd=(dt+timedelta(hours=1)).strftime("%H:%M")
                    cnf=(dt+timedelta(minutes=25)).strftime("%H:%M")
                    flights.append({
                        "Flight Number":fn,
                        "Aircraft Type":ac,
                        "Route":rt,
                        "ETD":etd,
                        "ETD Local":dt.strftime("%H:%M"),
                        "Conformance Time":cnf,
                        "Load Factor":f"{lf}%",
                        "Load Factor Numeric":lf
                    })
            except:
                pass
        i+=1
    df=pd.DataFrame(flights)
    if not df.empty:
        if filter_type=="Flights above 90%":
            df=df[df["Load Factor Numeric"]>=90]
        elif filter_type=="Flights above 70%":
            df=df[df["Load Factor Numeric"]>=70]
        elif filter_type=="Domestic":
            df=df[df["Route"].isin(DOMESTIC_ROUTES)]
        df=df.sort_values("ETD Local")
    return df

# === UI Inputs ===
st.markdown("<h4 style='color:#3e577d;'>SELECT MAYFLY DATE</h4>", unsafe_allow_html=True)
selected_date = st.date_input("", datetime.today(), format="DD/MM/YYYY")
date_str      = selected_date.strftime("%d %B")

st.markdown("<h4 style='color:#3e577d;'>SELECT STATION</h4>", unsafe_allow_html=True)
station       = st.selectbox("", ["All Stations","T3","T5","LGW"])

st.markdown("<h4 style='color:#3e577d;'>CHOOSE FILTER</h4>", unsafe_allow_html=True)
filter_option = st.radio("", ["All Flights","Flights above 90%","Flights above 70%","Domestic"])

st.markdown("<h4 style='color:#3e577d;'>FILTER BY DEPARTURE HOUR</h4>", unsafe_allow_html=True)
min_hour, max_hour = st.slider(
    "", 0, 23, (0, 23),
    help="Show flights departing between these UTC hours"
)

st.markdown("<h4 style='color:#3e577d;'>LIVE MAYFLY PREVIEW - Paste Below</h4>", unsafe_allow_html=True)
text_input = st.text_area("", height=200)

if text_input:
    df = parse_txt(text_input, filter_option)
    if station=="T3":
        df=df[df["Flight Number"].isin(T3_FLIGHTS)]
    elif station=="T5":
        df=df[~df["Flight Number"].isin(T3_FLIGHTS)]
    elif station=="LGW":
        df=df[df["Flight Number"].isin(LGW_FLIGHTS)]

    # apply time‐window
    df = df[df["ETD Local"].apply(lambda t: min_hour <= int(t.split(":")[0]) <= max_hour)]

    if not df.empty:
        st.dataframe(df.drop(columns="Load Factor Numeric"), use_container_width=True)
        st.success(f"Processed {len(df)} flights ({filter_option}, {station}).")
        with st.spinner("Generating PDF…"):
            pdf=BA_PDF(date_str,'P','mm','A4')
            pdf.set_auto_page_break(True,10)
            pdf.add_page()
            pdf.flight_table(df)
            tmp="/tmp/BA_MayFly_Output.pdf"
            pdf.output(tmp)
        with open(tmp,"rb") as f:
            st.download_button("Download MayFly PDF", f,
                file_name=f"BA_MayFly_{date_str.replace(' ','_')}.pdf")
        st.info("Confidential © 2025  |  Generated by British Airways")
    else:
        st.error("No valid flights found with current filter.")
