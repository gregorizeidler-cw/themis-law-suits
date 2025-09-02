# 📦 #### Batch Processor - Análise de Absolvição em Lote
import os
import re
import json
import time
import threading
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import requests
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# 🔐 #### Credenciais
bigdata_token_id = os.getenv('BIGDATA_TOKEN_ID')
bigdata_token_hash = os.getenv('BIGDATA_TOKEN_HASH')

class BatchAbsolutionAnalyzer:
    """Analisador de absolvições em lote para múltiplos CPFs"""
    
    def __init__(self, max_workers: int = 10, delay_between_requests: float = 0.1):
        self.max_workers = max_workers
        self.delay_between_requests = delay_between_requests
        
        # Verificar credenciais
        if not bigdata_token_id or not bigdata_token_hash:
            raise ValueError("Credenciais BigData Corp não configuradas no arquivo .env")
    
    def fetch_single_cpf_data(self, cpf: str) -> Dict:
        """Buscar dados de um único CPF focando apenas em processos criminais"""
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
                "Datasets": "basic_data,processes.filter(partypolarity = PASSIVE, courttype = CRIMINAL)"
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
    
    def analyze_absolution(self, bdc_data: Dict, cpf: str) -> Dict:
        """Analisar se houve absolvição nos processos criminais"""
        try:
            if "Result" not in bdc_data or not bdc_data["Result"]:
                return {
                    "cpf": cpf,
                    "nome": "Não encontrado",
                    "foi_absolvido": None,
                    "total_processos_criminais": 0,
                    "total_absolvicoes": 0,
                    "detalhes_absolvicoes": [],
                    "status": "dados_nao_encontrados"
                }
            
            pessoa = bdc_data["Result"][0]
            basic = pessoa.get("BasicData", {})
            nome = basic.get("Name", "Nome não informado")
            
            processos = pessoa.get("Processes", {})
            lawsuits = processos.get("Lawsuits", [])
            
            # Filtrar apenas processos criminais onde a pessoa é ré
            processos_criminais = []
            for proc in lawsuits:
                if proc.get("CourtType") == "CRIMINAL":
                    # Verificar se a pessoa é ré
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
            
            total_processos = len(processos_criminais)
            absolvicoes = []
            
            # Analisar decisões em busca de absolvições
            for proc in processos_criminais:
                numero_processo = proc.get("CaseNumber") or proc.get("Number", "")
                
                # Verificar em diferentes campos onde podem estar as decisões
                campos_decisao = [
                    proc.get("Decision", ""),
                    proc.get("Content", ""),
                    proc.get("Description", ""),
                    proc.get("Summary", "")
                ]
                
                # Verificar decisões específicas do processo
                decisoes = proc.get("Decisions", [])
                for decisao in decisoes:
                    campos_decisao.append(decisao.get("DecisionContent", ""))
                
                # Buscar por palavras-chave de absolvição
                for campo in campos_decisao:
                    if isinstance(campo, str) and campo.strip():
                        texto_lower = campo.lower()
                        
                        # Palavras-chave que indicam absolvição
                        palavras_absolvicao = [
                            'absolv', 'improcedent', 'arquiv', 'extinç', 
                            'não procede', 'nao procede', 'julgo improcedente',
                            'absolvo', 'não há elementos', 'nao ha elementos',
                            'ausência de provas', 'ausencia de provas',
                            'insuficiência de provas', 'insuficiencia de provas'
                        ]
                        
                        for palavra in palavras_absolvicao:
                            if palavra in texto_lower:
                                absolvicoes.append({
                                    "processo": numero_processo,
                                    "tipo_decisao": self._classify_absolution_type(campo),
                                    "data": proc.get("CloseDate") or proc.get("LastMovementDate"),
                                    "orgao": proc.get("CourtName"),
                                    "comarca": proc.get("CourtDistrict"),
                                    "trecho_decisao": campo[:200] + "..." if len(campo) > 200 else campo
                                })
                                break
                        
                        if absolvicoes and absolvicoes[-1]["processo"] == numero_processo:
                            break
            
            total_absolvicoes = len(absolvicoes)
            foi_absolvido = total_absolvicoes > 0
            
            return {
                "cpf": cpf,
                "nome": nome,
                "foi_absolvido": foi_absolvido,
                "total_processos_criminais": total_processos,
                "total_absolvicoes": total_absolvicoes,
                "detalhes_absolvicoes": absolvicoes,
                "status": "sucesso"
            }
            
        except Exception as e:
            return {
                "cpf": cpf,
                "nome": "Erro no processamento",
                "foi_absolvido": None,
                "total_processos_criminais": 0,
                "total_absolvicoes": 0,
                "detalhes_absolvicoes": [],
                "status": f"erro: {str(e)}"
            }
    
    def _classify_absolution_type(self, texto: str) -> str:
        """Classificar o tipo de absolvição baseado no texto"""
        texto_lower = texto.lower()
        
        if any(word in texto_lower for word in ['absolv']):
            return "Absolvição"
        elif any(word in texto_lower for word in ['improcedent', 'não procede', 'nao procede']):
            return "Improcedência"
        elif any(word in texto_lower for word in ['arquiv']):
            return "Arquivamento"
        elif any(word in texto_lower for word in ['extinç']):
            return "Extinção"
        else:
            return "Outra forma de absolvição"
    
    def process_batch(self, cpfs: List[str], progress_callback=None) -> List[Dict]:
        """Processar lista de CPFs em lote"""
        results = []
        total = len(cpfs)
        
        print(f"Iniciando processamento em lote de {total} CPFs...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submeter todas as tarefas
            future_to_cpf = {executor.submit(self.fetch_single_cpf_data, cpf): cpf for cpf in cpfs}
            
            for i, future in enumerate(as_completed(future_to_cpf), 1):
                cpf = future_to_cpf[future]
                try:
                    bdc_data = future.result()
                    
                    # Analisar absolvição
                    if "error" in bdc_data:
                        result = {
                            "cpf": cpf,
                            "nome": "Erro na consulta",
                            "foi_absolvido": None,
                            "total_processos_criminais": 0,
                            "total_absolvicoes": 0,
                            "detalhes_absolvicoes": [],
                            "status": f"erro_api: {bdc_data['error']}"
                        }
                    else:
                        result = self.analyze_absolution(bdc_data, cpf)
                    
                    results.append(result)
                    
                    # Callback de progresso
                    if progress_callback:
                        progress_callback(i, total, result)
                    
                    # Log de progresso
                    if i % 10 == 0 or i == total:
                        print(f"Processados: {i}/{total} CPFs ({i/total*100:.1f}%)")
                
                except Exception as exc:
                    print(f'CPF {cpf} gerou exceção: {exc}')
                    results.append({
                        "cpf": cpf,
                        "nome": "Erro na consulta",
                        "foi_absolvido": None,
                        "total_processos_criminais": 0,
                        "total_absolvicoes": 0,
                        "detalhes_absolvicoes": [],
                        "status": f"excecao: {str(exc)}"
                    })
        
        return results
    
    def export_to_csv(self, results: List[Dict], filename: str = "analise_absolvicoes.csv"):
        """Exportar resultados para CSV"""
        # Dados básicos para CSV
        csv_data = []
        for result in results:
            csv_data.append({
                "CPF": result["cpf"],
                "Nome": result["nome"],
                "Foi_Absolvido": result["foi_absolvido"],
                "Total_Processos_Criminais": result["total_processos_criminais"],
                "Total_Absolvicoes": result["total_absolvicoes"],
                "Status": result["status"]
            })
        
        df = pd.DataFrame(csv_data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"Resultados exportados para: {filename}")
        return filename
    
    def get_summary_stats(self, results: List[Dict]) -> Dict:
        """Obter estatísticas resumidas dos resultados"""
        total = len(results)
        absolvidos = sum(1 for r in results if r["foi_absolvido"] is True)
        nao_absolvidos = sum(1 for r in results if r["foi_absolvido"] is False)
        sem_dados = sum(1 for r in results if r["foi_absolvido"] is None)
        
        return {
            "total_processados": total,
            "total_absolvidos": absolvidos,
            "total_nao_absolvidos": nao_absolvidos,
            "total_sem_dados": sem_dados,
            "percentual_absolvidos": (absolvidos / total * 100) if total > 0 else 0,
            "percentual_nao_absolvidos": (nao_absolvidos / total * 100) if total > 0 else 0,
            "percentual_sem_dados": (sem_dados / total * 100) if total > 0 else 0
        }

# Função para teste
if __name__ == "__main__":
    # Teste com alguns CPFs de exemplo
    analyzer = BatchAbsolutionAnalyzer(max_workers=5)
    
    cpfs_teste = [
        "01130380114",  # CPF de exemplo
        "12345678901",  # CPF inválido para teste
    ]
    
    results = analyzer.process_batch(cpfs_teste)
    
    # Mostrar resultados
    for result in results:
        print(f"CPF: {result['cpf']}")
        print(f"Nome: {result['nome']}")
        print(f"Foi absolvido: {result['foi_absolvido']}")
        print(f"Total processos criminais: {result['total_processos_criminais']}")
        print(f"Total absolvições: {result['total_absolvicoes']}")
        print(f"Status: {result['status']}")
        print("-" * 50)
    
    # Estatísticas
    stats = analyzer.get_summary_stats(results)
    print("ESTATÍSTICAS:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # Exportar para CSV
    analyzer.export_to_csv(results, "teste_absolvicoes.csv")
