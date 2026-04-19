import streamlit as st
import pandas as pd
import sqlite3
import hashlib

# --- CONEXÃO ---
conn = sqlite3.connect('escola.db', check_same_thread=False)
c = conn.cursor()

def criar_tabelas()
    # Adicionada a coluna 'perfil' (Professor ou Gestor)
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (nome TEXT, usuario TEXT PRIMARY KEY, senha TEXT, perfil TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS planos(autor TEXT, serie TEXT, habilidade TEXT, conteudo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS notas(professor TEXT, aluno TEXT, turma TEXT, nota REAL)')
    conn.commit()

criar_tabelas()

def criar_hash(senha)
    return hashlib.sha256(senha.encode()).hexdigest()

def verificar_senha(senha, senha_hash)
    return hashlib.sha256(senha.encode()).hexdigest() == senha_hash

# --- INTERFACE ---
st.set_page_config(page_title=EduDesk Pro - Gestão & Docência, layout=wide)

if 'logado' not in st.session_state
    st.session_state.logado = False
    st.session_state.perfil = None

if not st.session_state.logado
    st.title(🔐 EduDesk - Portal de Acesso)
    tab1, tab2 = st.tabs([Login, Cadastrar Novo Usuário])
    
    with tab1
        user = st.text_input(Usuário)
        pw = st.text_input(Senha, type=password)
        if st.button(Entrar)
            c.execute('SELECT senha, perfil FROM usuarios WHERE usuario = ', (user,))
            res = c.fetchone()
            if res and verificar_senha(pw, res[0])
                st.session_state.logado = True
                st.session_state.usuario = user
                st.session_state.perfil = res[1]
                st.rerun()
            else
                st.error(Credenciais inválidas)

    with tab2
        novo_nome = st.text_input(Nome Completo)
        novo_user = st.text_input(Usuário de Acesso)
        nova_pw = st.text_input(Senha, type=password)
        perfil = st.radio(Tipo de Conta, [Professor, Gestor])
        if st.button(Cadastrar)
            try
                c.execute('INSERT INTO usuarios VALUES(,,,)', (novo_nome, novo_user, criar_hash(nova_pw), perfil))
                conn.commit()
                st.success(Conta criada! Agora faça o login.)
            except
                st.error(Este usuário já existe.)

else
    # --- BARRA LATERAL ---
    st.sidebar.title(f👤 {st.session_state.usuario})
    st.sidebar.info(fNível de Acesso {st.session_state.perfil})
    
    if st.session_state.perfil == Gestor
        menu = st.sidebar.radio(Painel de Gestão, [Visão Geral (Notas), Banco de Planos de Aula, Sair])
    else
        menu = st.sidebar.radio(Painel do Professor, [Meu Diário, Criar Plano de Aula, Sair])

    if menu == Sair
        st.session_state.logado = False
        st.rerun()

    # --- LÓGICA DO GESTOR (APENAS LEITURA) ---
    elif menu == Visão Geral (Notas)
        st.header(📈 Relatório Geral de Desempenho (Modo Leitura))
        df_todas_notas = pd.read_sql(SELECT  FROM notas, conn)
        
        if not df_todas_notas.empty
            # Gráfico de média por turma para o gestor
            media_turma = df_todas_notas.groupby('turma')['nota'].mean().reset_index()
            st.bar_chart(data=media_turma, x='turma', y='nota')
            
            st.subheader(Lista Completa de Alunos)
            st.dataframe(df_todas_notas, use_container_width=True)
        else
            st.info(Nenhuma nota lançada no sistema ainda.)

    elif menu == Banco de Planos de Aula
        st.header(📂 Arquivo de Planos de Aula)
        df_planos = pd.read_sql(SELECT  FROM planos, conn)
        st.table(df_planos) # Visualização em tabela simples para o gestor

    # --- LÓGICA DO PROFESSOR (ESCRITA) ---
    elif menu == Meu Diário
        st.header(✍️ Lançamento de Notas)
        # Aqui o professor pode inserir dados
        with st.expander(Lançar Nota)
            aluno = st.text_input(Nome do Aluno)
            turma = st.selectbox(Turma, [601, 701, 801, 901])
            nota = st.number_input(Nota, 0.0, 10.0)
            if st.button(Salvar)
                c.execute('INSERT INTO notas VALUES(,,,)', (st.session_state.usuario, aluno, turma, nota))
                conn.commit()
                st.success(Nota salva!)

        st.subheader(Minhas Notas)
        df_profe = pd.read_sql(fSELECT aluno, turma, nota FROM notas WHERE professor = '{st.session_state.usuario}', conn)
        st.dataframe(df_profe)