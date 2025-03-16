import streamlit as st
import matplotlib.pyplot as plt
import plotly.express as px
import json
from fpdf import FPDF
import pandas as pd
from PIL import Image  # Add this import
import pdf

# Load questions
with open('questions.jsonl', 'r') as f:
    questions = [json.loads(line)['question'] for line in f]

# Load your images
try:
    logo = Image.open('logo.jpg')  # Replace with your logo file path
    full_form = Image.open('form.jpg')  # Replace with your full form image path
except Exception as e:
    st.error(f"Error loading images: {e}")
    logo = None
    full_form = None

# Initialize session state
if 'responses' not in st.session_state: 
    st.session_state.responses = [None] * len(questions)
if 'current_q' not in st.session_state:
    st.session_state.current_q = 0

# Helper functions
def update_question(delta):
    st.session_state.current_q = max(0, min(len(questions)-1, st.session_state.current_q + delta))

def jump_to_question(idx):
    st.session_state.current_q = idx

# CORRECTED personality calculation
def calculate_personality(responses):
    return {
        'Openness': sum(responses[4::5]),        # 10 questions (indices 4,9,14...)
        'Conscientiousness': sum(responses[3::5]), # 10 questions (indices 3,8,13...)
        'Extraversion': sum(responses[0::5]),    # 10 questions (indices 0,5,10...)
        'Agreeableness': sum(responses[1::5]),   # 10 questions (indices 1,6,11...) 
        'Neuroticism': sum(responses[2::5])      # 10 questions (indices 2,7,12...)
    }

# Sidebar navigation
st.sidebar.header("Question Navigation")
cols = st.sidebar.columns(5)
for i in range(50):
    with cols[i%5]:
        if st.button(f"{i+1}", key=f"nav_{i}", 
                    disabled=st.session_state.responses[i] is None,
                    on_click=jump_to_question, args=(i,)):
            pass

# Main content area
st.title("B etter A ssement B ehavioral E thical S ummary E valuation N avigat A ssistant")

# Create columns for the header section
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    if logo is not None:
        st.image(logo, width=150)  # Adjust width as needed

with col2:
    st.header("B.A.B.E.S.E.N.A Assessment")

with col3:
    if full_form is not None:
        st.image(full_form, width=150)  # Adjust width as needed

# Current question display
current_q = st.session_state.current_q
st.subheader(f"Question {current_q + 1}/{len(questions)}")
st.markdown(f"**{questions[current_q]}**")

# Response scale explanation
st.caption("""
**Response Scale:**
1️⃣ Strongly Disagree  
2️⃣ Disagree  
3️⃣ Neutral  
4️⃣ Agree  
5️⃣ Strongly Agree  
""")

# Answer selection
response = st.radio("Your answer:", options=[1,2,3,4,5], 
                   format_func=lambda x: ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"][x-1],
                   horizontal=True,
                   key=f"response_{current_q}")

# Store response
if response and response != st.session_state.responses[current_q]:
    st.session_state.responses[current_q] = response
    st.rerun()

# Navigation buttons
col1, col2, col3 = st.columns([1,2,1])
with col1:
    st.button("← Previous", on_click=update_question, args=(-1,), 
             disabled=current_q == 0)
with col3:
    st.button("Next →", on_click=update_question, args=(1,), 
             disabled=current_q == len(questions)-1)

# Submission and results
if st.button("Submit Final Answers", disabled=None in st.session_state.responses):
    # Calculate personality scores
    scores = calculate_personality(st.session_state.responses)
    
    # Show results
    st.success("Assessment Complete!")
    st.balloons()
    
    # Visualization
    st.header("Your Personality Profile")
    
    # Pie chart
    fig = px.pie(values=list(scores.values()), names=list(scores.keys()),
                title="Personality Traits Distribution")
    st.plotly_chart(fig)
    
    # Detailed breakdown
    st.subheader("Trait Breakdown:")
    for trait, score in scores.items():
        st.markdown(f"""
        **{trait}**: {score}/{(len(questions)//5)*5}
        {round(score/((len(questions)//5)*5)*100)}% of maximum possible
        """)
    
    # ENHANCED interpretation function
    def interpret_personality(scores):
        traits = {
            "Openness": {
                "icon": "🎨",
                "levels": [
                    (40, "High", "Highly creative and open to new experiences"),
                    (30, "Moderate", "Balanced between novelty and routine"),
                    (0, "Low", "Prefers tradition and practicality")
                ]
            },
            "Conscientiousness": {
                "icon": "📅",
                "levels": [
                    (40, "High", "Very organized and disciplined"),
                    (30, "Moderate", "Structured but flexible"),
                    (0, "Low", "Spontaneous and adaptable")
                ]
            },
            "Extraversion": {
                "icon": "🎉",
                "levels": [
                    (40, "High", "Social and energetic"),
                    (30, "Moderate", "Balanced social needs"),
                    (0, "Low", "Introverted and reserved")
                ]
            },
            "Agreeableness": {
                "icon": "🤝",
                "levels": [
                    (40, "High", "Compassionate and cooperative"),
                    (30, "Moderate", "Assertive yet kind"),
                    (0, "Low", "Independent and direct")
                ]
            },
            "Neuroticism": {
                "icon": "🧘",
                "levels": [
                    (40, "High", "Sensitive to stress"),
                    (30, "Moderate", "Generally resilient"),
                    (0, "Low", "Emotionally stable")
                ]
            }
        }

        results = []
        for trait, data in traits.items():
            score = scores[trait]
            for threshold, label, description in data["levels"]:
                if score >= threshold:
                    results.append({
                        "trait": trait,
                        "score": score,
                        "icon": data["icon"],
                        "label": label,
                        "description": description,
                        "full_text": get_full_description(trait, score)
                    })
                    break
        return results

    def get_full_description(trait, score):
        # Add comprehensive descriptions here
        descriptions = {
            "Openness": [
                "Highly creative, curious, and open to new experiences. You enjoy exploring abstract ideas and artistic expressions.",
                "Practical but imaginative, you balance novelty with familiar routines.",
                "Traditional and pragmatic, you value concrete information over abstract concepts."
            ],
            "Conscientiousness": [
                "Highly organized, responsible, and dependable. You excel in planning and executing tasks.",
                "Moderately organized, you balance structure with flexibility in your approach.",
                "Spontaneous and adaptable, you prefer to go with the flow rather than stick to a plan."
            ],
            "Extraversion": [
                "Social and outgoing, you thrive in group settings and enjoy engaging with others.",
                "Moderately social, you appreciate both social interactions and personal time.",
                "Reserved and introspective, you prefer solitary activities and quiet environments."
            ],
            "Agreeableness": [
                "Compassionate and cooperative, you prioritize harmony in relationships.",
                "Moderately agreeable, you can be assertive while still valuing kindness.",
                "Independent and direct, you prioritize honesty over tact."
            ],
            "Neuroticism": [
                "Sensitive to stress, you may experience anxiety and emotional fluctuations.",
                "Generally resilient, you handle stress but can be affected by challenges.",
                "Emotionally stable, you maintain a calm demeanor even in stressful situations."
            ]
        }
        index = 0 if score >= 40 else 1 if score >= 30 else 2
        return descriptions[trait][index]

    # Get interpretation results
    results = interpret_personality(scores)

    # Display Results
    st.success("## 🎉 Assessment Complete!")
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, 'Personality Assessment Report', 0, 1, 'C')
    
    pdf.set_font("Arial", '', 12)
    for res in results:
        pdf.cell(0, 10, f"{res['icon']} {res['trait']}: {res['score']}/50 ({res['label']})", 0, 1)
        pdf.multi_cell(0, 10, res['full_text'])
        pdf.ln(5)
    
    # Download button
    st.download_button(
        "📥 Download Full Report",
        pdf.output(dest='S').encode('latin1'),
        "personality_report.pdf",
        "application/pdf"
    )

    # Reset button
    if st.button("Take Again"):
        st.session_state.responses = [None] * len(questions)
        st.session_state.current_q = 0
        st.rerun()

# Progress indicator
progress = sum(1 for r in st.session_state.responses if r is not None)/len(questions)
st.progress(progress, text=f"Completion: {int(progress*100)}%")