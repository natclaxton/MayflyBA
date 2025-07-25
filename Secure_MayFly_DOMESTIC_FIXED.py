import streamlit as st
import pandas as pd
import re
from datetime import datetime, timedelta, time
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
st.set_page_config(page_title="BA – MayFly Generator", page_icon="✈️", layout="centered")

# === Dark Mode Toggle ===
dark_mode = st.checkbox("Enable Dark Mode")

# === Theming CSS ===
if dark_mode:
    st.markdown("""<style>/* dark mode CSS here */</style>""", unsafe_allow_html=True)
else:
    st.markdown("""<style>/* light mode CSS here */</style>""", unsafe_allow_html=True)

# === Header ===
st.markdown(
    "<h1 style='text-align:center; color:#3e577d; margin-bottom:0;'>BA – MAYFLY GENERATOR</h1>",
    unsafe_allow_html=True
)
st.markdown("---")

# === Flight Lists & Definitions ===
DOMESTIC_ROUTES = ["LHRABZ","LHRINV","LHRGLA","LHREDI","LHRBHD",
                   "LHRNCL","LHRJER","LHRMAN","LHRBFS","LHRDUB"]
T3_FLIGHTS = [
    "BA159","BA227","BA247","BA253","BA289","BA336","BA340","BA350","BA366",
    "BA368","BA370","BA372","BA374","BA376","BA378","BA380","BA382","BA386",
    "BA408","BA416","BA418","BA422","BA490","BA492","BA498","BA532","BA608",
    "BA616","BA618","BA690","BA696","BA700","BA702","BA704","BA706","BA760",
    "BA762","BA764","BA766","BA770","BA790","BA792","BA802","BA806","BA848",
    "BA852","BA854","BA856","BA858","BA860","BA862","BA864","BA866","BA868",
    "BA870","BA872","BA874","BA882","BA884","BA886","BA892","BA896","BA918","BA920"
]
LGW_FLIGHTS = [
    "BA2640","BA2704","BA2670","BA2740","BA2624","BA2748","BA2676","BA2758","BA2784",
    "BA2610","BA2606","BA2574","BA2810","BA2666","BA2614","BA2716","BA2808","BA2660",
    "BA2680","BA2720","BA2642","BA2520","BA2161","BA2037","BA2754","BA2239","BA1480",
    "BA2159","BA2167","BA2780","BA2203","BA2702","BA2756","BA2263","BA2612","BA2794",
    "BA2039","BA2812","BA2752","BA2273","BA2602","BA2682","BA2662","BA2608","BA2644",
    "BA2650","BA2576","BA2590","BA2722","BA2816","BA2596","BA2656","BA2668","BA2672","BA2572"
]
SHORT_HAUL_TYPES = ["320","32N","32Q","319","32A"]

# === PDF Styling ===
BA_BLUE   = (0, 32, 91)
GREEN     = (198, 239, 206)
AMBER     = (255, 229, 153)
LIGHT_RED = (255, 204, 204)

class BA_PDF(FPDF):
    def __init__(self, date_str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.date_str = date_str

    def header(self):
        self.set_fill_color(*BA_BLUE)
        self.set_text_color(255,255,255)
        self.set_font('Arial','B',14)
        self.cell(0,10,f'MayFly {self.date_str} - British Airways', ln=True, align='C', fill=True)
        self.ln(5)
        self.set_font('Arial','I',8)
        self.set_text_color(0)
        self.multi_cell(
            0,5,
            "Please note, Conformance times below are for landside only. For connections, add 5 minutes.",
            align='C'
        )
        self.ln(3)

    def footer(self):
        # Note at bottom
        self.set_y(-25)
        self.set_font('Arial','I',6)
        self.set_text_color(0)
        self.multi_cell(
            0,5,
            "if customers flight is delayed please cross check with JFE/FLY to ensure the customer is within the conformance time",
            align='C'
        )
        # Confidential footer
        self.set_y(-12)
        self.set_font('Arial','I',8)
        self.set_text_color(100)
        self.cell(0,8,'Confidential © 2025 | Generated by British Airways', 0, 0, 'C')

    def flight_table(self, data):
        headers = ['Flight No','Aircraft','Route','STD','Conformance','Load']
        widths  = [30,25,30,30,30,20]
        # header row
        self.set_font('Arial','B',8.5)
        self.set_fill_color(*BA_BLUE)
        self.set_text_color(255,255,255)
        for w,h in zip(widths, headers):
            self.cell(w,6,h,1,0,'C',True)
        self.ln()
        # data rows
        self.set_font('Arial','',7.5)
        self.set_text_color(0)
        for _, row in data.iterrows():
            for w,key in zip(widths, [
                "Flight Number","Aircraft Type","Route",
                "ETD","Conformance Time","Load Factor"
            ]):
                fill = False
                if key == "Load Factor":
                    lf = int(row["Load Factor"].rstrip('%'))
                    if lf < 70:
                        self.set_fill_color(*GREEN); fill = True
                    elif lf <= 90:
                        self.set_fill_color(*AMBER); fill = True
                    else:
                        self.set_fill_color(*LIGHT_RED); fill = True
                self.cell(w,6,str(row[key]),1,0,'C',fill)
            self.ln()

def parse_txt(content):
    lines = content.strip().split('\n')
    flights = []
    utc = pytz.utc
    i = 0
    while i < len(lines):
        if lines[i].startswith("BA"):
            try:
                fn = lines[i].strip()
                ac = lines[i+2].strip()
                rt = re.sub(r"\s+","",lines[i+3].strip().upper())
                m1 = re.search(r"STD: \d{2} \w+ - (\d{2}:\d{2})z", lines[i+4])
                m2 = re.search(r"(\d{1,3})%Status", lines[i+8])
                if m1 and m2:
                    t, lf = m1.group(1), int(m2.group(1))
                    dt = utc.localize(datetime.strptime(t, "%H:%M"))
                    flights.append({
                        "Flight Number": fn,
                        "Aircraft Type": ac,
                        "Route": rt,
                        "ETD": (dt + timedelta(hours=1)).strftime("%H:%M"),
                        "ETD Local": dt.strftime("%H:%M"),
                        "Conformance Time": (dt + timedelta(minutes=25)).strftime("%H:%M"),
                        "Load Factor": f"{lf}%",
                        "Load Factor Numeric": lf
                    })
                    # skip the lines we just consumed to avoid duplicates
                    i += 9
                    continue
            except:
                pass
        i += 1
    df = pd.DataFrame(flights)
    return df.sort_values("ETD Local") if not df.empty else df

# === UI Inputs ===
st.markdown("<h4 style='color:#3e577d;'>SELECT MAYFLY DATE</h4>", unsafe_allow_html=True)
selected_date = st.date_input("", datetime.today(), format="DD/MM/YYYY")
date_str      = selected_date.strftime("%d %B")

st.markdown("<h4 style='color:#3e577d;'>SELECT STATION</h4>", unsafe_allow_html=True)
station = st.selectbox("", ["All Stations","T3","T5","LGW"])

st.markdown("<h4 style='color:#3e577d;'>CHOOSE FILTERS</h4>", unsafe_allow_html=True)
filter_options = st.multiselect(
    "",
    options=["All Flights","Flights above 90%","Flights above 70%","Domestic","Short Haul"],
    default=["All Flights"]
)

st.markdown("<h4 style='color:#3e577d;'>FILTER BY DEPARTURE HOUR</h4>", unsafe_allow_html=True)
min_h, max_h = st.slider("", 0, 23, (0, 23), help="Show flights departing between these UTC hours")

st.markdown("<h4 style='color:#3e577d;'>LIVE MAYFLY PREVIEW - Paste Below</h4>", unsafe_allow_html=True)
text_input = st.text_area("", height=200)

# === Countdown to next refresh at 00:00 UTC & 12:00 UTC ===
now = datetime.now(pytz.utc)
today = now.date()
times = [
    datetime.combine(today, time(0,0), tzinfo=pytz.utc),
    datetime.combine(today, time(12,0), tzinfo=pytz.utc),
    datetime.combine(today + timedelta(days=1), time(0,0), tzinfo=pytz.utc)
]
next_time = min(t for t in times if t > now)
secs = int((next_time - now).total_seconds())
h, r = divmod(secs, 3600)
m, s = divmod(r, 60)
bst_time = next_time + timedelta(hours=1)
st.markdown(f"**Next refresh: {next_time.strftime('%H:%M')} UTC / {bst_time.strftime('%H:%M')} BST in {h:02d}:{m:02d}:{s:02d}**")
st.markdown("[OpsDashboard](https://opsdashboard.baplc.com/#/search)")

if text_input:
    df = parse_txt(text_input)

    # Station filter
    if station == "T3":
        df = df[df["Flight Number"].isin(T3_FLIGHTS)]
    elif station == "T5":
        df = df[~df["Flight Number"].isin(T3_FLIGHTS)]
    elif station == "LGW":
        df = df[df["Flight Number"].isin(LGW_FLIGHTS)]

    # Apply filters
    if "All Flights" not in filter_options:
        if "Flights above 90%" in filter_options:
            df = df[df["Load Factor Numeric"] >= 90]
        if "Flights above 70%" in filter_options:
            df = df[df["Load Factor Numeric"] >= 70]
        if "Domestic" in filter_options:
            df = df[df["Route"].isin(DOMESTIC_ROUTES)]
        if "Short Haul" in filter_options:
            df = df[df["Aircraft Type"].isin(SHORT_HAUL_TYPES)]

    # Time window
    df = df[df["ETD Local"].apply(lambda t: min_h <= int(t.split(":")[0]) <= max_h)]

    if not df.empty:
        st.dataframe(df.drop(columns="Load Factor Numeric"), use_container_width=True)
        st.success(f"Processed {len(df)} flights ({station}, filters: {filter_options}).")
        with st.spinner("Generating PDF…"):
            pdf = BA_PDF(date_str, 'P', 'mm', 'A4')
            pdf.set_auto_page_break(True,10)
            pdf.add_page()
            pdf.flight_table(df)
            tmp = "/tmp/BA_MayFly_Output.pdf"
            pdf.output(tmp)
        with open(tmp, "rb") as f:
            st.download_button(
                "Download MayFly PDF", f,
                file_name=f"BA_MayFly_{date_str.replace(' ','_')}.pdf"
            )
        st.info("Confidential © 2025  |  Generated by British Airways")
    else:
        st.error("No valid flights found with current filter.")
