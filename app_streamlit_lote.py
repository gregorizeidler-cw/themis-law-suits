import streamlit as st
import pandas as pd
import time
import io
from batch_processor import BatchAbsolutionAnalyzer
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Análise de Absolvição em Lote", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Análise de Absolvição em Lote - Themis")

# Sidebar com informações
st.sidebar.markdown("""
### ℹ️ Como usar:
1. **Faça upload** do arquivo CSV ou TXT
2. **Configure** os parâmetros (opcional)
3. **Clique** em "Iniciar Análise"
4. **Aguarde** o processamento
5. **Baixe** os resultados em CSV

### 📁 Formato dos arquivos:
**CSV:**
```
CPF
01130380114
12345678901
```

**TXT:**
```
01130380114
12345678901
```

### 🎯 O que analisamos:
- Se foi **absolvido** em processos criminais
- **Quantidade** de processos como réu
- **Quantidade** de absolvições
- **Detalhes** das absolvições encontradas
""")

# Upload de arquivo
st.header("📁 Upload da Lista de CPFs")

uploaded_file = st.file_uploader(
    "Escolha um arquivo CSV ou TXT",
    type=['csv', 'txt'],
    help="Arquivo deve conter CPFs (CSV com cabeçalho 'CPF' ou TXT com um CPF por linha)"
)

cpfs_to_analyze = []

if uploaded_file is not None:
    try:
        if uploaded_file.type == "text/csv":
            # Processar CSV
            df = pd.read_csv(uploaded_file)
            if 'CPF' in df.columns:
                cpfs_to_analyze = df['CPF'].astype(str).tolist()
            else:
                # Se não tem cabeçalho CPF, usar primeira coluna
                cpfs_to_analyze = df.iloc[:, 0].astype(str).tolist()
        else:
            # Processar TXT
            content = uploaded_file.read().decode('utf-8-sig')
            cpfs_to_analyze = [line.strip() for line in content.split('\n') if line.strip()]
        
        # Limpar CPFs inválidos
        cpfs_to_analyze = [cpf for cpf in cpfs_to_analyze if len(cpf.replace('.', '').replace('-', '')) >= 11]
        
        st.success(f"✅ {len(cpfs_to_analyze)} CPFs carregados com sucesso!")
        
        # Mostrar preview
        if len(cpfs_to_analyze) > 0:
            st.subheader("👀 Preview dos CPFs")
            preview_df = pd.DataFrame({
                'CPF': cpfs_to_analyze[:10]  # Mostrar apenas os primeiros 10
            })
            st.dataframe(preview_df)
            
            if len(cpfs_to_analyze) > 10:
                st.info(f"Mostrando apenas os primeiros 10 CPFs. Total: {len(cpfs_to_analyze)}")
        
    except Exception as e:
        st.error(f"Erro ao processar arquivo: {str(e)}")
        cpfs_to_analyze = []

# Configurações da análise
if cpfs_to_analyze:
    st.header("⚙️ Configurações da Análise")
    
    col1, col2 = st.columns(2)
    
    with col1:
        max_workers = st.slider(
            "Número de threads paralelas", 
            min_value=1, 
            max_value=20, 
            value=10,
            help="Mais threads = mais rápido, mas pode sobrecarregar a API"
        )
    
    with col2:
        delay = st.slider(
            "Delay entre requisições (segundos)", 
            min_value=0.1, 
            max_value=2.0, 
            value=0.1, 
            step=0.1,
            help="Delay maior = mais lento, mas evita rate limiting"
        )
    
    # Estimativa de tempo
    estimated_time = (len(cpfs_to_analyze) / max_workers) * delay
    st.info(f"⏱️ Tempo estimado: {estimated_time:.1f} segundos ({estimated_time/60:.1f} minutos)")

# Botão para iniciar análise
if cpfs_to_analyze and st.button("🚀 Iniciar Análise", type="primary"):
    
    # Verificar limite
    if len(cpfs_to_analyze) > 10000:
        st.error("❌ Limite máximo de 10.000 CPFs por análise. Por favor, reduza a lista.")
    else:
        # Inicializar analisador
        analyzer = BatchAbsolutionAnalyzer(
            max_workers=max_workers,
            delay_between_requests=delay
        )
        
        # Containers para mostrar progresso
        progress_container = st.container()
        results_container = st.container()
        
        with progress_container:
            st.subheader("🔄 Processamento em Andamento")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            stats_cols = st.columns(4)
            
            # Contadores em tempo real
            with stats_cols[0]:
                total_metric = st.metric("Total", len(cpfs_to_analyze))
            with stats_cols[1]:
                processed_metric = st.metric("Processados", 0)
            with stats_cols[2]:
                absolved_metric = st.metric("Absolvidos", 0)
            with stats_cols[3]:
                percentage_metric = st.metric("Progresso", "0%")
        
        # Função de callback para atualizar progresso
        def update_progress(processed, total, result):
            progress = processed / total
            progress_bar.progress(progress)
            status_text.text(f"Processando CPF {processed}/{total}: {result['cpf']}")
            
            # Contar absolvidos até agora
            absolvidos_count = sum(1 for i in range(len(st.session_state.get('current_results', []))) 
                                 if st.session_state.current_results[i].get('foi_absolvido') is True)
            
            # Atualizar métricas
            processed_metric.metric("Processados", processed)
            absolved_metric.metric("Absolvidos", absolvidos_count)
            percentage_metric.metric("Progresso", f"{progress*100:.1f}%")
        
        # Inicializar session state para resultados
        if 'current_results' not in st.session_state:
            st.session_state.current_results = []
        
        # Executar análise
        start_time = time.time()
        
        try:
            results = analyzer.process_batch(cpfs_to_analyze, progress_callback=update_progress)
            st.session_state.current_results = results
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            # Finalizar barra de progresso
            progress_bar.progress(1.0)
            status_text.text(f"✅ Análise concluída em {elapsed_time:.1f} segundos!")
            
        except Exception as e:
            st.error(f"❌ Erro durante a análise: {str(e)}")
            st.session_state.current_results = []

# Mostrar resultados se existirem
if 'current_results' in st.session_state and st.session_state.current_results:
    results = st.session_state.current_results
    
    with st.container():
        st.header("📊 Resultados da Análise")
        
        # Calcular estatísticas
        analyzer = BatchAbsolutionAnalyzer()
        stats = analyzer.get_summary_stats(results)
        
        # Mostrar estatísticas
        st.subheader("📈 Estatísticas Gerais")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Processados", 
                stats['total_processados'],
                help="Quantidade total de CPFs analisados"
            )
        
        with col2:
            st.metric(
                "Absolvidos", 
                stats['total_absolvidos'],
                delta=f"{stats['percentual_absolvidos']:.1f}%",
                delta_color="normal",
                help="CPFs que foram absolvidos em processos criminais"
            )
        
        with col3:
            st.metric(
                "Não Absolvidos", 
                stats['total_nao_absolvidos'],
                delta=f"{stats['percentual_nao_absolvidos']:.1f}%",
                delta_color="inverse",
                help="CPFs que NÃO foram absolvidos"
            )
        
        with col4:
            st.metric(
                "Sem Dados", 
                stats['total_sem_dados'],
                delta=f"{stats['percentual_sem_dados']:.1f}%",
                delta_color="off",
                help="CPFs sem dados disponíveis"
            )
        
        # Gráfico de pizza
        st.subheader("📊 Distribuição dos Resultados")
        
        chart_data = pd.DataFrame({
            'Status': ['Absolvidos', 'Não Absolvidos', 'Sem Dados'],
            'Quantidade': [
                stats['total_absolvidos'],
                stats['total_nao_absolvidos'],
                stats['total_sem_dados']
            ]
        })
        
        st.bar_chart(chart_data.set_index('Status'))
        
        # Tabela de resultados
        st.subheader("📋 Resultados Detalhados")
        
        # Preparar dados para tabela
        table_data = []
        for result in results:
            table_data.append({
                'CPF': result['cpf'],
                'Nome': result['nome'],
                'Foi Absolvido': '✅ Sim' if result['foi_absolvido'] is True else ('❌ Não' if result['foi_absolvido'] is False else '❓ Sem dados'),
                'Total Processos Criminais': result['total_processos_criminais'],
                'Total Absolvições': result['total_absolvicoes'],
                'Status': result['status']
            })
        
        results_df = pd.DataFrame(table_data)
        
        # Filtros
        col1, col2 = st.columns(2)
        
        with col1:
            status_filter = st.selectbox(
                "Filtrar por resultado:",
                options=['Todos', 'Apenas Absolvidos', 'Apenas Não Absolvidos', 'Apenas Sem Dados']
            )
        
        with col2:
            name_filter = st.text_input("Filtrar por nome:", placeholder="Digite parte do nome...")
        
        # Aplicar filtros
        filtered_df = results_df.copy()
        
        if status_filter == 'Apenas Absolvidos':
            filtered_df = filtered_df[filtered_df['Foi Absolvido'] == '✅ Sim']
        elif status_filter == 'Apenas Não Absolvidos':
            filtered_df = filtered_df[filtered_df['Foi Absolvido'] == '❌ Não']
        elif status_filter == 'Apenas Sem Dados':
            filtered_df = filtered_df[filtered_df['Foi Absolvido'] == '❓ Sem dados']
        
        if name_filter:
            filtered_df = filtered_df[filtered_df['Nome'].str.contains(name_filter, case=False, na=False)]
        
        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Download dos resultados
        st.subheader("💾 Download dos Resultados")
        
        # Preparar CSV para download
        csv_data = []
        for result in results:
            csv_data.append({
                'CPF': result['cpf'],
                'Nome': result['nome'],
                'Foi_Absolvido': result['foi_absolvido'],
                'Total_Processos_Criminais': result['total_processos_criminais'],
                'Total_Absolvicoes': result['total_absolvicoes'],
                'Status': result['status']
            })
        
        csv_df = pd.DataFrame(csv_data)
        csv_buffer = io.StringIO()
        csv_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        csv_string = csv_buffer.getvalue()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="📥 Baixar Resultados Completos (CSV)",
                data=csv_string,
                file_name=f"analise_absolvicoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                help="Download com todos os resultados da análise"
            )
        
        with col2:
            # CSV apenas dos absolvidos
            absolved_df = csv_df[csv_df['Foi_Absolvido'] == True]
            if len(absolved_df) > 0:
                csv_buffer_abs = io.StringIO()
                absolved_df.to_csv(csv_buffer_abs, index=False, encoding='utf-8-sig')
                csv_string_abs = csv_buffer_abs.getvalue()
                
                st.download_button(
                    label="📥 Baixar Apenas Absolvidos (CSV)",
                    data=csv_string_abs,
                    file_name=f"apenas_absolvidos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    help="Download apenas dos CPFs que foram absolvidos"
                )
        
        # Detalhes expandidos
        if st.checkbox("🔍 Mostrar detalhes das absolvições"):
            st.subheader("📜 Detalhes das Absolvições")
            
            for result in results:
                if result['foi_absolvido'] and result['detalhes_absolvicoes']:
                    with st.expander(f"🔍 {result['nome']} ({result['cpf']})"):
                        for i, detalhe in enumerate(result['detalhes_absolvicoes'], 1):
                            st.markdown(f"""
                            **Absolvição #{i}:**
                            - **Processo:** {detalhe.get('processo', 'N/A')}
                            - **Tipo:** {detalhe.get('tipo_decisao', 'N/A')}
                            - **Órgão:** {detalhe.get('orgao', 'N/A')}
                            - **Comarca:** {detalhe.get('comarca', 'N/A')}
                            - **Data:** {detalhe.get('data', 'N/A')}
                            
                            **Trecho da decisão:**
                            > {detalhe.get('trecho_decisao', 'N/A')}
                            """)

# Rodapé
st.markdown("---")
st.markdown("""
### 💡 Dicas:
- **Para lotes grandes (>1000 CPFs)**: Use menos threads (5-10) e mais delay (0.2-0.5s)
- **Para análise rápida**: Use mais threads (15-20) e menos delay (0.1s)
- **Em caso de erro**: Tente reduzir o número de threads e aumentar o delay

### ⚠️ Considerações:
- Nem todos os CPFs terão dados disponíveis
- Absolvições podem estar em diferentes formatos nas decisões
- O sistema busca por palavras-chave específicas nas decisões judiciais

**Themis © {} - Análise Jurídica Automatizada**
""".format(datetime.now().year))
