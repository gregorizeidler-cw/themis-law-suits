import streamlit as st
import pandas as pd
import time
import io
from batch_processor_llm import BatchAbsolutionAnalyzerLLM
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Análise Inteligente de Absolvição - LLM", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🧠 Análise Inteligente de Absolvição em Lote - Themis AI")

# Sidebar com informações
st.sidebar.markdown("""
### ℹ️ Como usar:
1. **Configure** sua chave OpenAI no .env
2. **Faça upload** do arquivo CSV ou TXT
3. **Configure** os parâmetros (opcional)
4. **Clique** em "🚀 Iniciar Análise IA"
5. **Aguarde** o processamento (mais lento)
6. **Baixe** os resultados detalhados

### 🧠 Diferencial da IA:
- **Análise contextual** das decisões
- **Justificativa detalhada** por CPF
- **Nível de confiança** da análise
- **Interpretação jurídica** especializada

### 📁 Formato dos arquivos:
**CSV:**
```
CPF
01130380114
12345678901
```

### 🎯 O que a IA analisa:
- **Contexto completo** das decisões
- **Identificação precisa** de absolvições
- **Análise semântica** do texto jurídico
- **Confiança** na conclusão (0-100%)
""")

# Aviso sobre OpenAI
st.info("🤖 **Esta versão usa Inteligência Artificial (GPT-4)** para análise contextual. É mais precisa, mas mais lenta e consome tokens OpenAI.")

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
            st.dataframe(preview_df, width='stretch')
            
            if len(cpfs_to_analyze) > 10:
                st.info(f"Mostrando apenas os primeiros 10 CPFs. Total: {len(cpfs_to_analyze)}")
        
    except Exception as e:
        st.error(f"Erro ao processar arquivo: {str(e)}")
        cpfs_to_analyze = []

# Configurações da análise IA
if cpfs_to_analyze:
    st.header("🧠 Configurações da Análise IA")
    
    col1, col2 = st.columns(2)
    
    with col1:
        max_workers = st.slider(
            "Threads paralelas (IA)", 
            min_value=1, 
            max_value=8, 
            value=3,
            help="Menos threads para IA evita sobrecarga. Recomendado: 2-5"
        )
    
    with col2:
        delay = st.slider(
            "Delay entre requisições (segundos)", 
            min_value=0.2, 
            max_value=3.0, 
            value=0.5, 
            step=0.1,
            help="IA precisa de mais delay para processar contexto"
        )
    
    # Estimativa de tempo (mais conservadora para IA)
    estimated_time = (len(cpfs_to_analyze) / max_workers) * (delay + 2.0)  # +2s para processamento IA
    st.warning(f"⏱️ Tempo estimado: {estimated_time:.1f} segundos ({estimated_time/60:.1f} minutos)")
    st.info("🧠 A análise IA é mais lenta mas muito mais precisa que regex simples!")
    
    # Aviso sobre custos
    cost_estimate = len(cpfs_to_analyze) * 0.01  # Estimativa rough de $0.01 por CPF
    st.warning(f"💰 Custo estimado OpenAI: ~${cost_estimate:.2f} USD (aproximadamente)")

# Verificar se OpenAI está configurado
import os
from dotenv import load_dotenv
load_dotenv()
openai_key = os.getenv('OPENAI_API_KEY')

if not openai_key:
    st.error("❌ **OPENAI_API_KEY não configurada!**")
    st.code("Configure no arquivo .env:\nOPENAI_API_KEY=sk-proj-sua-chave-aqui")
    st.stop()
else:
    st.success("✅ OpenAI API Key configurada")

# Botão para iniciar análise IA
if cpfs_to_analyze and st.button("🧠 Iniciar Análise IA", type="primary"):
    
    # Verificar limite
    if len(cpfs_to_analyze) > 1000:  # Limite menor para IA
        st.error("❌ Limite máximo de 1.000 CPFs para análise IA. Por favor, reduza a lista.")
        st.info("💡 Para lotes maiores, use a versão rápida (sem IA)")
    else:
        # Inicializar analisador IA
        try:
            analyzer = BatchAbsolutionAnalyzerLLM(
                max_workers=max_workers,
                delay_between_requests=delay
            )
            
            # Containers para mostrar progresso
            progress_container = st.container()
            results_container = st.container()
            
            with progress_container:
                st.subheader("🧠 Análise IA em Andamento")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                stats_cols = st.columns(4)
                
                # Contadores em tempo real
                with stats_cols[0]:
                    total_metric = st.metric("Total", len(cpfs_to_analyze))
                with stats_cols[1]:
                    processed_metric = st.metric("Processados", 0)
                with stats_cols[2]:
                    absolved_metric = st.metric("Absolvidos (IA)", 0)
                with stats_cols[3]:
                    confidence_metric = st.metric("Confiança Média", "0%")
            
            # Função de callback para atualizar progresso
            def update_progress(processed, total, result):
                progress = processed / total
                progress_bar.progress(progress)
                status_text.text(f"🤖 Analisando com IA: {processed}/{total} - {result['cpf']}")
                
                # Contar absolvidos e calcular confiança média
                current_results = st.session_state.get('current_results_llm', [])
                if result not in current_results:  # Evitar duplicatas
                    current_results.append(result)
                    st.session_state.current_results_llm = current_results
                
                absolvidos_count = sum(1 for r in current_results if r.get('foi_absolvido') is True)
                confidences = [r.get('confianca_analise', 0) for r in current_results if r.get('confianca_analise')]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                
                # Atualizar métricas
                processed_metric.metric("Processados", processed)
                absolved_metric.metric("Absolvidos (IA)", absolvidos_count)
                confidence_metric.metric("Confiança Média", f"{avg_confidence:.1f}%")
            
            # Inicializar session state para resultados IA
            if 'current_results_llm' not in st.session_state:
                st.session_state.current_results_llm = []
            
            # Executar análise IA
            start_time = time.time()
            
            results = analyzer.process_batch(cpfs_to_analyze, progress_callback=update_progress)
            st.session_state.current_results_llm = results
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            # Finalizar barra de progresso
            progress_bar.progress(1.0)
            status_text.text(f"🧠✅ Análise IA concluída em {elapsed_time:.1f} segundos!")
            
        except Exception as e:
            st.error(f"❌ Erro durante a análise IA: {str(e)}")
            st.session_state.current_results_llm = []

# Mostrar resultados IA se existirem
if 'current_results_llm' in st.session_state and st.session_state.current_results_llm:
    results = st.session_state.current_results_llm
    
    with st.container():
        st.header("🧠 Resultados da Análise IA")
        
        # Calcular estatísticas IA
        analyzer = BatchAbsolutionAnalyzerLLM()
        stats = analyzer.get_summary_stats(results)
        
        # Mostrar estatísticas IA
        st.subheader("📊 Estatísticas da Inteligência Artificial")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "Total Processados", 
                stats['total_processados'],
                help="Quantidade total de CPFs analisados pela IA"
            )
        
        with col2:
            st.metric(
                "Absolvidos (IA)", 
                stats['total_absolvidos'],
                delta=f"{stats['percentual_absolvidos']:.1f}%",
                delta_color="normal",
                help="CPFs identificados pela IA como absolvidos"
            )
        
        with col3:
            st.metric(
                "Confiança Média", 
                f"{stats['confianca_media_ia']:.1f}%",
                help="Nível médio de confiança das análises da IA"
            )
        
        with col4:
            st.metric(
                "Alta Confiança", 
                stats['analises_com_alta_confianca'],
                help="Análises com confiança ≥ 80%"
            )
        
        with col5:
            st.metric(
                "Baixa Confiança", 
                stats['analises_com_baixa_confianca'],
                delta_color="inverse",
                help="Análises com confiança < 50%"
            )
        
        # Gráfico de distribuição
        st.subheader("📊 Distribuição dos Resultados IA")
        
        chart_data = pd.DataFrame({
            'Status': ['Absolvidos', 'Não Absolvidos', 'Sem Dados'],
            'Quantidade': [
                stats['total_absolvidos'],
                stats['total_nao_absolvidos'], 
                stats['total_sem_dados']
            ]
        })
        
        st.bar_chart(chart_data.set_index('Status'))
        
        # Tabela de resultados IA
        st.subheader("📋 Resultados Detalhados da IA")
        
        # Preparar dados para tabela
        table_data = []
        for result in results:
            foi_absolvido = result['foi_absolvido']
            if foi_absolvido is True:
                status_icon = '✅ Sim'
                status_color = 'normal'
            elif foi_absolvido is False:
                status_icon = '❌ Não'
                status_color = 'inverse'
            else:
                status_icon = '❓ Sem dados'
                status_color = 'off'
                
            table_data.append({
                'CPF': result['cpf'],
                'Nome': result['nome'],
                'Foi Absolvido': status_icon,
                'Confiança IA': f"{result.get('confianca_analise', 0)}%",
                'Processos Criminais': result['total_processos_criminais'],
                'Status': result['status']
            })
        
        results_df = pd.DataFrame(table_data)
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.selectbox(
                "Filtrar por resultado:",
                options=['Todos', 'Apenas Absolvidos', 'Apenas Não Absolvidos', 'Apenas Sem Dados']
            )
        
        with col2:
            confidence_filter = st.selectbox(
                "Filtrar por confiança:",
                options=['Todas', 'Alta Confiança (≥80%)', 'Média Confiança (50-79%)', 'Baixa Confiança (<50%)']
            )
        
        with col3:
            name_filter = st.text_input("Filtrar por nome:", placeholder="Digite parte do nome...")
        
        # Aplicar filtros
        filtered_df = results_df.copy()
        filtered_results = results.copy()
        
        if status_filter == 'Apenas Absolvidos':
            filtered_df = filtered_df[filtered_df['Foi Absolvido'] == '✅ Sim']
            filtered_results = [r for r in results if r['foi_absolvido'] is True]
        elif status_filter == 'Apenas Não Absolvidos':
            filtered_df = filtered_df[filtered_df['Foi Absolvido'] == '❌ Não']
            filtered_results = [r for r in results if r['foi_absolvido'] is False]
        elif status_filter == 'Apenas Sem Dados':
            filtered_df = filtered_df[filtered_df['Foi Absolvido'] == '❓ Sem dados']
            filtered_results = [r for r in results if r['foi_absolvido'] is None]
        
        if confidence_filter == 'Alta Confiança (≥80%)':
            filtered_results = [r for r in filtered_results if r.get('confianca_analise', 0) >= 80]
        elif confidence_filter == 'Média Confiança (50-79%)':
            filtered_results = [r for r in filtered_results if 50 <= r.get('confianca_analise', 0) < 80]
        elif confidence_filter == 'Baixa Confiança (<50%)':
            filtered_results = [r for r in filtered_results if r.get('confianca_analise', 0) < 50]
        
        if name_filter:
            filtered_results = [r for r in filtered_results if name_filter.lower() in r['nome'].lower()]
        
        # Reconstruir DataFrame filtrado
        if confidence_filter != 'Todas' or name_filter:
            filtered_table_data = []
            for result in filtered_results:
                foi_absolvido = result['foi_absolvido']
                if foi_absolvido is True:
                    status_icon = '✅ Sim'
                elif foi_absolvido is False:
                    status_icon = '❌ Não'
                else:
                    status_icon = '❓ Sem dados'
                    
                filtered_table_data.append({
                    'CPF': result['cpf'],
                    'Nome': result['nome'],
                    'Foi Absolvido': status_icon,
                    'Confiança IA': f"{result.get('confianca_analise', 0)}%",
                    'Processos Criminais': result['total_processos_criminais'],
                    'Status': result['status']
                })
            filtered_df = pd.DataFrame(filtered_table_data)
        
        st.dataframe(filtered_df, width='stretch', hide_index=True)
        
        # Análises detalhadas da IA
        if st.checkbox("🧠 Mostrar Justificativas da IA"):
            st.subheader("🤖 Análises Detalhadas da Inteligência Artificial")
            
            for result in filtered_results[:20]:  # Limitar a 20 para performance
                confianca = result.get('confianca_analise', 0)
                cor_confianca = "🟢" if confianca >= 80 else "🟡" if confianca >= 50 else "🔴"
                
                with st.expander(f"{cor_confianca} {result['nome']} ({result['cpf']}) - Confiança: {confianca}%"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**🎯 Resultado:** {result['foi_absolvido']}")
                        st.markdown(f"**📊 Confiança:** {confianca}%")
                        st.markdown(f"**⚖️ Processos:** {result['total_processos_criminais']}")
                    
                    with col2:
                        st.markdown("**🧠 Justificativa da IA:**")
                        st.write(result.get('justificativa', 'Sem justificativa'))
                    
                    st.markdown("**🔍 Detalhes da Análise:**")
                    st.info(result.get('detalhes_ia', 'Sem detalhes'))
            
            if len(filtered_results) > 20:
                st.info(f"Mostrando apenas os primeiros 20 resultados. Total filtrado: {len(filtered_results)}")
        
        # Download dos resultados IA
        st.subheader("💾 Download dos Resultados IA")
        
        # Preparar CSV para download com dados da IA
        csv_data = []
        for result in results:
            csv_data.append({
                'CPF': result['cpf'],
                'Nome': result['nome'],
                'Foi_Absolvido': result['foi_absolvido'],
                'Confianca_IA': result.get('confianca_analise', 0),
                'Justificativa_IA': result.get('justificativa', ''),
                'Detalhes_IA': result.get('detalhes_ia', ''),
                'Total_Processos_Criminais': result['total_processos_criminais'],
                'Status': result['status']
            })
        
        csv_df = pd.DataFrame(csv_data)
        csv_buffer = io.StringIO()
        csv_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        csv_string = csv_buffer.getvalue()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="🧠 Baixar Resultados IA Completos (CSV)",
                data=csv_string,
                file_name=f"analise_absolvicoes_ia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                help="Download com análises completas da IA"
            )
        
        with col2:
            # CSV apenas dos absolvidos com alta confiança
            high_conf_absolved = csv_df[(csv_df['Foi_Absolvido'] == True) & (csv_df['Confianca_IA'] >= 80)]
            if len(high_conf_absolved) > 0:
                csv_buffer_hc = io.StringIO()
                high_conf_absolved.to_csv(csv_buffer_hc, index=False, encoding='utf-8-sig')
                csv_string_hc = csv_buffer_hc.getvalue()
                
                st.download_button(
                    label="⭐ Baixar Alta Confiança (CSV)",
                    data=csv_string_hc,
                    file_name=f"absolvidos_alta_confianca_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    help="Download apenas dos absolvidos com confiança ≥ 80%"
                )

# Rodapé
st.markdown("---")
st.markdown(f"""
### 💡 Dicas para Análise IA:
- **Para lotes grandes**: Use 2-3 threads e delay de 0.5s
- **Para análise rápida**: Use a versão sem IA (regex)
- **Confiança baixa**: Revisar manualmente os casos
- **Alta confiança**: Resultados mais confiáveis

### 🧠 Sobre a IA:
- Usa **GPT-4o-mini** para análise contextual
- **Interpreta** o contexto jurídico completo
- **Justifica** cada decisão tomada
- **Calcula confiança** baseada na clareza dos dados

**Themis AI © {datetime.now().year} - Análise Jurídica Inteligente**
""")
