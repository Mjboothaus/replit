import streamlit as st

# Create a very basic Streamlit app
st.set_page_config(
    page_title="Basic Streamlit Test",
    page_icon="🔍",
    layout="centered"
)

st.title("Basic Streamlit Test")
st.markdown("This is a basic test app to check if Streamlit is working properly.")

st.write("If you can see this, the Streamlit app is working correctly!")

# Add a simple input
name = st.text_input("Enter your name")
if name:
    st.write(f"Hello, {name}!")

# Add a simple button
if st.button("Click me"):
    st.success("Button clicked!")
    st.balloons()