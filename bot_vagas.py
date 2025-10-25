# ===========================
# 📦 IMPORTAÇÕES
# ===========================
import os
import time
import random
import logging
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
# 🛠️ CONFIGURAÇÃO CHROME STEALTH
# ===========================
def setup_chrome_stealth():
    """Configuração stealth para evitar detecção"""
    options = Options()
    
    # Configurações básicas
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # Configurações stealth
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # User agents realistas (rotaciona)
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    options.add_argument(f"--user-agent={random.choice(user_agents)}")
    
    # Para Chromium
    options.binary_location = "/usr/bin/chromium-browser"
    
    return options

def remover_rastros_automacao(driver):
    """Remove rastros de automação"""
    try:
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    except:
        pass

# ===========================
# 🔍 BUSCA INDEED COM FALLBACKS
# ===========================
def buscar_vagas_indeed():
    log_info("🌐 Buscando no Indeed...")
    driver = None
    
    try:
        options = setup_chrome_stealth()
        driver = webdriver.Chrome(options=options)
        remover_rastros_automacao(driver)
        
        # URL alternativa mais simples
        url = f"https://br.indeed.com/jobs?q=ti&l={LOCAL.replace(' ', '+')}"
        log_info(f"🔗 {url}")
        
        driver.get(url)
        time.sleep(random.uniform(3, 6))  # Espera aleatória
        
        # Tenta diferentes abordagens
        vagas = []
        
        # Método 1: Seletores comuns
        seletores = [
            "a.jcs-JobTitle",
            "[data-jk]",
            ".jobTitle",
            "a[class*='jobTitle']",
            ".jcs-JobTitle"
        ]
        
        for seletor in seletores:
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
                if elementos:
                    vagas = elementos
                    log_info(f"🔍 {len(vagas)} vagas com: {seletor}")
                    break
            except:
                continue
        
        # Método 2: Busca por texto
        if not vagas:
            try:
                page_source = driver.page_source.lower()
                if "vagas" in page_source or "emprego" in page_source:
                    log_info("📄 Página carregou, mas não encontrou elementos")
                else:
                    log_info("🚫 Página pode estar bloqueada")
            except:
                pass
        
        resultados = []
        for job in vagas[:6]:
            try:
                titulo = job.text.strip()
                link = job.get_attribute("href")
                
                if not titulo or len(titulo) < 5:
                    continue
                
                # Filtro TI
                termos_ti = ['ti', 'tecnologia', 'desenvolvedor', 'programador', 'analista', 'software', 'sistema', 'dev', 'dados']
                if any(termo in titulo.lower() for termo in termos_ti):
                    resultados.append(f"**{titulo}**\n{link}")
                    log_success(f"✅ Indeed: {titulo}")
                    
            except Exception as e:
                continue
                
        return resultados
        
    except Exception as e:
        log_error(f"Erro Indeed: {str(e)[:100]}...")
        return []
    finally:
        if driver:
            driver.quit()

# ===========================
# 🔍 BUSCA INFOJOBS (ALTERNATIVA AO GLASSDOOR)
# ===========================
def buscar_vagas_infojobs():
    log_info("🌐 Buscando no InfoJobs...")
    driver = None
    
    try:
        options = setup_chrome_stealth()
        driver = webdriver.Chrome(options=options)
        remover_rastros_automacao(driver)
        
        # InfoJobs é mais acessível
        url = f"https://www.infojobs.com.br/vagas-de-emprego-{LOCAL.replace(',', '').replace(' ', '-').lower()}.aspx?palabra=desenvolvedor"
        log_info(f"🔗 {url}")
        
        driver.get(url)
        time.sleep(random.uniform(4, 7))
        
        # Seletores InfoJobs
        seletores = [
            "a.js_vacancyTitle",
            ".vacancy-title a",
            "[data-vacancy-title]",
            "a[href*='/vagas']"
        ]
        
        vagas = []
        for seletor in seletores:
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
                if elementos:
                    vagas = elementos
                    log_info(f"🔍 {len(vagas)} vagas com: {seletor}")
                    break
            except:
                continue
        
        resultados = []
        for job in vagas[:6]:
            try:
                titulo = job.text.strip()
                link = job.get_attribute("href")
                
                if not titulo or len(titulo) < 5:
                    continue
                
                # Filtro TI
                termos_ti = ['ti', 'tecnologia', 'desenvolvedor', 'programador', 'analista', 'software', 'sistema', 'dev']
                if any(termo in titulo.lower() for termo in termos_ti):
                    resultados.append(f"**{titulo}**\n{link}")
                    log_success(f"✅ InfoJobs: {titulo}")
                    
            except:
                continue
                
        return resultados
        
    except Exception as e:
        log_error(f"Erro InfoJobs: {str(e)[:100]}...")
        return []
    finally:
        if driver:
            driver.quit()

# ===========================
# 🔍 BUSCA CATHO (ALTERNATIVA)
# ===========================
def buscar_vagas_catho():
    log_info("🌐 Buscando na Catho...")
    driver = None
    
    try:
        options = setup_chrome_stealth()
        driver = webdriver.Chrome(options=options)
        remover_rastros_automacao(driver)
        
        url = f"https://www.catho.com.br/vagas/{LOCAL.replace(' ', '-').lower()}/?q=desenvolvedor"
        log_info(f"🔗 {url}")
        
        driver.get(url)
        time.sleep(random.uniform(4, 7))
        
        # Seletores Catho
        seletores = [
            "a[data-testid*='job']",
            ".job-card a",
            "[data-id*='job']",
            "a[href*='/vaga/']"
        ]
        
        vagas = []
        for seletor in seletores:
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
                if elementos:
                    vagas = elementos
                    log_info(f"🔍 {len(vagas)} vagas com: {seletor}")
                    break
            except:
                continue
        
        resultados = []
        for job in vagas[:6]:
            try:
                titulo = job.text.strip()
                link = job.get_attribute("href")
                
                if not titulo or len(titulo) < 5:
                    continue
                
                # Filtro TI
                termos_ti = ['ti', 'tecnologia', 'desenvolvedor', 'programador', 'analista', 'software', 'sistema', 'dev']
                if any(termo in titulo.lower() for termo in termos_ti):
                    resultados.append(f"**{titulo}**\n{link}")
                    log_success(f"✅ Catho: {titulo}")
                    
            except:
                continue
                
        return resultados
        
    except Exception as e:
        log_error(f"Erro Catho: {str(e)[:100]}...")
        return []
    finally:
        if driver:
            driver.quit()

# ===========================
# 🚀 ENVIAR DISCORD
# ===========================
def enviar_discord(vagas):
    if not vagas:
        log_info("📭 Nenhuma vaga para enviar")
        try:
            if DISCORD_WEBHOOK_URL:
                requests.post(DISCORD_WEBHOOK_URL, 
                            json={"content": f"🔍 Nenhuma vaga de TI encontrada em {LOCAL} na busca de hoje."}, 
                            timeout=10)
        except:
            pass
        return
        
    mensagem = f"🎯 **Vagas de TI em {LOCAL}**\n\n" + "\n\n".join(vagas[:8])
    
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": mensagem}, timeout=10)
        log_success("📤 Mensagem enviada para Discord!")
    except Exception as e:
        log_error(f"Erro Discord: {e}")

# ===========================
# 🧠 FUNÇÃO PRINCIPAL
# ===========================
def main():
    setup_logging()
    log_info("🚀 Iniciando busca de vagas...")
    
    if not DISCORD_WEBHOOK_URL:
        log_error("❌ Discord webhook não configurado")
        return
    
    # Busca em MÚLTIPLAS plataformas (fallbacks)
    log_info("🔄 Testando diferentes plataformas...")
    
    vagas_indeed = buscar_vagas_indeed()
    vagas_infojobs = buscar_vagas_infojobs()
    vagas_catho = buscar_vagas_catho()
    
    # Combina todos os resultados
    todas_vagas = vagas_indeed + vagas_infojobs + vagas_catho
    
    if todas_vagas:
        log_success(f"🎯 Total: {len(todas_vagas)} vagas encontradas")
        log_info(f"📊 Indeed: {len(vagas_indeed)} | InfoJobs: {len(vagas_infojobs)} | Catho: {len(vagas_catho)}")
        enviar_discord(todas_vagas)
    else:
        log_info("📭 Nenhuma vaga encontrada em nenhuma plataforma")
        enviar_discord([])
    
    log_success("🏁 Busca concluída!")

if __name__ == "__main__":
    main()
