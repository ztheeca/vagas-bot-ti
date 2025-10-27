# ===========================
# 📦 IMPORTAÇÕES
# ===========================
import os
import time
import random
import logging
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from dotenv import load_dotenv

load_dotenv()

# ===========================
# 🔧 CONFIGURAÇÕES
# ===========================
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
LOCAL = os.getenv("LOCAL", "Salvador, BA")

# Sites ativos
SITES_ATIVOS = {
    'linkedin': True,
    'programathor': True,  # Site focado em TI! 🎯
    'glassdoor': True,
    'catho': True,
    'infojobs': True
}

# ===========================
# 🎯 TERMOS DE BUSCA ESTRATÉGICOS
# ===========================
TERMOS_BUSCA = [
    "estágio ti",
    "estagio tecnologia",
    "auxiliar ti",
    "junior ti",
    "desenvolvedor junior",
    "analista ti junior",
    "suporte tecnico",
    "ti"
]

# ===========================
# 📝 CONFIGURAÇÃO DE LOGS
# ===========================
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def log_info(message): logging.info(f"📝 {message}")
def log_error(message): logging.error(f"❌ {message}")
def log_success(message): logging.info(f"✅ {message}")

# ===========================
# 🎯 FILTRO DE VAGAS
# ===========================
def filtrar_vaga_ti(titulo, site_nome=""):
    """Filtro MENOS restritivo - aceita tudo exceto sênior e não-TI"""
    if not titulo or len(titulo) < 8:
        return False
    
    titulo_lower = titulo.lower()
    
    # REJEIÇÃO IMEDIATA para termos óbvios não-TI
    rejeicao_imediata = [
        'marketing', 'arquivologia', 'licitações', 'licitacao',
        'suprimentos', 'supply chain', 'contábil', 'contabil',
        'administrativo', 'vendedor', 'comercial'
    ]
    
    if any(termo in titulo_lower for termo in rejeicao_imediata):
        # EXCEÇÃO: Se tem "tech" ou "tecnologia" junto, pode ser válido
        if not any(t in titulo_lower for t in ['tech', 'tecnologia', 'ti ']):
            return False
    
    # Termos TI
    termos_ti = [
        'ti', 'tecnologia', 'informação', 'informacao', 'tech',
        'desenvolvedor', 'developer', 'dev',
        'programador', 'programadora', 'programação',
        'analista', 'técnico', 'tecnico',
        'software', 'sistema', 'web', 'mobile', 'app',
        'java', 'python', 'javascript', 'php', 'c#', '.net',
        'react', 'angular', 'node', 'sql', 'database',
        'cloud', 'aws', 'azure', 'devops', 'docker',
        'ux', 'ui', 'dados', 'data', 'bi', 'analytics',
        'segurança', 'cyber', 'redes', 'infra',
        'suporte', 'help desk', 'service desk',
        'qa', 'teste', 'tester', 'quality',
        'scrum', 'agile', 'product'
    ]
    
    # Rejeitar APENAS sênior
    termos_senior = [
        'sênior', 'senior', 'sr.', 'sr ', ' sr',
        'coordenador', 'gerente', 'diretor',
        'tech lead', 'principal', 'head'
    ]
    
    # Rejeitar não-TI (LISTA EXPANDIDA)
    termos_nao_ti = [
        # Vendas e Comercial
        'vendedor', 'comercial', 'representante',
        
        # Operacional
        'motorista', 'entregador', 'delivery',
        
        # Administrativo (NÃO TI)
        'administrativo', 'administração', 'administracion',
        'recepcionista', 'secretária', 'office boy',
        'auxiliar administrativo', 'assistente administrativo',
        
        # Contábil e Financeiro
        'contador', 'contábil', 'contable', 'accounting',
        'financeiro', 'tesoureiro', 'fiscal',
        
        # RH
        'recursos humanos', 'rh', 'recrutador',
        
        # Marketing (que não seja tech)
        'social media', 'copywriter', 'redator',
        
        # Outras profissões
        'professor', 'educador', 'instrutor',
        'enfermeiro', 'médico', 'fisioterapeuta',
        'advogado', 'jurídico', 'paralegal',
        'atendente', 'caixa', 'garçom', 'cozinheiro',
        
        # Arquitetura e Engenharia Civil
        'arquivologia', 'arquivista', 'obra',
        'proyectos sociales', 'rr.hh',
        
        # Licitações e Suprimentos (NÃO TI)
        'licitações', 'licitacao', 'suprimentos',
        
        # Links do site
        'anunciar', 'cadastrar', 'entrar', 'login',
        'ver mais', 'saiba mais', 'clique'
    ]
    
    # Rejeitar cidades soltas
    if titulo_lower.count('-') >= 2 and titulo_lower.count(' ') < 3:
        return False
    
    tem_ti = any(t in titulo_lower for t in termos_ti)
    nao_ti = any(t in titulo_lower for t in termos_nao_ti)
    eh_senior = any(t in titulo_lower for t in termos_senior)
    
    return tem_ti and not nao_ti and not eh_senior

# ===========================
# 🔍 BUSCA GENÉRICA
# ===========================
def buscar_vagas_site(site_nome, url_template, xpaths, termo_busca, wait_time=5):
    """Função genérica para buscar em qualquer site"""
    driver = None
    
    try:
        options = ChromeOptions()
        options.binary_location = "/usr/bin/google-chrome-stable"  # Força o uso do Chrome instalado
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--headless')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        driver = uc.Chrome(options=options, use_subprocess=False)
        
    except Exception as e:
        log_error(f"{site_nome}: Erro ao iniciar - {str(e)[:60]}")
        return []


    try:
        url = url_template.format(termo=termo_busca.replace(' ', '+'), local=LOCAL.replace(' ', '+').replace(',', ''))
        log_info(f"🔗 {site_nome}: {termo_busca}")
        
        driver.get(url)
        time.sleep(random.uniform(wait_time, wait_time + 3))
        
        vagas = []
        for xpath in xpaths:
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located((By.XPATH, xpath))
                )
                elementos = driver.find_elements(By.XPATH, xpath)
                if elementos and len(elementos) > 2:
                    log_info(f"✓ {site_nome}: {len(elementos)} elementos encontrados")
                    vagas = elementos
                    break
            except:
                continue
        
        if not vagas:
            log_info(f"⚠ {site_nome}: Nenhum elemento encontrado")
            return []
        
        resultados = []
        vagas_vistas = set()
        
        for job in vagas[:20]:
            try:
                titulo = job.text.strip()
                link = job.get_attribute("href")
                
                if not titulo or len(titulo) < 8 or not link:
                    continue
                
                # Evitar duplicatas
                if titulo in vagas_vistas:
                    continue
                
                # Validação RIGOROSA - precisa ter pelo menos 2 palavras válidas
                palavras_validas_primary = ['desenvolvedor', 'programador', 'ti', 'tecnologia', 'software', 'suporte técnico', 'help desk']
                palavras_validas_secondary = ['vaga', 'emprego', 'job', 'analista', 'técnico', 'estagio', 'junior', 'tech', 'developer']
                
                tem_primary = any(p in titulo.lower() for p in palavras_validas_primary)
                tem_secondary = any(p in titulo.lower() for p in palavras_validas_secondary)
                
                if not (tem_primary or tem_secondary):
                    continue
                
                if filtrar_vaga_ti(titulo, site_nome):
                    resultados.append(f"**{titulo}**\n{link}")
                    vagas_vistas.add(titulo)
                    log_success(f"{site_nome}: {titulo[:60]}...")
                
                time.sleep(random.uniform(0.2, 0.5))
                    
            except Exception:
                continue
        
        return resultados
        
    except Exception as e:
        log_error(f"{site_nome}: {str(e)[:80]}")
        return []
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

# ===========================
# 🌐 CONFIGURAÇÕES DOS SITES
# ===========================
def buscar_todas_plataformas():
    """Busca em todas as plataformas com múltiplos termos"""
    
    todas_vagas = []
    
    # ===========================
    # LINKEDIN
    # ===========================
    if SITES_ATIVOS['linkedin']:
        log_info("🌐 Buscando no LinkedIn...")
        xpaths_linkedin = [
            "//a[contains(@href, '/jobs/view/')]",
            "//div[contains(@class, 'job-card')]//a",
            "//div[contains(@class, 'base-search-card')]//a",
            "//h3[contains(@class, 'job-card')]//a"
        ]
        
        for termo in TERMOS_BUSCA[:2]:
            local_linkedin = LOCAL.replace(',', '').replace(' ', '%20')
            # LinkedIn requer localização codificada
            url_linkedin = f"https://www.linkedin.com/jobs/search/?keywords={{termo}}&location={local_linkedin}"
            vagas = buscar_vagas_site("LinkedIn", url_linkedin, xpaths_linkedin, termo, wait_time=6)
            todas_vagas.extend(vagas)
            time.sleep(random.uniform(5, 8))
        
        log_info(f"📊 LinkedIn: {len([v for v in todas_vagas])} vagas")
    
    # ===========================
    # GLASSDOOR
    # ===========================
    if SITES_ATIVOS['glassdoor']:
        log_info("🌐 Buscando no Glassdoor...")
        xpaths_glassdoor = [
            "//a[contains(@class, 'JobCard_jobTitle') or contains(@class, 'job-title')]",
            "//a[contains(@data-test, 'job-link')]",
            "//h2[contains(@class, 'jobTitle')]//a",
            "//div[contains(@class, 'JobCard')]//a[contains(@href, '/job/')]"
        ]
        
        count_inicial = len(todas_vagas)
        for termo in TERMOS_BUSCA[:2]:
            # Glassdoor BR usa estrutura diferente
            termo_encoded = termo.replace(' ', '%20')
            url_glassdoor = f"https://www.glassdoor.com.br/Vaga/brasil-{{termo}}-vagas-SRCH_IL.0,6_IN36_KO7.htm"
            vagas = buscar_vagas_site("Glassdoor", url_glassdoor, xpaths_glassdoor, termo, wait_time=7)
            todas_vagas.extend(vagas)
            time.sleep(random.uniform(6, 9))
        
        log_info(f"📊 Glassdoor: {len(todas_vagas) - count_inicial} vagas")
    
    # ===========================
    # CATHO
    # ===========================
    if SITES_ATIVOS['catho']:
        log_info("🌐 Buscando na Catho...")
        xpaths_catho = [
            "//div[contains(@class, 'job') or contains(@class, 'vacancy')]//a",
            "//article//a",
            "//h3//a | //h2//a"
        ]
        
        count_inicial = len(todas_vagas)
        for termo in TERMOS_BUSCA[:3]:
            local_catho = LOCAL.replace(',', '').replace(' ', '-').lower()
            url_catho = f"https://www.catho.com.br/vagas/{local_catho}/?q={{termo}}"
            vagas = buscar_vagas_site("Catho", url_catho, xpaths_catho, termo, wait_time=5)
            todas_vagas.extend(vagas)
            time.sleep(random.uniform(3, 5))
        
        log_info(f"📊 Catho: {len(todas_vagas) - count_inicial} vagas")
    
    # ===========================
    # INFOJOBS
    # ===========================
    if SITES_ATIVOS['infojobs']:
        log_info("🌐 Buscando no InfoJobs...")
        xpaths_infojobs = [
            "//div[contains(@class, 'job') or contains(@class, 'vacancy')]//a",
            "//article//a",
            "//h3//a | //h2//a"
        ]
        
        count_inicial = len(todas_vagas)
        for termo in TERMOS_BUSCA[:2]:
            local_info = LOCAL.replace(',', '').replace(' ', '-').lower()
            url_info = f"https://www.infojobs.com.br/vagas-de-emprego-{local_info}.aspx?palavra={{termo}}"
            vagas = buscar_vagas_site("InfoJobs", url_info, xpaths_infojobs, termo, wait_time=5)
            todas_vagas.extend(vagas)
            time.sleep(random.uniform(3, 5))
        
        log_info(f"📊 InfoJobs: {len(todas_vagas) - count_inicial} vagas")
    
    # Remover duplicatas finais
    vagas_unicas = list(dict.fromkeys(todas_vagas))  # Mantém a ordem
    return vagas_unicas

# ===========================
# 🚀 ENVIAR DISCORD
# ===========================
def enviar_discord(vagas):
    if not vagas:
        log_info("📭 Nenhuma vaga para enviar")
        try:
            if DISCORD_WEBHOOK_URL:
                requests.post(DISCORD_WEBHOOK_URL, 
                            json={"content": f"🔍 Nenhuma vaga de TI encontrada em {LOCAL}."}, 
                            timeout=10)
        except:
            pass
        return
    
    # Formatar mensagem mais bonita
    mensagem_header = f"🎯 **{len(vagas)} Vagas de TI em {LOCAL}**\n"
    mensagem_header += f"📅 {time.strftime('%d/%m/%Y às %H:%M')}\n"
    mensagem_header += "─" * 50 + "\n\n"
    
    # Limitar a 10 vagas por mensagem (limite do Discord)
    vagas_formatadas = "\n\n".join(vagas[:10])
    mensagem = mensagem_header + vagas_formatadas
    
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": mensagem}, timeout=10)
        log_success("📤 Mensagem enviada para Discord!")
        
        # Se houver mais de 10 vagas, enviar em mensagem separada
        if len(vagas) > 10:
            time.sleep(2)
            mensagem_extra = f"📋 **Mais {len(vagas) - 10} vagas:**\n\n" + "\n\n".join(vagas[10:15])
            requests.post(DISCORD_WEBHOOK_URL, json={"content": mensagem_extra}, timeout=10)
            log_success("📤 Mensagem adicional enviada!")
            
    except Exception as e:
        log_error(f"Erro Discord: {e}")

# ===========================
# 🧠 FUNÇÃO PRINCIPAL
# ===========================
def main():
    setup_logging()
    log_info("🚀 Iniciando busca AVANÇADA de vagas...")
    log_info(f"🔍 Buscando em: {', '.join([k.replace('_', '.').title() for k, v in SITES_ATIVOS.items() if v])}")
    
    if not DISCORD_WEBHOOK_URL:
        log_error("❌ Discord webhook não configurado")
        return
    
    todas_vagas = buscar_todas_plataformas()
    
    if todas_vagas:
        log_success(f"🎯 Total: {len(todas_vagas)} vagas únicas encontradas!")
        enviar_discord(todas_vagas)
    else:
        log_info("📭 Nenhuma vaga encontrada")
        enviar_discord([])
    
    log_success("🏁 Busca concluída!")

if __name__ == "__main__":
    main()



