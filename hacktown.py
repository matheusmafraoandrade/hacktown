### Requirements
#from datetime import timezone
#from tkinter import FALSE
import requests
from bs4 import BeautifulSoup
import lxml
import xlsxwriter
import openpyxl
import pandas as pd
import numpy as np
import streamlit as st
from pandas.api.types import CategoricalDtype
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode
from io import BytesIO

st.set_page_config(page_title='Programação Hacktown', layout='wide')
st.title('Programação Hacktown')

### Dicionário de dias para indexar busca por abas da planilha
days = {0:'Quinta',1:'Sexta',2:'Sábado',3:'Domingo'}

### Criar tipo "Dias da Semana"
days_order = CategoricalDtype(
    ['Quinta','Sexta','Sábado','Domingo'], 
    ordered=True)

### Função Webscraping
@st.cache(allow_output_mutation=True)
def hacktown(link: str) -> pd.DataFrame:
    """
    Função que coleta os dados dos eventos via web scraping da planilha de programação do Hacktown, dividida por dias do evento.
    Em seguida, itera pelos dias definidos no dicionário 'days' para coletar todos os dados dos eventos correspondentes ao dia e 
    preencher o dataframe 'mydata'.
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

    mydata.fillna("", inplace=True)

    return mydata

df = pd.DataFrame(hacktown(
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vTUAuTwwFq_debnSmBPcUMg3B_9kx76J_BygLDCYkGb9BNG8AvIx27wouDrg6pL3r8Vo_oBFYx7eNp4/pubhtml?gid=0")
    )

### Manipular os horários de início e fim
df['Início'] = df['Horario'].str.split(' ').str[0]
df['Fim'] = df['Horario'].str.split(' ').str[-1]
conditions = [(df['Início'] == df['Fim']), (df['Início'] != df['Fim'])]
choices = ["", df['Fim']]
df['Fim'] = np.select(conditions, choices, default="")
df.drop(columns=['Horario'], axis=1, inplace=True)
df['Início'] = df['Início'].str.replace('^8h','08h', regex=True).replace('^9h','09h', regex=True).replace('','16h')
df['Dia'] = df['Dia'].astype(days_order)

### Componentes da barra lateral: filtro de data, horário e palavra-chave
with st.sidebar:
    # Logo Hacktown
    st.image('https://hacktown.com.br/wp-content/uploads/elementor/thumbs/LOGO-HTW22-pflc15fialujhvsk6ptrdxdngopibx60z8o2o775s0.png',
        width=130)

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
        \nPara limpar o filtro de palavra chave, pressione Enter com o campo de busca vazio.")

    # Contato
    for i in range (0,7):
        st.write("\n")
    st.markdown("### Desenvolvido por Matheus Mafra")

    l_logo,g_logo = st.columns(2)
    l_logo.image("https://cdn-icons-png.flaticon.com/512/174/174857.png",width=50)
    l_logo.markdown("**[Linkedin](https://www.linkedin.com/in/matheus-andrade-122b34180/)**")
    
    g_logo.image("https://cdn-icons-png.flaticon.com/512/25/25231.png",width=50)
    g_logo.markdown("**[GitHub](https://github.com/matheusmafraoandrade)**")

### Componentes da página principal: multiselect, aba 1 e aba 2

# Habilitar seleção múltipla
mult_select = st.checkbox("Habilitar Seleção Múltipla", 
                            help="Clique para habilitar seleção de múltiplos eventos ao mesmo tempo.")
if mult_select:
    ms = 'multiple'
else:
    ms = 'single'

# Dividir em abas
tab1, tab2 = st.tabs(["Programação completa", "Minha programação"])
with tab1:
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

    # Configurações tabela Ag Grid
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_column('Evento', min_column_width=8, headerCheckboxSelection = True)
    gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=10) #Add pagination
    gb.configure_side_bar() #Add a sidebar
    gb.configure_selection(ms, use_checkbox=True, groupSelectsChildren="Group checkbox select children") #Enable multi-row selection
    gridOptions = gb.build()

    # Construção tabela Ag Grid
    grid_response = AgGrid(
        df,
        gridOptions=gridOptions,
        data_return_mode='AS_INPUT',
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        #update_mode='MODEL_CHANGED', 
        fit_columns_on_grid_load=True,
        enable_enterprise_modules=True,
        reload_data=False,
        width='100%'
        #height=700, 
        #theme='ALPINE', #Add theme color to the table
    )

    # Filtro de linhas selecionadas
    data = grid_response['data']
    selected = grid_response['selected_rows']
    df_selected = pd.DataFrame(selected) #Pass the selected rows to a new dataframe

    # Botões de adicionar e remover evento 
    add, remove = st.columns(2)
    adicionar = add.button("Adicionar evento(s) à minha programação")
    remover = remove.button("Remover evento(s) da minha programação")

    # Construção tabela de detalhes do evento
    st.header("Detalhes do Evento")
    try:
        st.table(df_selected[['Evento', 'Descrição', 'Local', 'Dia', 'Início', 'Fim']])
    except KeyError:
        "Selecione um evento para ampliar"

with tab2:
    # Minha Programação
    st.header("Minha Programação")

    # Inicializar minha programação
    if 'minha_prog' not in st.session_state:
        st.session_state.minha_prog = pd.DataFrame(columns = df.columns)

    # Upload da planilha
    with st.expander("Importar programação"):
        with st.form("Importar", clear_on_submit=True):
            uploaded_file = st.file_uploader('Se já tiver uma programação em Excel, clique em "Browse Files" ou arraste o arquivo para cá para continuar montando.')
            submitted = st.form_submit_button("Importar")
            if submitted and uploaded_file is not None:
                minha_prog = pd.read_excel(uploaded_file)
                st.session_state.minha_prog = pd.concat([st.session_state.minha_prog, minha_prog])
                del minha_prog

    # Instrução download
    #st.write(
    #    'Clique com o botão direito em qualquer evento e, em seguida, clique em "Export" para baixar sua programação em CSV ou Excel.')                
                
    # Adicionar e remover eventos
    if adicionar:
        st.session_state.minha_prog = pd.concat([st.session_state.minha_prog, df_selected])
        # Colocar os dias da semana na ordem
        (st.session_state.minha_prog)['Dia'] = (st.session_state.minha_prog)['Dia'].astype(days_order)

    if remover:
        try:
            for index,row in df_selected[['Evento']].iterrows():
                st.session_state.minha_prog = st.session_state.minha_prog[st.session_state.minha_prog['Evento'] != row['Evento']]
        except KeyError:
            st.write("Nenhum evento selecionado")

    # Configurações tabela Ag Grid
    gb = GridOptionsBuilder.from_dataframe(
        (st.session_state.minha_prog)[
            ['Evento', 'Descrição', 'Local', 'Tipo', 'Dia', 'Início', 'Fim'] # Remover coluna dict que impede remover duplicatas
            ].drop_duplicates().sort_values(by=['Dia', 'Início']) # Remover duplicatas e ordenar por dia e horário
        )
    gb.configure_column('Evento', min_column_width=8, headerCheckboxSelection = True)
    gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=10) #Add pagination
    gb.configure_side_bar() #Add a sidebar
    gb.configure_selection(ms, use_checkbox=True, groupSelectsChildren="Group checkbox select children", suppressRowDeselection=True) #Enable multi-row selection
    gridOptions = gb.build()

    # Construção tabela Ag Grid
    grid_response_minha_prog = AgGrid(
        (st.session_state.minha_prog)[
            ['Evento', 'Descrição', 'Local', 'Tipo', 'Dia', 'Início', 'Fim'] # Remover coluna dict que impede remover duplicatas
            ].drop_duplicates().sort_values(by=['Dia', 'Início']), # Remover duplicatas e ordenar por dia e horário
        gridOptions=gridOptions,
        data_return_mode='AS_INPUT',
        update_mode=GridUpdateMode.MODEL_CHANGED,
        fit_columns_on_grid_load=True,
        enable_enterprise_modules=True,
        reload_data=False,
        width='100%'
    )

    # Filtro de linhas selecionadas
    data_minha_prog = grid_response_minha_prog['data']
    selected_minha_prog = grid_response_minha_prog['selected_rows'] 
    df_selected_minha_prog = pd.DataFrame(selected_minha_prog) #Pass the selected rows to a new dataframe

    # Botões de remover evento e atualizar (botão vazio)
    remove_selected, update, download = st.columns(3)
    remover_selecao = remove_selected.button("Remover evento(s) selecionado(s)")
    atualizar = update.button("Atualizar programação", help="Clique para atualizar a tabela após remover eventos.")

    if remover_selecao:
        try:
            for index,row in df_selected_minha_prog[['Evento']].iterrows():
                st.session_state.minha_prog = st.session_state.minha_prog[st.session_state.minha_prog['Evento'] != row['Evento']]
                df_selected_minha_prog = df_selected_minha_prog[df_selected_minha_prog['Evento'] != row['Evento']]
        except KeyError:
            st.write("Nenhum evento selecionado")

    # Botão de download da planilha
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        ((st.session_state.minha_prog)[
            ['Evento', 'Descrição', 'Local', 'Tipo', 'Dia', 'Início', 'Fim']
            ].drop_duplicates().sort_values(by=['Dia', 'Início'])
        ).to_excel(writer, sheet_name='Minha Programação')
        writer.save()

    download.download_button(
        label="Baixar programação",
        data=buffer,
        file_name="minha_programacao.xlsx",
        mime="application/vnd.ms-excel")

    # Construção tabela de detalhes do evento
    st.header("Detalhes do Evento")
    try:
        st.table(df_selected_minha_prog[['Evento', 'Descrição', 'Local', 'Dia', 'Início', 'Fim']])
    except KeyError:
        "Selecione um evento para ampliar"