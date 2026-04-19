import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
from fpdf import FPDF 

# --- CONEXÃO E CRIAÇÃO DO BANCO ---
conn = sqlite3.connect('escola_viana_oficial.db', check_same_thread=False)
c = conn.cursor()

def criar_tabelas():
    c.execute('CREATE TABLE IF NOT EXISTS usuarios(nome TEXT, usuario TEXT PRIMARY KEY, senha TEXT, perfil TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS planos(
                 autor TEXT, data TEXT, horario TEXT, serie TEXT, componente TEXT, 
                 tema TEXT, habilidades TEXT, conteudo TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS notas(professor TEXT, aluno TEXT, turma TEXT, nota REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS frequencia(professor TEXT, data TEXT, turma TEXT, aluno TEXT, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS mural(autor TEXT, titulo TEXT, mensagem TEXT, data TEXT, prioridade INTEGER)')
    conn.commit()

criar_tabelas()

# --- FUNÇÕES DE SISTEMA ---
def criar_hash(senha): 
    return hashlib.sha256(senha.encode()).hexdigest()

def verificar_senha(senha, h): 
    return hashlib.sha256(senha.encode()).hexdigest() == h

def gerar_pdf_plano(dados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Escola Municipal Pascoal Possidonio Gomes - Plano de Aula", ln=True, align='C')
    pdf.ln(5)
    
    for chave, valor in dados.items():
        pdf.set_font("Arial", 'B', 11)
        chave_limpa = str(chave).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(0, 8, f"{chave_limpa}:", ln=True)
        
        pdf.set_font("Arial", '', 11)
        texto_limpo = str(valor).replace('º', 'o.').replace('ª', 'a.')
        texto_limpo = texto_limpo.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, texto_limpo)
        pdf.ln(3)
        
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="EduDesk - Pascoal Possidônio", layout="wide", page_icon="🏫")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #0056b3; color: white; border: none; padding: 10px; font-weight: bold;}
    .stButton>button:hover { background-color: #003d82; color: white; }
    div[data-baseweb="select"] > div { background-color: #f8f9fa; }
    </style>
""", unsafe_allow_html=True)

if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.perfil = None
    st.session_state.usuario = None

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    col1, col2 = st.columns([1, 4])
    with col1:
        try: st.image("logo_escola.png", width=120)
        except: st.info("Logo da Escola")
    with col2: 
        st.title("EduDesk - Portal de Acesso")
        st.subheader("Escola Municipal Pascoal Possidônio Gomes")
    
    aba1, aba2 = st.tabs(["🔐 Entrar", "📝 Cadastro de Servidor"])
    
    with aba1:
        u = st.text_input("Usuário", key="login_usuario")
        p = st.text_input("Senha", type="password", key="login_senha")
        if st.button("Acessar Sistema"):
            c.execute('SELECT senha, perfil FROM usuarios WHERE usuario = ?', (u,))
            res = c.fetchone()
            if res and verificar_senha(p, res[0]):
                st.session_state.logado, st.session_state.usuario, st.session_state.perfil = True, u, res[1]
                st.rerun()
            else:
                st.error("Credenciais incorretas.")
                
    with aba2:
        n_nome = st.text_input("Nome Completo", key="cad_nome")
        n_user = st.text_input("Login", key="cad_login")
        n_pw = st.text_input("Senha", type="password", key="cad_senha")
        n_perf = st.radio("Cargo", ["Professor", "Gestor"], key="cad_cargo")
        if st.button("Realizar Cadastro"):
            try:
                c.execute('INSERT INTO usuarios VALUES(?,?,?,?)', (n_nome, n_user, criar_hash(n_pw), n_perf))
                conn.commit()
                st.success("Cadastro realizado! Retorne à aba Entrar.")
            except: 
                st.error("Erro: Este usuário já existe.")

# --- SISTEMA LOGADO ---
else:
    st.sidebar.title(f"Olá, {st.session_state.usuario}")
    st.sidebar.caption(f"Perfil: {st.session_state.perfil}")
    st.sidebar.divider()
    
    turmas_escola = ["6º Ano", "7º Ano", "8º Ano", "9º Ano"]
    horarios_aula = ["1º Horário", "2º Horário", "3º Horário", "4º Horário", "5º Horário"]
    
    if st.session_state.perfil == "Gestor":
        menu = st.sidebar.radio("Menu de Gestão", ["Mural da Escola", "Relatórios Gerais", "Planos de Aula (Arquivo)", "Sair"])
    else:
        menu = st.sidebar.radio("Menu Pedagógico", ["Mural da Escola", "Frequência Digital", "Diário de Notas", "Planejamento Mágico", "Sair"])

    if menu == "Sair":
        st.session_state.logado = False
        if 'pdf_pronto' in st.session_state: del st.session_state['pdf_pronto']
        st.rerun()

    # --- MURAL ---
    elif menu == "Mural da Escola":
        st.header("📌 Mural de Comunicações")
        with st.expander("➕ Colar novo recado"):
            t = st.text_input("Título do Recado")
            m = st.text_area("Mensagem")
            prio = 1 if st.session_state.perfil == "Gestor" and st.checkbox("Marcar como Comunicado Oficial") else 0
            if st.button("Publicar no Mural"):
                data_post = datetime.now().strftime("%d/%m/%Y %H:%M")
                c.execute('INSERT INTO mural VALUES(?,?,?,?,?)', (st.session_state.usuario, t, m, data_post, prio))
                conn.commit()
                st.rerun()
                
        avisos = pd.read_sql("SELECT * FROM mural ORDER BY prioridade DESC, data DESC", conn)
        for _, av in avisos.iterrows():
            if av['prioridade'] == 1:
                st.warning(f"📢 **OFICIAL: {av['titulo']}** ({av['data']})\n\n{av['mensagem']}")
            else:
                st.info(f"**{av['titulo']}** - {av['autor']} ({av['data']})\n\n{av['mensagem']}")

    # --- PLANO DE AULA (CASCATA DE TEMAS E AULA PRONTA) ---
    elif menu == "Planejamento Mágico":
        st.header("✨ Planejador Inteligente de Aulas")
        st.write("Defina a turma e a matéria para ver sugestões de aulas prontas.")
        
        col1, col2 = st.columns(2)
        with col1:
            d = st.date_input("Data da Aula", format="DD/MM/YYYY")
            s = st.selectbox("Série (Turma)", turmas_escola)
        with col2:
            h = st.selectbox("Horário", horarios_aula)
            comp = st.selectbox("Componente Curricular", [
                "Língua Portuguesa", "Computação", "Matemática", "História", 
                "Geografia", "Ciências", "Arte", "Educação Física", "Ensino Religioso", "Língua Inglesa"
            ])
        
        st.divider()

        # ---------------------------------------------------------
        # O "CÉREBRO" DE AULAS PRONTAS (CASCATA)
        # ---------------------------------------------------------
        banco_aulas = {
            "6º Ano": {
                "Língua Portuguesa": {
                    "Liberdade de Expressão vs Discurso de Ódio": {
                        "habs": ["EF69LP01 - Diferenciar liberdade de expressão de discursos de ódio."],
                        "metodologia": "1. Dinâmica inicial: O que é opinar? O que é ofender?\n2. Análise na lousa de postagens fictícias de redes sociais.\n3. Roda de conversa: Os impactos reais das palavras virtuais.\n4. Atividade: Produção coletiva de um cartaz de 'Regras de Convivência Digital'."
                    },
                    "Notícias e Fake News": {
                        "habs": ["EF67LP03 - Comparar informações sobre um mesmo fato em diferentes mídias."],
                        "metodologia": "1. Leitura de duas manchetes diferentes sobre o mesmo fato.\n2. Discussão com a turma sobre a intenção de quem escreveu.\n3. Atividade em pequenos grupos: Jogo rápido para identificar pistas de Fake News no papel."
                    }
                },
                "Computação": {
                    "O Impacto da Tecnologia na Sociedade": {
                        "habs": ["EF06CO01 - Analisar o impacto das tecnologias digitais."],
                        "metodologia": "1. Brainstorm: Como era o mundo antes do celular smartphone?\n2. Criação de linha do tempo no quadro.\n3. Debate mediado sobre os impactos positivos e negativos (ex: lixo eletrônico, distanciamento)."
                    }
                }
            },
            "9º Ano": {
                "Língua Portuguesa": {
                    "Neologismos e Variação Linguística": {
                        "habs": ["EF09LP01 - Analisar a criação de neologismos."],
                        "metodologia": "1. Leitura mediada de fragmentos de Guimarães Rosa ou cordéis maranhenses.\n2. Busca ativa no texto por palavras 'inventadas' ou estritamente regionais.\n3. Debate: Como a língua é viva e se adapta.\n4. Atividade de fixação: Criar um 'minidicionário regional' da sala."
                    },
                    "O Texto Argumentativo": {
                        "habs": ["EF89LP04 - Identificar argumentos e recursos de persuasão."],
                        "metodologia": "1. Leitura compartilhada de um artigo de opinião atual.\n2. Grifar: de azul a Tese (ideia principal) e de vermelho os Argumentos.\n3. Produção textual: Um parágrafo argumentativo sobre a merenda ou rotina escolar."
                    }
                },
                "Computação": {
                    "Pensamento Computacional na Prática": {
                        "habs": ["EF09CO04 - Aplicar o pensamento computacional."],
                        "metodologia": "1. Divisão da turma em pequenos grupos (3 alunos).\n2. Desafio: Criar um algoritmo (passo a passo de instruções) para organizar a fila da escola sem empurra-empurra.\n3. Teste de mesa: Um grupo lê a instrução do outro para ver se faz sentido."
                    }
                }
            }
        }

        # Busca os temas disponíveis para a Série e Componente selecionados
        temas_disponiveis = banco_aulas.get(s, {}).get(comp, {})
        
        habs_sugeridas = []
        metodologia_sugerida = ""
        tema_final = ""

        if temas_disponiveis:
            lista_temas = ["➡️ Selecione um tema sugerido..."] + list(temas_disponiveis.keys())
            tema_escolhido = st.selectbox("💡 Sugestões de Temas Prontos", lista_temas)
            
            if tema_escolhido != "➡️ Selecione um tema sugerido...":
                habs_sugeridas = temas_disponiveis[tema_escolhido]["habs"]
                metodologia_sugerida = temas_disponiveis[tema_escolhido]["metodologia"]
                tema_final = tema_escolhido
                st.success(f"Magia feita! A aula '{tema_escolhido}' foi preenchida abaixo. Você pode editar os campos livremente.")
        else:
            st.info("Ainda não há aulas prontas cadastradas para esta série e disciplina. Sinta-se livre para preencher os campos manualmente.")
            tema_final = st.text_input("Tema da Aula (Opcional)")

        # Dicionário com TODAS as habilidades disponíveis para não dar erro
        todas_habilidades = [
            "EF69LP01 - Diferenciar liberdade de expressão de discursos de ódio.",
            "EF67LP03 - Comparar informações sobre um mesmo fato em diferentes mídias.",
            "EF89LP04 - Identificar argumentos e recursos de persuasão.",
            "EF69LP44 - Inferir a presença de valores sociais e culturais.",
            "EF09LP01 - Analisar a criação de neologismos.",
            "EF06CO01 - Analisar o impacto das tecnologias digitais.",
            "EF07CO02 - Desenvolver algoritmos para resolução de problemas.",
            "EF08CO03 - Compreender o funcionamento estrutural da internet.",
            "EF09CO04 - Aplicar o pensamento computacional.",
            "EF06MA01 - Comparar, ordenar e ler números naturais e racionais.",
            "EF06CI01 - Classificar como homogênea ou heterogênea a mistura de materiais."
        ]
        
        # Garante que as habilidades sugeridas estejam na lista total
        for h in habs_sugeridas:
            if h not in todas_habilidades:
                todas_habilidades.append(h)

        # Campos preenchidos automaticamente (ou manuais)
        hab_sel = st.multiselect("Habilidades (BNCC/DCTMA)", options=todas_habilidades, default=habs_sugeridas)
        txt = st.text_area("Desenvolvimento / Procedimentos Didáticos", value=metodologia_sugerida, height=150)
        
        # Botão Salvar
        if st.button("💾 Salvar Plano e Gerar PDF"):
            if hab_sel and txt:
                habs_texto = "\n".join(hab_sel)
                # Incluí o TEMA no PDF para ficar ainda mais profissional
                dados = {
                    "Professor": st.session_state.usuario, "Data": d.strftime("%d/%m/%Y"), 
                    "Horario": h, "Serie": s, "Componente": comp, "Tema da Aula": tema_final if tema_final else "Livre",
                    "Habilidades": habs_texto, "Procedimentos": txt
                }
                c.execute('INSERT INTO planos VALUES(?,?,?,?,?,?,?,?)', tuple(dados.values()))
                conn.commit()
                st.success("Plano salvo com sucesso! O botão de Download apareceu abaixo.")
                
                st.session_state.pdf_pronto = gerar_pdf_plano(dados)
                st.session_state.pdf_nome = f"Plano_{comp}_{d.strftime('%d-%m-%Y')}.pdf"
            else:
                st.warning("Por favor, preencha as habilidades e o desenvolvimento antes de salvar.")

        # Botão Download
        if 'pdf_pronto' in st.session_state:
            st.download_button(
                label="📥 Baixar Plano Oficial em PDF", 
                data=st.session_state.pdf_pronto, 
                file_name=st.session_state.pdf_nome, 
                mime="application/pdf"
            )

    # --- FREQUÊNCIA ---
    elif menu == "Frequência Digital":
        st.header("📅 Chamada Digital")
        data_chamada = st.date_input("Data da Aula", format="DD/MM/YYYY")
        t_sel = st.selectbox("Turma", turmas_escola)
        aluno = st.text_input("Nome do Aluno")
        status = st.radio("Registro", ["Presente", "Faltou"])
        
        if st.button("Registrar no Diário"):
            if aluno:
                c.execute('INSERT INTO frequencia VALUES(?,?,?,?,?)', (st.session_state.usuario, data_chamada.strftime("%d/%m/%Y"), t_sel, aluno, status))
                conn.commit()
                st.success(f"Registro de {aluno} gravado!")
            else:
                st.error("Informe o nome do aluno.")
                
        st.divider()
        st.subheader(f"Chamada Registrada: {data_chamada.strftime('%d/%m/%Y')} - {t_sel}")
        df_f = pd.read_sql(f"SELECT aluno, status FROM frequencia WHERE data = '{data_chamada.strftime('%d/%m/%Y')}' AND turma = '{t_sel}' AND professor = '{st.session_state.usuario}'", conn)
        st.dataframe(df_f, use_container_width=True)

    # --- NOTAS ---
    elif menu == "Diário de Notas":
        st.header("✍️ Lançamento de Notas")
        with st.container():
            aluno_n = st.text_input("Nome do Aluno")
            turma_n = st.selectbox("Turma", turmas_escola)
            nota_n = st.number_input("Nota", 0.0, 10.0, step=0.5)
            if st.button("Salvar Nota no Sistema"):
                if aluno_n:
                    c.execute('INSERT INTO notas VALUES(?,?,?,?)', (st.session_state.usuario, aluno_n, turma_n, nota_n))
                    conn.commit()
                    st.success("Nota arquivada.")
                else:
                    st.error("Informe o nome do aluno.")
        
        st.divider()
        st.subheader("Relatório de Notas do Professor")
        df_notas = pd.read_sql(f"SELECT aluno, turma, nota FROM notas WHERE professor = '{st.session_state.usuario}'", conn)
        st.dataframe(df_notas, use_container_width=True)

    # --- RELATÓRIOS GERAIS (GESTOR) ---
    elif menu == "Relatórios Gerais":
        st.header("📊 Inteligência Administrativa")
        
        tab1, tab2 = st.tabs(["Desempenho Geral", "Controle de Faltas"])
        with tab1:
            df_notas_geral = pd.read_sql("SELECT * FROM notas", conn)
            if not df_notas_geral.empty:
                st.subheader("Média da Escola por Turma")
                st.bar_chart(df_notas_geral.groupby('turma')['nota'].mean())
                st.dataframe(df_notas_geral, use_container_width=True)
            else:
                st.write("Sem notas no banco de dados.")
                
        with tab2:
            df_freq_geral = pd.read_sql("SELECT * FROM frequencia", conn)
            if not df_freq_geral.empty:
                faltas = df_freq_geral[df_freq_geral['status'] == 'Faltou'].groupby('aluno').size()
                if not faltas.empty:
                    st.warning("Evasão Escolar: Quantidade de Faltas por Aluno")
                    st.bar_chart(faltas)
                else:
                    st.success("Nenhuma falta registrada!")
            else:
                st.write("Sem chamadas registradas no banco.")

    elif menu == "Planos de Aula (Arquivo)":
        st.header("📂 Transparência: Planos Arquivados")
        df_planos_geral = pd.read_sql("SELECT * FROM planos", conn)
        st.dataframe(df_planos_geral, use_container_width=True)
