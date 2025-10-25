# ===========================
# 📦 IMPORTAÇÕES
# ===========================
import os
import time
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
# 🛠️ CONFIGURAÇÃO CHROME
# ===========================
def setup_chrome():
    """Configuração para Chromium"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36")
    
    # Para Chromium
    options.binary_location = "/usr/bin/chromium-browser"
    
    return options

# ===========================
# 🔍 BUSCA INDEED MELHORADA
# ===========================
def buscar_vagas_indeed():
    log_info("🌐 Buscando no Indeed...")
    driver = None
    
    try:
        options = setup_chrome()
        driver = webdriver.Chrome(options=options)
        
        # URL melhorada
        url = f"https://br.indeed.com/jobs?q=desenvolvedor+programador+ti&l={LOCAL.replace(' ', '+')}"
        log_info(f"🔗 {url}")
        
        driver.get(url)
        
        # Espera mais inteligente
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".job_seen_beacon"))
        )
        
        time.sleep(3)
        
        # MÚLTIPLOS seletores para Indeed
        seletores_indeed = [
            "a.jcs-JobTitle",
            "[data-jk]",
            ".jobTitle",
            ".jcs-JobTitle",
            "a[data-jk]"
        ]
        
        vagas = []
        for seletor in seletores_indeed:
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
                if elementos:
                    vagas = elementos
                    log_info(f"🔍 {len(vagas)} vagas com: {seletor}")
                    break
            except:
                continue
        
        resultados = []
        for job in vagas[:8]:
            try:
                titulo = job.text.strip()
                link = job.get_attribute("href")
                
                if not titulo or not link:
                    continue
                    
                # Log para debug
                log_info(f"📌 Vaga: {titulo[:50]}...")
                
                # Filtro mais amplo
                termos_ti = ['ti', 'tecnologia', 'desenvolvedor', 'programador', 'analista', 'software', 'sistema', 'dev', 'web']
                titulo_lower = titulo.lower()
                
                if any(termo in titulo_lower for termo in termos_ti):
                    resultados.append(f"**{titulo}**\n{link}")
                    log_success(f"✅ Indeed: {titulo}")
                    
            except Exception as e:
                log_error(f"Erro vaga: {e}")
                continue
                
        return resultados
        
    except Exception as e:
        log_error(f"Erro Indeed: {e}")
        return []
    finally:
        if driver:
            driver.quit()

# ===========================
# 🔍 BUSCA GLASSDOOR MELHORADA
# ===========================
def buscar_vagas_glassdoor():
    log_info("🌐 Buscando no Glassdoor...")
    driver = None
    
    try:
        options = setup_chrome()
        driver = webdriver.Chrome(options=options)
        
        # URL mais simples
        url = f"https://www.glassdoor.com.br/Emprego/{LOCAL.replace(' ', '-')}-vagas-SRCH_IL.0,9_IC2348682.htm"
        log_info(f"🔗 {url}")
        
        driver.get(url)
        time.sleep(8)  # Mais tempo para carregar
        
        # MÚLTIPLOS seletores para Glassdoor
        seletores_glassdoor = [
            "a[data-test='job-link']",
            ".jobLink",
            "[data-test='job-title']",
            "a.jobLink",
            ".job-title",
            "a[href*='/job-listing/']"
        ]
        
        vagas = []
        for seletor in seletores_glassdoor:
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
                if elementos:
                    vagas = elementos
                    log_info(f"🔍 {len(vagas)} vagas com: {seletor}")
                    break
            except:
                continue
        
        # Se não encontrou, tenta buscar qualquer link que pareça vaga
        if not vagas:
            todos_links = driver.find_elements(By.CSS_SELECTOR, "a")
            for link in todos_links:
                href = link.get_attribute("href") or ""
                if "/job-listing/" in href or "/Vaga/" in href:
                    vagas.append(link)
            log_info(f"🔍 {len(vagas)} vagas encontradas por URL")
        
        resultados = []
        for job in vagas[:8]:
            try:
                titulo = job.text.strip()
                link = job.get_attribute("href")
                
                if not titulo or len(titulo) < 5:
                    continue
                    
                # Log para debug
                log_info(f"📌 Vaga Glassdoor: {titulo[:50]}...")
                
                # Garante link completo
                if link and link.startswith('/'):
                    link = f"https://www.glassdoor.com.br{link}"
                
                # Filtro mais amplo
                termos_ti = ['ti', 'tecnologia', 'desenvolvedor', 'programador', 'analista', 'software', 'sistema', 'dev']
                titulo_lower = titulo.lower()
                
                if any(termo in titulo_lower for termo in termos_ti):
                    resultados.append(f"**{titulo}**\n{link}")
                    log_success(f"✅ Glassdoor: {titulo}")
                    
            except Exception as e:
                log_error(f"Erro vaga Glassdoor: {e}")
                continue
                
        return resultados
        
    except Exception as e:
        log_error(f"Erro Glassdoor: {e}")
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
        # Envia mensagem informativa
        try:
            if DISCORD_WEBHOOK_URL:
                requests.post(DISCORD_WEBHOOK_URL, 
                            json={"content": f"🔍 Nenhuma vaga de TI encontrada em {LOCAL} hoje."}, 
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
    
    # Busca em ambas as plataformas
    vagas_indeed = buscar_vagas_indeed()
    vagas_glassdoor = buscar_vagas_glassdoor()
    
    # Combina resultados
    todas_vagas = vagas_indeed + vagas_glassdoor
    
    if todas_vagas:
        log_success(f"🎯 Total: {len(todas_vagas)} vagas encontradas")
        enviar_discord(todas_vagas)
    else:
        log_info("📭 Nenhuma vaga encontrada")
        enviar_discord([])  # Envia mensagem de "nenhuma vaga"
    
    log_success("🏁 Busca concluída!")

if __name__ == "__main__":
    main()
