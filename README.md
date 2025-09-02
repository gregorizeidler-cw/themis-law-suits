# 📊 Themis - Análise de Absolvição em Lote

Sistema especializado para análise automatizada de **absolvições em processos criminais** para milhares de CPFs simultaneamente.

## 🎯 O que o Sistema Faz

O Themis analisa se uma pessoa foi **absolvida** em processos criminais, processando:
- ✅ **Milhares de CPFs** simultaneamente
- 🔍 **Consulta automática** na BigData Corp
- ⚖️ **Identificação de absolvições** em decisões judiciais
- 📊 **Relatórios** em CSV com resultados detalhados

---

## 🚀 Duas Versões Disponíveis

### 🏃‍♂️ **Versão Rápida** (Porta 8501)
- **Método**: Análise por palavras-chave (regex)
- **Velocidade**: Muito rápida
- **Custo**: Apenas BigData Corp API
- **Precisão**: Boa para casos simples
- **Limite**: 10.000 CPFs por lote

### 🧠 **Versão Inteligente** (Porta 8502)  
- **Método**: Análise com GPT-4 (OpenAI)
- **Velocidade**: Mais lenta
- **Custo**: BigData Corp + OpenAI
- **Precisão**: Muito alta (análise contextual)
- **Extras**: Justificativa + nível de confiança
- **Limite**: 1.000 CPFs por lote

---

## 📁 Estrutura do Projeto

```
themis/
├── 🏃‍♂️ VERSÃO RÁPIDA
│   ├── batch_processor.py          # Lógica de processamento (regex)
│   └── app_streamlit_lote.py       # Interface Streamlit (porta 8501)
│
├── 🧠 VERSÃO INTELIGENTE  
│   ├── batch_processor_llm.py      # Lógica de processamento (LLM)
│   └── app_streamlit_lote_llm.py   # Interface Streamlit (porta 8502)
│
├── ⚙️ CONFIGURAÇÃO
│   ├── requirements.txt            # Dependências Python
│   ├── env_template.txt            # Template de credenciais
│   └── README.md                   # Esta documentação
│
└── venv/                           # Ambiente virtual Python
```

---

## 🛠️ Instalação e Configuração

### 1. **Preparar Ambiente**
```bash
# Clonar e entrar no projeto
cd themis

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 2. **Configurar Credenciais**
```bash
# Copiar template
cp env_template.txt .env

# Editar .env com suas chaves:
# BIGDATA_TOKEN_ID=sua_chave_aqui
# BIGDATA_TOKEN_HASH=seu_hash_aqui
# OPENAI_API_KEY=sk-sua_chave_openai  # Apenas para versão LLM
```

---

## 🚀 Como Executar

### 🏃‍♂️ **Versão Rápida** (Recomendada para grandes volumes)
```bash
streamlit run app_streamlit_lote.py --server.port 8501
```
**Acesse**: [http://localhost:8501](http://localhost:8501)

### 🧠 **Versão Inteligente** (Recomendada para precisão máxima)
```bash  
streamlit run app_streamlit_lote_llm.py --server.port 8502
```
**Acesse**: [http://localhost:8502](http://localhost:8502)

### 🔥 **Executar Ambas Simultaneamente**
```bash
# Terminal 1 - Versão Rápida
streamlit run app_streamlit_lote.py --server.port 8501 &

# Terminal 2 - Versão Inteligente  
streamlit run app_streamlit_lote_llm.py --server.port 8502 &
```

---

## 📝 Como Usar

### **1. Preparar Lista de CPFs**

**Formato CSV:**
```csv
CPF
01130380114
12345678901
98765432100
```

**Formato TXT:**
```txt
01130380114
12345678901
98765432100
```

### **2. Fazer Upload e Configurar**
- 📁 **Upload** do arquivo CSV/TXT
- ⚙️ **Ajustar parâmetros** (workers, delay)
- 🚀 **Iniciar análise**

### **3. Aguardar Processamento**
- 📊 **Acompanhar progresso** em tempo real
- 📈 **Ver estatísticas** durante processamento

### **4. Baixar Resultados**
- 💾 **Download CSV** com todos os dados
- 📋 **Visualizar tabela** de resultados

---

## 📊 Resultados Gerados

### **Versão Rápida** - Colunas do CSV:
- `cpf`: CPF analisado
- `nome`: Nome da pessoa
- `foi_absolvido`: true/false/null
- `total_processos_criminais`: Quantidade de processos
- `total_absolvicoes`: Quantidade de absolvições
- `detalhes_absolvicoes`: Lista das absolvições
- `status`: Status do processamento

### **Versão Inteligente** - Colunas adicionais:
- `confianca_analise`: Nível de confiança (0-100%)
- `justificativa`: Explicação da decisão da IA
- `detalhes_ia`: Resumo dos processos analisados

---

## ⚡ Performance

### **Versão Rápida**
- 🏃‍♂️ **~10 CPFs/segundo** (depende da API)
- 💰 **Custo**: Apenas BigData Corp
- 🎯 **Ideal para**: Grandes volumes (1.000+ CPFs)

### **Versão Inteligente**
- 🧠 **~2-5 CPFs/segundo** (depende da OpenAI)
- 💰 **Custo**: BigData Corp + OpenAI tokens
- 🎯 **Ideal para**: Análises precisas (até 1.000 CPFs)

---

## 🔑 Credenciais Necessárias

### **BigData Corp** (Obrigatório para ambas)
- `BIGDATA_TOKEN_ID`: Seu token ID
- `BIGDATA_TOKEN_HASH`: Seu token hash

### **OpenAI** (Apenas versão inteligente)
- `OPENAI_API_KEY`: Sua chave da API OpenAI

---

## 🛡️ Segurança

- ✅ **Credenciais** protegidas em arquivo `.env`
- ✅ **`.env` nunca** commitado no Git
- ✅ **Template** disponível para configuração
- ✅ **Dados** processados localmente

---

## 📋 Dependências Principais

```txt
streamlit>=1.28.0          # Interface web
pandas>=2.0.0              # Manipulação de dados
requests>=2.31.0           # Chamadas HTTP
openai>=1.0.0              # IA (apenas versão inteligente)
python-dotenv>=1.0.0       # Variáveis de ambiente
```

---

## 🆘 Solução de Problemas

### **Erro: "command not found: python"**
```bash
# Use python3 em vez de python
python3 -m venv venv
```

### **Erro: "BIGDATA_TOKEN não configurado"**
```bash
# Verifique se o arquivo .env existe e tem as chaves corretas
cat .env
```

### **Erro: "This site can't be reached"**
```bash
# Verifique se o Streamlit está rodando
ps aux | grep streamlit
# Mate processos antigos se necessário
pkill -f streamlit
```

### **Versão LLM muito lenta**
- ✅ **Reduza max_workers** (2-3)
- ✅ **Aumente delay** (0.5s+)  
- ✅ **Use lotes menores** (<500 CPFs)

---

## 🤝 Suporte

Para dúvidas ou problemas:
1. ✅ Verifique este README
2. ✅ Confirme configuração do `.env`
3. ✅ Teste com poucos CPFs primeiro
4. ✅ Verifique logs no terminal

---

**⚖️ Themis - Análise jurídica automatizada com precisão e eficiência**