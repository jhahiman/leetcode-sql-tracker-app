import streamlit as st
import json
import pandas as pd
from datetime import datetime, timedelta
import time
import altair as alt # We are using Altair for the main chart

# --- Configuration (unchanged) ---
DATA_FILE = 'leetcode_sql_tracker_data.json'
DAILY_GOAL = 25 
REMINDER_INTERVAL_MINUTES = 30 

# --- Data Loading and Saving Functions (unchanged) ---
def load_data():
    """
    Loads daily questions data from a JSON file.
    Handles migration from old 'total count' format to new 'difficulty breakdown' format.
    """
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            migrated_data = {}
            for date_key, value in data.items():
                if date_key == "leetcode_list_url":
                    migrated_data[date_key] = value
                elif isinstance(value, int):
                    migrated_data[date_key] = {"easy": value, "medium": 0, "hard": 0}
                elif isinstance(value, dict) and "easy" in value and "medium" in value and "hard" in value:
                    migrated_data[date_key] = value
                else:
                    st.warning(f"Skipping unexpected data format for date {date_key}: {value}")
            return migrated_data
    except FileNotFoundError:
        with open(DATA_FILE, 'w') as f:
            json.dump({}, f) 
        return {} 
    except json.JSONDecodeError:
        st.error("Error reading data file. It might be corrupted. Starting with empty data.")
        return {}

def save_data(data):
    """Saves daily questions data to a JSON file."""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- KPI Calculation Function (unchanged) ---
def calculate_current_streak(data, daily_goal):
    """Calculates the current consecutive streak of meeting the daily goal."""
    today = datetime.now().date()
    streak = 0
    current_date = today

    limit_date = today - timedelta(days=365 * 2) 

    while current_date >= limit_date:
        date_str = current_date.strftime("%Y-%m-%d")
        daily_problems_dict = data.get(date_str, None)

        questions_solved = 0
        if daily_problems_dict is None:
            if current_date == today:
                questions_solved = 0
            else:
                break
        elif isinstance(daily_problems_dict, int):
             questions_solved = daily_problems_dict
        elif isinstance(daily_problems_dict, dict):
            questions_solved = daily_problems_dict.get('easy', 0) + \
                               daily_problems_dict.get('medium', 0) + \
                               daily_problems_dict.get('hard', 0)
        
        if questions_solved >= daily_goal:
            streak += 1
        else:
            break
        
        current_date -= timedelta(days=1)
    return streak


# --- Initialize Session State for Reminder & App Load Time (unchanged) ---
if 'app_load_time' not in st.session_state:
    st.session_state.app_load_time = time.time()
    st.session_state.reminder_triggered = False

# --- Main App Configuration (unchanged) ---
st.set_page_config(
    page_title="LeetCode SQL Tracker",
    page_icon="📊",
    layout="wide"
)

st.title("📊 LeetCode SQL Daily Tracker")

data = load_data()

# --- LeetCode Problem List Link (Dynamic from data) ---
current_leetcode_list_url = data.get("leetcode_list_url", "https://leetcode.com/problem-list/n7bysmt7/")

link_col1, link_col2, link_col3 = st.columns([0.65, 0.25, 0.1]) 

with link_col2:
    st.markdown(
        f"""
        <div style="text-align: right; margin-top: 10px; margin-bottom: 20px;">
            <a href="{current_leetcode_list_url}" target="_blank" style="
                display: inline-block;
                padding: 8px 18px;
                background-color: #f0f2f6;
                color: #3c4043;
                border-radius: 20px;
                text-decoration: none;
                font-weight: 600;
                font-size: 0.9em;
                border: 1px solid #ddd;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                transition: all 0.2s ease-in-out;
            ">
                My LeetCode List 🔗
            </a>
        </div>
        """, unsafe_allow_html=True
    )

# --- Shared Data Preparation for Chart & KPIs ---
daily_progress_data_only = {k: v for k, v in data.items() if k != "leetcode_list_url"}

df_chart_historical_raw = pd.DataFrame.from_dict(daily_progress_data_only, orient='index')
df_chart_historical_raw = df_chart_historical_raw.reindex(columns=['easy', 'medium', 'hard']).fillna(0).astype(int)
df_chart_historical_raw.index = pd.to_datetime(df_chart_historical_raw.index)
df_chart_historical_raw = df_chart_historical_raw.sort_index()


default_days_to_display = st.session_state.get('days_to_display_input', 7) 

end_date_chart = datetime.now().date()
start_date_chart = end_date_chart - timedelta(days=default_days_to_display - 1)

full_date_range = pd.to_datetime([start_date_chart + timedelta(days=x) for x in range(default_days_to_display)])

df_chart_display = df_chart_historical_raw.reindex(full_date_range).fillna(0).astype(int)
df_chart_display = df_chart_display[['easy', 'medium', 'hard']]


df_chart_display['Questions Solved'] = df_chart_display['easy'] + df_chart_display['medium'] + df_chart_display['hard']
df_chart_display['Daily Goal'] = DAILY_GOAL
df_chart_display['Met Goal'] = df_chart_display['Questions Solved'] >= DAILY_GOAL

df_chart_data_final = df_chart_display.reset_index().rename(columns={'index': 'Date'})

df_chart_melted = df_chart_data_final.melt(
    id_vars=['Date', 'Daily Goal', 'Questions Solved', 'Met Goal'],
    value_vars=['easy', 'medium', 'hard'],
    var_name='Difficulty',
    value_name='Count'
)
df_chart_melted['Difficulty_sort_order'] = df_chart_melted['Difficulty'].map({'easy': 1, 'medium': 2, 'hard': 3})


# --- KPI Display ---
st.subheader("📊 Key Performance Indicators")

today_date_str = datetime.now().date().strftime("%Y-%m-%d")
today_difficulty_data = data.get(today_date_str, {})
questions_solved_today = today_difficulty_data.get('easy',0) + today_difficulty_data.get('medium',0) + today_difficulty_data.get('hard',0)

daily_goal_percentage = (questions_solved_today / DAILY_GOAL) * 100 if DAILY_GOAL > 0 else 0

total_solved_all_time = sum(
    v.get('easy', 0) + v.get('medium', 0) + v.get('hard', 0) 
    for k, v in data.items() if k != "leetcode_list_url" and isinstance(v, dict)
)

average_daily_last_n_days = df_chart_display['Questions Solved'].mean() if not df_chart_display.empty else 0

current_streak = calculate_current_streak(data, DAILY_GOAL)


kpi_cols = st.columns(5)

with kpi_cols[0]:
    st.metric(label="Solved Today", value=questions_solved_today)
with kpi_cols[1]:
    delta_color = "normal" if daily_goal_percentage >= 100 else "inverse"
    st.metric(label="% Goal Today", value=f"{daily_goal_percentage:.0f}%", delta_color=delta_color)
with kpi_cols[2]:
    st.metric(label="Current Streak", value=f"{current_streak} days")
with kpi_cols[3]:
    st.metric(label="Total Solved (All Time)", value=total_solved_all_time)
with kpi_cols[4]:
    st.metric(label=f"Avg. Daily (Last {default_days_to_display} days)", value=f"{average_daily_last_n_days:.1f}")

st.markdown("---")


# --- Sidebar for Input & Settings ---
with st.sidebar:
    st.header("✏️ Log Daily Progress")
    today_sidebar = datetime.now().date()
    selected_date = st.date_input("Select Date", today_sidebar, max_value=today_sidebar)

    date_str = selected_date.strftime("%Y-%m-%d")

    current_counts = data.get(date_str, {"easy": 0, "medium": 0, "hard": 0})
    if isinstance(current_counts, int):
        current_counts = {"easy": current_counts, "medium": 0, "hard": 0}

    st.subheader(f"Questions solved for {date_str}:")
    easy_solved = st.number_input(
        "Easy:",
        min_value=0,
        value=current_counts.get("easy", 0),
        step=1,
        key=f"easy_input_{date_str}"
    )
    medium_solved = st.number_input(
        "Medium:",
        min_value=0,
        value=current_counts.get("medium", 0),
        step=1,
        key=f"medium_input_{date_str}"
    )
    hard_solved = st.number_input(
        "Hard:",
        min_value=0,
        value=current_counts.get("hard", 0),
        step=1,
        key=f"hard_input_{date_str}"
    )

    if st.button("💾 Save Progress"):
        data[date_str] = {"easy": easy_solved, "medium": medium_solved, "hard": hard_solved}
        save_data(data)
        st.success(f"Progress saved for {date_str}!")
        st.rerun()

    st.markdown("---")
    st.header("⚙️ App Settings")
    
    st.subheader("🔗 LeetCode List Settings")
    new_leetcode_list_url = st.text_input(
        "Your Public LeetCode Problem List URL:",
        value=current_leetcode_list_url,
        help="Enter the URL of your public LeetCode problem list. This will be saved for all users of this app."
    )
    
    if new_leetcode_list_url != current_leetcode_list_url:
        data["leetcode_list_url"] = new_leetcode_list_url
        save_data(data)
        st.success("LeetCode list URL updated! Reloading app...")
        st.rerun()

    days_to_display_input = st.number_input(
        "Number of days to display (charts & status):",
        min_value=1,
        max_value=365,
        value=default_days_to_display,
        step=1,
        key="days_to_display_input"
    )
    
    if days_to_display_input != default_days_to_display:
        st.session_state['days_to_display_input'] = days_to_display_input
        st.rerun()

    st.markdown("---")
    st.header("⏰ Reminder Settings")
    st.info(f"Reminder will trigger {REMINDER_INTERVAL_MINUTES} minutes after app load (if active in browser).")
    if st.button("🔄 Reset Reminder Timer"):
        st.session_state.app_load_time = time.time()
        st.session_state.reminder_triggered = False
        st.success("Reminder timer reset!")

# --- Main Content Area (Dashboard - continued) ---

# --- Altair Chart Visualization (STACKED BARS - REVISED X-AXIS WITH TIMEUNIT) ---
st.subheader(f"📈 Daily SQL Progress (Last {default_days_to_display} Days)")

if df_chart_data_final.empty:
    st.info("No historical data to display for the selected period. Log some questions to see your progress chart!")
else:
    # Base chart definition for stacked bars
    base_stacked = alt.Chart(df_chart_melted).encode(
        # Use 'Date:T' (Temporal) and explicitly define TimeUnit for X-axis for correct grouping
        x=alt.X('Date:T', 
                timeUnit="yearmonthdate", # Group by day (e.g., "Jul 23")
                axis=alt.Axis(format="%b %d", title="Date") # Format labels like "Jul 23"
        ),
        y=alt.Y('Count:Q', title="Questions Solved", axis=alt.Axis(grid=True, format="d")), # Format Y-axis as integer
        color=alt.Color('Difficulty:N', # Color by 'Difficulty' field
                        scale=alt.Scale(domain=['easy', 'medium', 'hard'], range=['#34A853', '#F9AB00', '#EA4335']), # Green, Yellow, Red palette
                        legend=alt.Legend(title="Difficulty")), # Add a legend for difficulty
        order=alt.Order('Difficulty_sort_order', sort='ascending') # Ensure consistent stacking order
    )

    # Stacked Bars layer
    stacked_bars_chart = base_stacked.mark_bar().encode(
        tooltip=[ # Enhanced Tooltip for stacked bars
            alt.Tooltip('Date:T', format="%b %d", title="Date"), # Keep Date:T for tooltip for formatting
            alt.Tooltip('Difficulty:N', title="Difficulty"),
            alt.Tooltip('Count:Q', title="Solved"),
            alt.Tooltip('Questions Solved:Q', title="Total Daily Solved"),
            alt.Tooltip('Met Goal:N', title='Daily Goal Status')
        ]
    )

    # Goal line (on top of the stacked bars)
    goal_line_chart = alt.Chart(df_chart_data_final).mark_line(color='#A0A0A0', strokeWidth=2, strokeDash=[5, 5]).encode(
        # X-axis for line needs to match (Temporal with TimeUnit) for correct overlay
        x=alt.X('Date:T', timeUnit="yearmonthdate"), 
        y=alt.Y('Daily Goal:Q', title="Daily Goal"),
        tooltip=[alt.Tooltip('Daily Goal:Q', title="Goal")]
    )

    # Vertical line for today (dynamic based on current date)
    today_date_for_chart_plain = datetime.now().date() 
    today_line_data_chart = pd.DataFrame({'Date': [today_date_for_chart_plain]}) # Use plain datetime.date object here too

    today_line_chart = alt.Chart(today_line_data_chart).mark_rule(color='#4285F4', strokeWidth=2).encode(
        # X-axis for vertical line consistent (Temporal with TimeUnit)
        x=alt.X('Date:T', timeUnit="yearmonthdate", title=""), # Use 'Date:T' with timeUnit
        tooltip=[alt.Tooltip('Date:T', format="%b %d", title="Today")] # Tooltip still uses Date:T for formatting
    )

    # Layer all chart elements together
    final_chart = alt.layer(stacked_bars_chart, goal_line_chart, today_line_chart).interactive() # .interactive() allows zoom/pan
    st.altair_chart(final_chart, use_container_width=True) # Render the chart

# --- Daily Goal Status Section (Upcoming Daily Goals) ---
st.subheader("🎯 Upcoming Daily Goals")

st.markdown("""
<style>
    :root {
        --primary-accent: #1a73e8;
        --success-color: #34a853;
        --warning-color: #fbbc05;
        --error-color: #ea4335;
        --text-dark: #3c4043;
        --text-light: #5f6368;
        --border-light: rgba(223, 225, 229, 0.5);
        --bg-light: #ffffff;
        --shadow-subtle: rgba(60, 64, 67, 0.08) 0px 1px 3px 0px, rgba(60, 64, 67, 0.05) 0px 4px 8px 3px;
        --shadow-hover: rgba(60, 64, 67, 0.15) 0px 3px 6px 0px, rgba(60, 64, 67, 0.1) 0px 8px 16px 6px;
    }

    .st-emotion-cache-1r6dm7f {
        gap: 1.5rem;
    }

    .faang-card {
        background-color: var(--bg-light);
        border-radius: 12px;
        box-shadow: var(--shadow-subtle);
        padding: 20px;
        text-align: center;
        transition: all 0.2s ease-in-out;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 180px;
        border: 1px solid var(--border-light);
    }
    .faang-card:hover {
        transform: translateY(-5px);
        box-shadow: var(--shadow-hover);
    }

    .faang-card.goal-met {
        border-color: var(--success-color);
        background-color: #e6f7ed;
    }
    .faang-card.below-goal {
        border-color: var(--error-color);
        background-color: #fce8e6;
    }
    .faang-card.upcoming {
        border-color: var(--primary-accent);
        background-color: #e8f0fe;
    }

    .faang-card h4 {
        font-size: 1.3em;
        font-weight: 600;
        color: var(--text-dark);
        margin-bottom: 8px;
    }
    .faang-card .solved-count {
        font-size: 1.8em;
        font-weight: 700;
        color: var(--primary-accent);
        margin-bottom: 5px;
    }
    .faang-card.goal-met .solved-count { color: var(--success_color); }
    .faang_card.below_goal .solved_count { color: var(--error_color); }

    .faang_card .status_text {
        font_size: 1em;
        font_weight: 500;
        color: var(--text_light);
        margin_bottom: 15px;
    }
    .faang_card.goal_met .status_text { color: var(--success_color); }
    .faang_card.below_goal .status_text { color: var(--error_color); }
    .faang_card.upcoming .status_text { color: var(--primary_accent); }


    .faang_progress_container {
        background_color: #e0e0e0;
        border_radius: 50px;
        height: 10px;
        margin_top: auto;
        width: 100%;
        overflow: hidden;
    }
    .faang_progress_bar {
        height: 100%;
        border_radius: 50px;
        background_color: var(--success_color);
        transition: width 0.3s ease_in_out;
    }
    .faang_progress_bar.red { background_color: var(--error_color); }
    .faang_progress_bar.blue { background_color: var(--primary_accent); }

    .faang_percentage {
        font_size: 0.8em;
        color: var(--text_light);
        margin_top: 8px;
        font_weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# --- Prepare DataFrame for Status Cards (Next N Days) ---
today_for_status_cards = datetime.now().date()
all_status_dates = [today_for_status_cards + timedelta(days=x) for x in range(default_days_to_display)]
all_status_dates_str = [d.strftime("%Y-%m-%d") for d in all_status_dates]

df_status_cards = pd.DataFrame(index=all_status_dates_str, columns=['easy', 'medium', 'hard']).fillna(0).astype(int)

for date_str, daily_data_dict in data.items():
    if date_str in all_status_dates_str and isinstance(daily_data_dict, dict):
        df_status_cards.loc[date_str, 'easy'] = daily_data_dict.get('easy', 0)
        df_status_cards.loc[date_str, 'medium'] = daily_data_dict.get('medium', 0)
        df_status_cards.loc[date_str, 'hard'] = daily_data_dict.get('hard', 0)

df_status_cards.index = pd.to_datetime(df_status_cards.index)
df_status_cards = df_status_cards.sort_index()

df_status_cards['Questions Solved'] = df_status_cards['easy'] + df_status_cards['medium'] + df_status_cards['hard']
df_status_cards['Daily Goal'] = DAILY_GOAL
df_status_cards['Met Goal'] = df_status_cards['Questions Solved'] >= DAILY_GOAL

cols = st.columns(min(default_days_to_display, 7))

for i, (date, row) in enumerate(df_status_cards.iterrows()):
    col = cols[i % len(cols)]
    with col:
        solved_count = int(row['Questions Solved'])
        goal_status_text = ""
        card_class = ""
        progress_bar_color_class = ""
        percentage = min(100, (solved_count / DAILY_GOAL) * 100) if DAILY_GOAL > 0 else 0

        if date.date() > today_for_status_cards:
            goal_status_text = "Upcoming"
            card_class = "upcoming"
            progress_bar_color_class = "blue"
            percentage = 0
        elif row['Met Goal']:
            goal_status_text = "Goal Met! 🎉"
            card_class = "goal-met"
            progress_bar_color_class = ""
        else:
            goal_status_text = "Below Goal 📉"
            card_class = "below-goal"
            progress_bar_color_class = "red"

        st.markdown(f"""
        <div class="faang-card {card_class}">
            <h4>{date.strftime('%b %d')}</h4>
            <p class="solved-count"><b>{solved_count}</b></p>
            <p class="status-text">{goal_status_text}</p>
            <div class="faang-progress-container">
                <div class="faang-progress-bar {progress_bar_color_class}" style="width: {percentage}%;"></div>
            </div>
            <p class="faang-percentage">{percentage:.0f}%</p>
        </div>
        """, unsafe_allow_html=True)

# --- Reminder Logic ---
elapsed_time = time.time() - st.session_state.app_load_time
if elapsed_time >= REMINDER_INTERVAL_MINUTES * 60 and not st.session_state.reminder_triggered:
    st.error(f"🚨🚨 Time to do your LeetCode SQL questions! Goal: {DAILY_GOAL} questions! 🚨🚨")
    st.session_state.reminder_triggered = True

st.info(f"App loaded {int(elapsed_time)} seconds ago.")