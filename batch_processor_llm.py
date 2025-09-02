# 📦 #### Batch Processor com LLM - Análise Inteligente de Absolvição em Lote
import os
import re
import json
import time
import threading
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import requests
import openai
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# 🔐 #### Credenciais
bigdata_token_id = os.getenv('BIGDATA_TOKEN_ID')
bigdata_token_hash = os.getenv('BIGDATA_TOKEN_HASH')
openai_api_key = os.getenv('OPENAI_API_KEY')

class BatchAbsolutionAnalyzerLLM:
    """Analisador de absolvições em lote com IA para múltiplos CPFs"""
    
    def __init__(self, max_workers: int = 5, delay_between_requests: float = 0.3):
        self.max_workers = max_workers  # Menos workers para não sobrecarregar a OpenAI
        self.delay_between_requests = delay_between_requests
        
        # Verificar credenciais BigData
        if not bigdata_token_id or not bigdata_token_hash:
            raise ValueError("Credenciais BigData Corp não configuradas no arquivo .env")
        
        # Verificar credenciais OpenAI
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY não configurada no arquivo .env")
        
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        print("✅ LLM (OpenAI GPT-4) inicializada com sucesso!")
    
    def fetch_single_cpf_data(self, cpf: str) -> Dict:
        """Buscar dados de um único CPF focando em processos criminais"""
        try:
            cpf_sanitizado = re.sub(r'\D', '', cpf)
            if len(cpf_sanitizado) != 11:
                return {"cpf": cpf, "error": "CPF inválido"}
            
            # Adicionar delay para evitar rate limiting
            time.sleep(self.delay_between_requests)
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "AccessToken": bigdata_token_hash,
                "TokenId": bigdata_token_id
            }
            
            payload = {
                "q": f"doc{{{cpf_sanitizado}}}",
                "Datasets": """basic_data,
                               processes.filter(partypolarity = PASSIVE, courttype = CRIMINAL),
                               kyc.filter(standardized_type, standardized_sanction_type, type, sanctions_source = Conselho Nacional de Justiça)"""
            }
            
            response = requests.post(
                "https://plataforma.bigdatacorp.com.br/pessoas",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"Erro ao processar CPF {cpf}: {str(e)}")
            return {"cpf": cpf, "error": str(e)}
    
    def analyze_with_llm(self, texto_decisoes: str, dados_pessoa: Dict) -> Dict:
        """Analisar decisões com IA (GPT-4) para determinar absolvição"""
        try:
            if not texto_decisoes.strip():
                return {
                    "foi_absolvido": None,
                    "confianca_analise": 0,
                    "justificativa": "Nenhuma decisão disponível para análise",
                    "detalhes_ia": "Sem dados suficientes"
                }
            
            prompt = f"""
Você é um especialista jurídico. Analise as decisões judiciais abaixo e determine se a pessoa foi ABSOLVIDA em processos criminais.

DADOS DA PESSOA:
Nome: {dados_pessoa.get('nome', 'Não informado')}
CPF: {dados_pessoa.get('cpf', 'Não informado')}

DECISÕES JUDICIAIS:
{texto_decisoes}

INSTRUÇÃO ESPECÍFICA:
1. Determine se houve ABSOLVIÇÃO em algum processo criminal
2. Considere: absolvições, improcedências, arquivamentos, extinções
3. Ignore processos onde a pessoa não seja réu/investigado
4. Seja preciso: só retorne True se houver absolvição clara

RESPONDA APENAS EM JSON:
{{
  "foi_absolvido": true/false/null,
  "confianca_analise": 0-100,
  "justificativa": "Explicação clara da análise",
  "detalhes_ia": "Resumo dos processos relevantes"
}}
"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Você é um analista jurídico especializado em análise de absolvições. Responda sempre em JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            resultado_ia = json.loads(response.choices[0].message.content)
            return resultado_ia
            
        except Exception as e:
            return {
                "foi_absolvido": None,
                "confianca_analise": 0,
                "justificativa": f"Erro na análise IA: {str(e)}",
                "detalhes_ia": "Falha no processamento"
            }
    
    def analyze_absolution_with_llm(self, bdc_data: Dict, cpf: str) -> Dict:
        """Analisar absolvição usando IA"""
        try:
            if "Result" not in bdc_data or not bdc_data["Result"]:
                return {
                    "cpf": cpf,
                    "nome": "Não encontrado",
                    "foi_absolvido": None,
                    "confianca_analise": 0,
                    "justificativa": "Dados não encontrados na base",
                    "detalhes_ia": "CPF não localizado",
                    "total_processos_criminais": 0,
                    "status": "dados_nao_encontrados"
                }
            
            pessoa = bdc_data["Result"][0]
            basic = pessoa.get("BasicData", {})
            nome = basic.get("Name", "Nome não informado")
            
            processos = pessoa.get("Processes", {})
            lawsuits = processos.get("Lawsuits", [])
            
            # Filtrar apenas processos criminais onde a pessoa é ré
            processos_criminais = []
            texto_completo_decisoes = []
            
            for proc in lawsuits:
                if proc.get("CourtType") == "CRIMINAL":
                    # Verificar se é réu
                    partes = proc.get("Parties", [])
                    is_reu = False
                    for parte in partes:
                        papel = parte.get("Type", "").upper()
                        nome_parte = parte.get("Name", "").strip().upper()
                        espec = parte.get("PartyDetails", {}).get("SpecificType", "").upper()
                        
                        if (papel == "DEFENDANT" or papel == "RÉU" or espec == "RÉU") and \
                           nome.strip().upper() in nome_parte:
                            is_reu = True
                            break
                    
                    if is_reu:
                        processos_criminais.append(proc)
                        
                        # Coletar dados do processo para IA
                        numero_processo = proc.get("CaseNumber") or proc.get("Number", "")
                        tribunal = proc.get("CourtName", "")
                        
                        # Coletar textos relevantes
                        textos_processo = []
                        
                        # Conteúdo do processo
                        if proc.get("Content"):
                            textos_processo.append(f"Conteúdo: {proc.get('Content')}")
                        
                        # Decisão principal
                        if proc.get("Decision"):
                            textos_processo.append(f"Decisão: {proc.get('Decision')}")
                        
                        # Descrição
                        if proc.get("Description"):
                            textos_processo.append(f"Descrição: {proc.get('Description')}")
                        
                        # Decisões específicas
                        decisoes = proc.get("Decisions", [])
                        for i, decisao in enumerate(decisoes):
                            conteudo_decisao = decisao.get("DecisionContent", "")
                            data_decisao = decisao.get("DecisionDate", "")
                            if conteudo_decisao:
                                textos_processo.append(f"Decisão {i+1} ({data_decisao}): {conteudo_decisao}")
                        
                        # Consolidar texto do processo
                        if textos_processo:
                            texto_processo_completo = f"""
PROCESSO {numero_processo} - {tribunal}:
{chr(10).join(textos_processo)}
---
"""
                            texto_completo_decisoes.append(texto_processo_completo)
            
            total_processos = len(processos_criminais)
            
            # Analisar com IA
            texto_para_ia = "\n".join(texto_completo_decisoes)
            dados_pessoa = {"nome": nome, "cpf": cpf}
            
            resultado_ia = self.analyze_with_llm(texto_para_ia, dados_pessoa)
            
            return {
                "cpf": cpf,
                "nome": nome,
                "foi_absolvido": resultado_ia.get("foi_absolvido"),
                "confianca_analise": resultado_ia.get("confianca_analise", 0),
                "justificativa": resultado_ia.get("justificativa", ""),
                "detalhes_ia": resultado_ia.get("detalhes_ia", ""),
                "total_processos_criminais": total_processos,
                "status": "sucesso"
            }
            
        except Exception as e:
            return {
                "cpf": cpf,
                "nome": "Erro no processamento",
                "foi_absolvido": None,
                "confianca_analise": 0,
                "justificativa": f"Erro durante processamento: {str(e)}",
                "detalhes_ia": "Falha na análise",
                "total_processos_criminais": 0,
                "status": f"erro: {str(e)}"
            }
    
    def process_batch(self, cpfs: List[str], progress_callback=None) -> List[Dict]:
        """Processar lista de CPFs em lote com análise IA"""
        results = []
        total = len(cpfs)
        
        print(f"🧠 Iniciando processamento INTELIGENTE em lote de {total} CPFs...")
        print("⚡ Usando GPT-4 para análise contextual das decisões")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submeter todas as tarefas
            future_to_cpf = {executor.submit(self.fetch_single_cpf_data, cpf): cpf for cpf in cpfs}
            
            for i, future in enumerate(as_completed(future_to_cpf), 1):
                cpf = future_to_cpf[future]
                try:
                    bdc_data = future.result()
                    
                    # Analisar com IA
                    if "error" in bdc_data:
                        result = {
                            "cpf": cpf,
                            "nome": "Erro na consulta",
                            "foi_absolvido": None,
                            "confianca_analise": 0,
                            "justificativa": f"Erro na API: {bdc_data['error']}",
                            "detalhes_ia": "Falha na consulta de dados",
                            "total_processos_criminais": 0,
                            "status": f"erro_api: {bdc_data['error']}"
                        }
                    else:
                        result = self.analyze_absolution_with_llm(bdc_data, cpf)
                    
                    results.append(result)
                    
                    # Callback de progresso
                    if progress_callback:
                        progress_callback(i, total, result)
                    
                    # Log de progresso
                    if i % 5 == 0 or i == total:
                        print(f"🤖 Processados com IA: {i}/{total} CPFs ({i/total*100:.1f}%)")
                
                except Exception as exc:
                    print(f'CPF {cpf} gerou exceção: {exc}')
                    results.append({
                        "cpf": cpf,
                        "nome": "Erro na consulta",
                        "foi_absolvido": None,
                        "confianca_analise": 0,
                        "justificativa": f"Exceção durante processamento: {str(exc)}",
                        "detalhes_ia": "Falha no processamento",
                        "total_processos_criminais": 0,
                        "status": f"excecao: {str(exc)}"
                    })
        
        return results
    
    def export_to_csv(self, results: List[Dict], filename: str = "analise_absolvicoes_llm.csv"):
        """Exportar resultados para CSV com dados da IA"""
        # Dados para CSV com colunas extras da IA
        csv_data = []
        for result in results:
            csv_data.append({
                "CPF": result["cpf"],
                "Nome": result["nome"],
                "Foi_Absolvido": result["foi_absolvido"],
                "Confianca_Analise": result.get("confianca_analise", 0),
                "Justificativa_IA": result.get("justificativa", ""),
                "Detalhes_IA": result.get("detalhes_ia", ""),
                "Total_Processos_Criminais": result["total_processos_criminais"],
                "Status": result["status"]
            })
        
        df = pd.DataFrame(csv_data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"Resultados da análise IA exportados para: {filename}")
        return filename
    
    def get_summary_stats(self, results: List[Dict]) -> Dict:
        """Obter estatísticas resumidas dos resultados com dados da IA"""
        total = len(results)
        absolvidos = sum(1 for r in results if r["foi_absolvido"] is True)
        nao_absolvidos = sum(1 for r in results if r["foi_absolvido"] is False)
        sem_dados = sum(1 for r in results if r["foi_absolvido"] is None)
        
        # Estatísticas de confiança da IA
        confiancas = [r.get("confianca_analise", 0) for r in results if r.get("confianca_analise") is not None]
        confianca_media = sum(confiancas) / len(confiancas) if confiancas else 0
        
        return {
            "total_processados": total,
            "total_absolvidos": absolvidos,
            "total_nao_absolvidos": nao_absolvidos,
            "total_sem_dados": sem_dados,
            "percentual_absolvidos": (absolvidos / total * 100) if total > 0 else 0,
            "percentual_nao_absolvidos": (nao_absolvidos / total * 100) if total > 0 else 0,
            "percentual_sem_dados": (sem_dados / total * 100) if total > 0 else 0,
            "confianca_media_ia": confianca_media,
            "analises_com_alta_confianca": sum(1 for c in confiancas if c >= 80),
            "analises_com_baixa_confianca": sum(1 for c in confiancas if c < 50)
        }

# Função para teste
if __name__ == "__main__":
    # Teste com alguns CPFs de exemplo
    analyzer = BatchAbsolutionAnalyzerLLM(max_workers=2, delay_between_requests=0.5)
    
    cpfs_teste = [
        "01130380114",  # CPF de exemplo
        "12345678901",  # CPF inválido para teste
    ]
    
    results = analyzer.process_batch(cpfs_teste)
    
    # Mostrar resultados
    for result in results:
        print(f"\n🤖 ANÁLISE IA:")
        print(f"CPF: {result['cpf']}")
        print(f"Nome: {result['nome']}")
        print(f"Foi absolvido: {result['foi_absolvido']}")
        print(f"Confiança: {result.get('confianca_analise', 0)}%")
        print(f"Justificativa: {result.get('justificativa', '')}")
        print(f"Detalhes IA: {result.get('detalhes_ia', '')}")
        print(f"Status: {result['status']}")
        print("-" * 70)
    
    # Estatísticas
    stats = analyzer.get_summary_stats(results)
    print("\n📊 ESTATÍSTICAS IA:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # Exportar para CSV
    analyzer.export_to_csv(results, "teste_absolvicoes_llm.csv")
