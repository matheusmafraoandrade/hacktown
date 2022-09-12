import streamlit as st
import pandas as pd

# Minha Programação
st.header("Minha Programação")
with st.expander("Minha Programação"):
    minha_agenda = pd.DataFrame(columns = hacktown.df.columns)
    minha_agenda = pd.concat([minha_agenda, hacktown.df_selected])
    st.dataframe(minha_agenda)