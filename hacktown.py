### Requirements
#from datetime import timezone
#from tkinter import FALSE
import requests
from bs4 import BeautifulSoup
import lxml
import pandas as pd
import numpy as np
import streamlit as st
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode

st.title('Programação Hacktown')

days = {0:'Quinta',1:'Sexta',2:'Sábado',3:'Domingo'}

@st.cache(allow_output_mutation=True)
def hacktown(link: str) -> pd.DataFrame:
  """
  Função que coleta os dados dos eventos via web scraping da planilha de programação do Hacktown, dividida por dias do evento.
  Em seguida, itera pelos dias definidos no dicionário 'days' para coletar todos os dados dos eventos correspondentes ao dia e preencher o dataframe 'mydata'.
  """  
  # Create object page
  page = requests.get(link)

  # parser-lxml = Change html to Python friendly format
  # Obtain page's information
  soup = BeautifulSoup(page.text, 'lxml')

  # Create a dataframe
  headers = ['Horario', 'Evento', 'Descrição', 'Local', 'Tipo', 'Dia']
  mydata = pd.DataFrame(columns=headers)

  for index, table in enumerate(soup.find_all('table')):
    dia = days[index]
    # Create a for loop to fill mydata
    for j in table.find_all('tr')[1:]:
      row_data = j.find_all('td')
      row = [i.text for i in row_data]
      row.append(dia)
      length = len(mydata)
      mydata.loc[length] = row

  return mydata

df = pd.DataFrame(hacktown(
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vTUAuTwwFq_debnSmBPcUMg3B_9kx76J_BygLDCYkGb9BNG8AvIx27wouDrg6pL3r8Vo_oBFYx7eNp4/pubhtml?gid=0")
    )

# Manipular os horários de início e fim
df['Início'] = df['Horario'].str.split(' ').str[0]
df['Fim'] = df['Horario'].str.split(' ').str[-1]
conditions = [(df['Início'] == df['Fim']), (df['Início'] != df['Fim'])]
choices = ["", df['Fim']]
df['Fim'] = np.select(conditions, choices, default="")
df.drop(columns=['Horario'], axis=1, inplace=True)
df['Início'] = df['Início'].str.replace('^8h','08h', regex=True).replace('^9h','09h', regex=True).replace('','16h')

### Componentes da barra lateral: filtro de data, horário e palavra-chave
with st.sidebar:
    # Logo Hacktown
    st.image('hacktown_logo.png')

    # Lista de dias do evento + opção "todos"
    dates = list(days.values())
    dates.append('Todos')
    dates = dates[-1:] + dates[:-1]
    date = st.selectbox("Dia", dates)

    # Filtro de dia e horário. OBS: Se eu filtrar por todas as datas, terei todos os horários. Caso contrário, terei os horários disponíveis no dia
    if date =='Todos':
        time = st.selectbox("Horário", ["Todos"])
    else:
        times = sorted(list(set(df[df['Dia']==date]['Início'])))
        times.append('Todos')
        times = times[-1:] + times[:-1]
        time = st.selectbox("Horário", times)

    # Filtro de tema
    theme = st.text_input("Palavra-chave", help="Busca por evento, descrição, local ou tipo.\
                                                 Para limpar o filtro de palavra chave, pressione Enter com o campo de busca vazio.")

    st.empty()
    st.empty()
    st.empty()
    st.write("Desenvolvido por Matheus Mafra")
    st.markdown("[![linkedin](https://commons.wikimedia.org/wiki/File:LinkedIn_icon.svg)](https://www.linkedin.com/in/matheus-andrade-122b34180/)")
    st.write("https://www.linkedin.com/in/matheus-andrade-122b34180/")

### Componentes da página principal 
with st.container():
    # Aplicar filtro de tema
    if theme != "":
        df = df[(df['Evento'].str.contains(theme, case=False)) |
                (df['Descrição'].str.contains(theme, case=False))|
                (df['Local'].str.contains(theme, case=False))|
                (df['Tipo'].str.contains(theme, case=False))]
    else:
        df = df

    # Aplicar filtro de dia e horário (com o filtro de tema já aplicado)
    if date == 'Todos':
        df = df.reset_index(drop=True)
    elif time == 'Todos':
        df = df[(df['Dia']==date)].reset_index(drop=True)
    else:
        df = df[(df['Dia']==date) & (df['Início']==time)].reset_index(drop=True)

    # Habilitar seleção múltipla
    mult_select = st.checkbox("Habilitar Seleção Múltipla", help="Clique para habilitar seleção de múltiplos eventos ao mesmo tempo.")
    if mult_select:
        ms = 'multiple'
    else:
        ms = 'single'

    # Configurações tabela Ag Grid
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=10) #Add pagination
    gb.configure_side_bar() #Add a sidebar
    gb.configure_selection(ms, use_checkbox=True, groupSelectsChildren="Group checkbox select children") #Enable multi-row selection
    gridOptions = gb.build()

    # Construção tabela Ag Grid
    grid_response = AgGrid(
        df,
        gridOptions=gridOptions,
        data_return_mode='AS_INPUT',
        #update_mode=GridUpdateMode.SELECTION_CHANGED,
        update_mode='MODEL_CHANGED', 
        fit_columns_on_grid_load=True,
        enable_enterprise_modules=True,
        reload_data=True,
        width='100%'
        #height=700, 
        #theme='ALPINE', #Add theme color to the table
    )

    # Filtro de linhas selecionadas
    data = grid_response['data']
    selected = grid_response['selected_rows'] 
    df_selected = pd.DataFrame(selected) #Pass the selected rows to a new dataframe df

    # Construção tabela de detalhes do evento
    st.header("Detalhes do Evento")
    try:
        st.table(df_selected[['Evento', 'Descrição', 'Local', 'Dia', 'Início', 'Fim']])
    except KeyError:
        "Selecione um evento para ampliar"

    
