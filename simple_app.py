import streamlit as st

st.title("Simple Streamlit Test App")
st.write("This is a test to see if Streamlit is working properly.")

st.subheader("Counter Example")
count = st.button("Click me")
if count:
    st.write("Button was clicked!")
    st.balloons()