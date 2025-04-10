
import streamlit as st
from streamlit_function import SolutionApp

def main():
    cols = st.columns([6, 1])
    with cols[0]:
        st.title("🔧 OptRail Lösungs-Analyse")
    with cols[1]:
        if st.button("🔄 Neustart", key="reset_button_clicked"):
            st.session_state.clear()
            st.rerun()

    app = SolutionApp()
    app.run()

if __name__ == "__main__":
    main()