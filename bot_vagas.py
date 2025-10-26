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
# 🎯 FILTRO DE VAGAS DE TI MELHORADO
# ===========================
def filtrar_vaga_ti(titulo):
    """Filtro inteligente para vagas de TI junior/estágio/auxiliar, excluindo pleno/senior"""
    if not titulo or len(titulo) < 5:
        return False
    
    titulo_lower = titulo.lower()
    
    termos_ti = [
        'ti', 'tecnologia', 'tecnológico', 'tecnológica',
        'desenvolvedor', 'developer', 'dev',
        'programador', 'programadora', 'programação',
        'analista', 'analista de', 
        'software', 'sistema', 'sistemas',
        'web', 'frontend', 'front-end', 'backend', 'back-end', 'fullstack', 'full stack',
        'mobile', 'android', 'ios',
        'java', 'python', 'javascript', 'php', 'c#', 'c++', 'ruby', 'go', 'rust',
        'react', 'angular', 'vue', 'node', 'django', 'spring',
        'banco de dados', 'sql', 'mysql', 'postgresql', 'mongodb',
        'cloud', 'aws', 'azure', 'google cloud', 'devops',
        'ux', 'ui', 'designer', 'design',
        'dados', 'data', 'big data', 'bi', 'business intelligence',
        'segurança', 'cyber', 'security',
        'redes', 'infraestrutura', 'infra',
        'suporte', 'help desk', 'service desk',
        'qualidade', 'qa', 'teste', 'testing',
        'scrum', 'agile', 'product owner', 'po', 'scrum master'
    ]
    
    termos_inclusao_ti = [
        'auxiliar', 'assistente', 'estágio', 'estagiário', 'estagiária', 'junior', 'júnior', 'jr', 'jr.'
    ]
    
    termos_exclusao_ti = [
        'pleno', 'sênior', 'senior', 'sr', 'sr.'
    ]
    
    termos_nao_ti = [
        'vendedor', 'comercial', 'representante', 'consultor comercial',
        'motorista', 'entregador', 'delivery',
        'auxiliar', 'assistente administrativo', 'recepcionista',
        'professor', 'educador', 'instrutor',
        'enfermeiro', 'médico', 'fisioterapeuta',
        'advogado', 'jurídico',
        'contador', 'accounting',
        'marketing', 'mídia', 'publicidade',
        'rh', 'recursos humanos', 'human resources',
        'financeiro', 'financeira', 'financial',
        'administrativo', 'administração',
        'atendente', 'caixa', 'balconista',
        'cozinheiro', 'chef', 'garçom',
        'estágio jurídico', 'estágio administrativo', 'estágio contábil'
    ]
    
    tem_termo_ti = any(termo in titulo_lower for termo in termos_ti)
    nao_tem_nao_ti = not any(termo in titulo_lower for termo in termos_nao_ti)
    tem_inclusao = any(termo in titulo_lower for termo in termos_inclusao_ti)
    nao_tem_exclusao = not any(termo in titulo_lower for termo in termos_exclusao_ti)
    
    return tem_termo_ti and nao_tem_nao_ti and tem_inclusao and nao_tem_exclusao

# ===========================
# 🔍 BUSCA INFOJOBS
# ===========================
def buscar_vagas_infojobs():
    log_info("🌐 Buscando no InfoJobs...")
    driver = None
    
    try:
        options = ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--headless')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        driver = uc.Chrome(options=options, use_subprocess=False)
        
        url = f"https://www.infojobs.com.br/vagas-de-emprego-{LOCAL.replace(',', '').replace(' ', '-').lower()}.aspx?palabra=desenvolvedor"
        log_info(f"🔗 {url}")
        
        driver.get(url)
        time.sleep(random.uniform(5, 8))
        
        # Atualizado: Seletores expandidos
        seletores = [
            "a.js_vacancyTitle",
            ".vacancy-title a",
            "[data-vacancy-title]",
            "a[href*='/vagas']",
            ".job-title a",
            "h3 a",
            ".card-job a"
        ]
        
        vagas = []
        for seletor in seletores:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, seletor))
                )
                elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
                log_info(f"Elementos com '{seletor}': {len(elementos)}")  # Novo: Debug
                if elementos:
                    vagas = elementos
                    log_info(f"🔍 {len(vagas)} vagas encontradas")
                    break
            except:
                continue
        
        resultados = []
        for job in vagas[:12]:
            try:
                titulo = job.text.strip()
                link = job.get_attribute("href")
                
                if not titulo or len(titulo) < 5 or not link:
                    continue
                
                # Novo: Filtro extra para títulos inválidos
                if len(titulo) < 10 or not any(word in titulo.lower() for word in ['vaga', 'emprego', 'job', 'desenvolvedor']):
                    log_info(f"Pulado (título inválido): {titulo[:50]}...")
                    continue
                
                log_info(f"Analisando vaga: {titulo[:50]}...")
                
                if filtrar_vaga_ti(titulo):
                    resultados.append(f"**{titulo}**\n{link}")
                    log_success(f"InfoJobs: {titulo[:50]}...")
                else:
                    log_info(f"Rejeitado: {titulo[:50]}...")
                
                time.sleep(random.uniform(0.3, 0.8))
                    
            except Exception as e:
                continue
        
        log_info(f"📊 InfoJobs: {len(resultados)} vagas filtradas")
        return resultados
        
    except Exception as e:
        log_error(f"Erro InfoJobs: {str(e)[:100]}...")
        return []
    finally:
        if driver:
            driver.quit()
            time.sleep(random.uniform(2, 3))

# ===========================
# 🔍 BUSCA CATHO
# ===========================
def buscar_vagas_catho():
    log_info("🌐 Buscando na Catho...")
    driver = None
    
    try:
        options = ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--headless')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        driver = uc.Chrome(options=options, use_subprocess=False)
        
        local_catho = LOCAL.replace(',', '').replace(' ', '-').lower()
        url = f"https://www.catho.com.br/vagas/{local_catho}/?q=desenvolvedor"
        log_info(f"🔗 {url}")
        
        driver.get(url)
        time.sleep(random.uniform(7, 10))
        
        # Atualizado: Seletores expandidos
        seletores_catho = [
            "a[data-testid*='job']",
            "[data-id*='job']",
            "a[href*='/vaga/']",
            ".job-card a",
            "a[class*='job']",
            "h3 a",
            ".sc-1h4w872-0 a",
            ".job-item a",
            ".search-result-item a",
            ".job-link",
            ".vacancy-link a"
        ]
        
        vagas = []
        for seletor in seletores_catho:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, seletor))
                )
                elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
                log_info(f"Elementos com '{seletor}': {len(elementos)}")  # Novo: Debug
                if elementos:
                    vagas = elementos
                    log_info(f"🔍 {len(vagas)} vagas")
                    break
            except:
                continue
        
        resultados = []
        for job in vagas[:10]:
            try:
                titulo = job.text.strip()
                link = job.get_attribute("href")
                
                if not titulo or len(titulo) < 5 or not link:
                    continue
                
                # Novo: Filtro extra para títulos inválidos
                if len(titulo) < 10 or not any(word in titulo.lower() for word in ['vaga', 'emprego', 'job', 'desenvolvedor']):
                    log_info(f"Pulado (título inválido): {titulo[:50]}...")
                    continue
                
                log_info(f"Analisando vaga: {titulo[:50]}...")
                
                if filtrar_vaga_ti(titulo):
                    resultados.append(f"**{titulo}**\n{link}")
                    log_success(f"Catho: {titulo[:50]}...")
                else:
                    log_info(f"Rejeitado: {titulo[:50]}...")
                
                time.sleep(random.uniform(0.3, 0.8))
                    
            except Exception as e:
                continue
        
        log_info(f"📊 Catho: {len(resultados)} vagas filtradas")
        return resultados
        
    except Exception as e:
        log_error(f"Erro Catho: {str(e)[:100]}...")
        return []
    finally:
        if driver:
            driver.quit()
            time.sleep(random.uniform(2, 3))

# ===========================
# 🔍 BUSCA INDEED
# ===========================
def buscar_vagas_indeed():
    log_info("🌐 Buscando no Indeed...")
    driver = None
    
    try:
        options = ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--headless')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        driver = uc.Chrome(options=options, use_subprocess=False)
        
        url = f"https://br.indeed.com/jobs?q=programador&l={LOCAL.replace(' ', '+')}"
        log_info(f"🔗 {url}")
        
        driver.get(url)
        time.sleep(random.uniform(6, 9))
        
        # Atualizado: Seletores expandidos
        seletores_indeed = [
            "a[class*='jcs-JobTitle']",
            "[data-jk]",
            "a.jobTitle",
            ".job_seen_beacon a",
            "a[href*='/viewjob']",
            "h2 a",
            ".jobtitle a",
            ".resultContent a",
            ".jobsearch-ResultsList a",
            ".jobtitle-link",
            ".tapItem a"
        ]
        
        vagas = []
        for seletor in seletores_indeed:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, seletor))
                )
                elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
                log_info(f"Elementos com '{seletor}': {len(elementos)}")  # Novo: Debug
                if elementos and len(elementos) > 2:
                    vagas = elementos
                    log_info(f"🔍 {len(vagas)} vagas")
                    break
            except:
                continue
        
        resultados = []
        for job in vagas[:10]:
            try:
                titulo = job.text.strip()
                link = job.get_attribute("href")
                
                if not titulo or len(titulo) < 5 or not link:
                    continue
                
                # Novo: Filtro extra para títulos inválidos
                if len(titulo) < 10 or not any(word in titulo.lower() for word in ['
