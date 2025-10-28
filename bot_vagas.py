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
# 📍 VALIDAÇÃO DE LOCALIZAÇÃO
# ===========================
def validar_localizacao(titulo, link=""):
    """Valida se a vaga é de Salvador/BA ou remota"""
    texto_completo = f"{titulo} {link}".lower()
    
    # Localizações ACEITAS
    locais_aceitos = [
        'salvador', 'bahia', 'ba',
        'remoto', 'remota', 'home office', 'homeoffice',
        'anywhere', 'qualquer lugar', 'todo brasil'
    ]
    
    # Localizações REJEITADAS (outras cidades/estados)
    locais_rejeitados = [
        'curitiba', 'paraná', 'pr',
        'são paulo', 'sp', 'paulista',
        'rio de janeiro', 'rj',
        'belo horizonte', 'minas', 'mg',
        'brasília', 'df',
        'porto alegre', 'rs',
        'florianópolis', 'sc',
        'recife', 'pe',
        'fortaleza', 'ce',
        'goiânia', 'go'
    ]
    
    # Se menciona cidade rejeitada, bloquear
    if any(local in texto_completo for local in locais_rejeitados):
        return False
    
    # Se não menciona localização OU menciona Salvador/remoto, aceitar
    tem_localizacao_aceita = any(local in texto_completo for local in locais_aceitos)
    tem_localizacao_qualquer = any(local in texto_completo for local in locais_rejeitados + locais_aceitos)
    
    # Se não tem nenhuma localização mencionada OU tem Salvador/remoto, aceita
    return not tem_localizacao_qualquer or tem_localizacao_aceita


# ===========================
# 🎯 FILTRO DE VAGAS
# ===========================
def filtrar_vaga_ti(titulo, site_nome=""):
    """Filtro RIGOROSO - apenas vagas de TI"""
    if not titulo or len(titulo) < 8:
        return False
    
    titulo_lower = titulo.lower()
    
    # ❌ REJEITAR textos de interface/menu/cookies
    textos_interface = [
        'cookie', 'consentimento', 'não venda', 'privacidade',
        'termos', 'política', 'ajuda', 'sobre', 'contato',
        'login', 'cadastr', 'entrar', 'sair', 'perfil',
        'notificações', 'configurações', 'salvar', 'favoritar'
    ]
    
    if any(texto in titulo_lower for texto in textos_interface):
        return False
    
    # ❌ REJEITAR IMEDIATAMENTE áreas não-TI
    areas_nao_ti = [
        # Outras áreas
        'marketing', 'vendas', 'comercial', 'representante',
        'administrativo', 'administração', 'secretária', 'recepcion',
        'financeiro', 'contábil', 'contabil', 'fiscal',
        'recursos humanos', 'rh ', 'recrutador', 'aquisição de talentos',
        'farmacêutico', 'farmaceutico', 'enfermeiro', 'médico',
        'professor', 'educador', 'pedagogo',
        'arquivologia', 'licitações', 'suprimentos',
        
        # Engenharias NÃO relacionadas a TI
        'engenharia civil', 'engenharia ambiental', 'engenharia química',
        'engenharia mecânica', 'engenharia elétrica', 'engenharia produção',
        'ambiental', 'civil', 'mecânica', 'química'
    ]
    
    # Se menciona área não-TI, rejeitar (MESMO QUE tenha "tecnologia" no nome)
    if any(area in titulo_lower for area in areas_nao_ti):
        return False
    
    # ✅ PALAVRAS-CHAVE OBRIGATÓRIAS DE TI (precisa ter pelo menos UMA)
    palavras_ti_obrigatorias = [
        # TI Geral
        'ti ', ' ti', 'tecnologia informação', 'tecnologia da informação',
        'tech ', 'tecnologia',
        
        # Desenvolvimento
        'desenvolvedor', 'developer', 'programador', 'programação',
        'software', 'sistema', 'web', 'mobile', 'app',
        
        # Linguagens/Tecnologias
        'java', 'python', 'javascript', 'php', 'c#', '.net', 'node',
        'react', 'angular', 'vue', 'sql', 'database',
        
        # Infraestrutura
        'suporte técnico', 'help desk', 'service desk', 'infraestrutura',
        'redes', 'cloud', 'devops', 'sysadmin',
        
        # Dados
        'dados', 'data', 'bi ', 'analytics', 'big data',
        
        # Outros
        'qa', 'tester', 'ux', 'ui', 'scrum master', 'product owner',
        'cyber', 'segurança informação'
    ]
    
    tem_palavra_ti = any(palavra in titulo_lower for palavra in palavras_ti_obrigatorias)
    
    if not tem_palavra_ti:
        return False
    
    # ❌ Rejeitar cargos sênior/gerenciais
    cargos_senior = [
        'sênior', 'senior', 'sr.', 'sr ', ' sr',
        'coordenador', 'gerente', 'diretor', 'supervisor',
        'tech lead', 'principal', 'head', 'chief'
    ]
    
    if any(cargo in titulo_lower for cargo in cargos_senior):
        return False
    
    return True

# ===========================
# 🔍 BUSCA GENÉRICA
# ===========================
def buscar_vagas_site(site_nome, url_template, xpaths, termo_busca, wait_time=5):
    """Função genérica para buscar em qualquer site"""
    driver = None
    
    try:
        options = ChromeOptions()
        options.binary_location = "/usr/bin/google-chrome-stable"
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
        
        # ✅ TENTAR MÚLTIPLOS XPaths até encontrar
        vagas = []
        for xpath in xpaths:
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located((By.XPATH, xpath))
                )
                elementos = driver.find_elements(By.XPATH, xpath)
                if elementos and len(elementos) > 2:
                    log_info(f"✓ {site_nome}: {len(elementos)} elementos com XPath: {xpath[:50]}...")
                    vagas = elementos
                    break
            except:
                continue
        
        # ✅ SE NÃO ENCONTROU, tentar buscar TODOS os links
        if not vagas:
            log_info(f"⚠ {site_nome}: Tentando busca genérica de links...")
            try:
                todos_links = driver.find_elements(By.TAG_NAME, "a")
                # Filtrar apenas links que parecem ser de vagas
                vagas = [link for link in todos_links if link.get_attribute("href") and len(link.text.strip()) > 10]
                if vagas:
                    log_info(f"✓ {site_nome}: {len(vagas)} links encontrados (busca genérica)")
            except:
                pass
        
        if not vagas:
            log_info(f"⚠ {site_nome}: Nenhum elemento encontrado")
            return []
        
        resultados = []
        vagas_vistas = set()
        
        for job in vagas[:30]:
    try:
        titulo = job.text.strip()
        link = job.get_attribute("href")
        
        if not titulo or len(titulo) < 8 or not link:
            continue
        
        # ✅ IGNORAR links de navegação/interface
        links_ignorar = [
            'javascript:', '#', 'mailto:', 'tel:',
            '/sobre', '/contato', '/ajuda', '/termos',
            '/politica', '/privacidade', '/login', '/cadastro'
        ]
        
        if any(ignorar in link.lower() for ignorar in links_ignorar):
            continue
        
        # ✅ Link deve ser de vaga (conter palavras-chave)
        palavras_url_vaga = ['job', 'vaga', 'emprego', 'oportunidade', 'career']
        
        if site_nome != "Catho":  # Catho tem URLs diferentes
            if not any(palavra in link.lower() for palavra in palavras_url_vaga):
                continue
        
        # Evitar duplicatas
        if titulo in vagas_vistas:
            continue
        
        # ✅ Título deve ter tamanho razoável (vagas reais)
        if len(titulo) < 10 or len(titulo) > 150:
            continue
        
        # ✅ APLICAR FILTROS
        if filtrar_vaga_ti(titulo, site_nome):
            if validar_localizacao(titulo, link):
                resultados.append(f"**{titulo}**\n{link}")
                vagas_vistas.add(titulo)
                log_success(f"{site_nome}: {titulo[:60]}...")
            else:
                log_info(f"🚫 {site_nome}: Localização incorreta - {titulo[:60]}...")
        
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
    # LINKEDIN - Formato: ?keywords=TERMO&location=Salvador
    # ===========================
    if SITES_ATIVOS['linkedin']:
        log_info("🌐 Buscando no LinkedIn...")
       xpaths_linkedin = [
    "//a[contains(@href, '/jobs/view/')]",
    "//div[contains(@class, 'base-card')]//a[contains(@href, '/jobs/')]",
    "//li[contains(@class, 'jobs-search')]//a[contains(@href, '/jobs/')]"
    # ❌ Remover //a genérico
]
        
        for termo in TERMOS_BUSCA[:2]:
            # LinkedIn: keywords + location + geoId
            termo_encoded = termo.replace(' ', '%20')
            url_linkedin = f"https://www.linkedin.com/jobs/search/?keywords={termo_encoded}&location=Salvador%2C%20Bahia%2C%20Brazil&geoId=103644718&f_TPR=r604800"
            vagas = buscar_vagas_site("LinkedIn", url_linkedin, xpaths_linkedin, termo, wait_time=6)
            todas_vagas.extend(vagas)
            time.sleep(random.uniform(5, 8))
        
        log_info(f"📊 LinkedIn: {len([v for v in todas_vagas])} vagas")
    
    # ===========================
    # GLASSDOOR - Formato: /salvador-TERMO-vagas
    # ===========================
    if SITES_ATIVOS['glassdoor']:
        log_info("🌐 Buscando no Glassdoor...")
        xpaths_glassdoor = [
    "//a[contains(@data-test, 'job-link')]",
    "//a[contains(@href, '/job-listing/')]",
    "//a[contains(@class, 'JobCard')]",
    "//article[contains(@id, 'job')]//a"
    # ❌ Remover //a genérico
]
        
        count_inicial = len(todas_vagas)
        for termo in TERMOS_BUSCA[:2]:
            # Glassdoor: /Vaga/salvador-TERMO-vagas
            termo_formatado = termo.replace(' ', '-').lower()
            url_glassdoor = f"https://www.glassdoor.com.br/Vaga/salvador-{termo_formatado}-vagas-SRCH_IL.0,8_IC2613892_KO9.htm"
            vagas = buscar_vagas_site("Glassdoor", url_glassdoor, xpaths_glassdoor, termo, wait_time=7)
            todas_vagas.extend(vagas)
            time.sleep(random.uniform(6, 9))
        
        log_info(f"📊 Glassdoor: {len(todas_vagas) - count_inicial} vagas")
    
    # ===========================
    # CATHO - Formato: /vagas/TERMO/salvador-ba
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
            # Catho: /vagas/TERMO/salvador-ba
            termo_formatado = termo.replace(' ', '-').lower()
            url_catho = f"https://www.catho.com.br/vagas/{termo_formatado}/salvador-ba"
            vagas = buscar_vagas_site("Catho", url_catho, xpaths_catho, termo, wait_time=5)
            todas_vagas.extend(vagas)
            time.sleep(random.uniform(3, 5))
        
        log_info(f"📊 Catho: {len(todas_vagas) - count_inicial} vagas")
    
    # ===========================
    # INFOJOBS - Formato: /TERMO-em-salvador-ba
    # ===========================
    if SITES_ATIVOS['infojobs']:
        log_info("🌐 Buscando no InfoJobs...")
        xpaths_infojobs = [
    "//a[contains(@class, 'js-o-link')]",
    "//a[contains(@href, '/vaga.xhtml')]",
    "//div[contains(@class, 'element-vaga')]//a",
    "//article[contains(@class, 'vaga')]//a"
    # ❌ Remover //a genérico
]
        
        count_inicial = len(todas_vagas)
        for termo in TERMOS_BUSCA[:2]:
            # InfoJobs: /emprego-TERMO-em-salvador-ba
            termo_formatado = termo.replace(' ', '-').lower()
            url_info = f"https://www.infojobs.com.br/empregos-{termo_formatado}-em-salvador-ba.aspx"
            vagas = buscar_vagas_site("InfoJobs", url_info, xpaths_infojobs, termo, wait_time=5)
            todas_vagas.extend(vagas)
            time.sleep(random.uniform(3, 5))
        
        log_info(f"📊 InfoJobs: {len(todas_vagas) - count_inicial} vagas")
    
    # Remover duplicatas finais
    vagas_unicas = list(dict.fromkeys(todas_vagas))
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
    
    LIMITE_DISCORD = 1900  # Margem de segurança (Discord permite 2000)
    
    mensagem_header = f"🎯 **{len(vagas)} Vagas de TI em {LOCAL}**\n"
    mensagem_header += f"📅 {time.strftime('%d/%m/%Y às %H:%M')}\n"
    mensagem_header += "─" * 50 + "\n\n"
    
    try:
        # Primeira mensagem
        mensagem_atual = mensagem_header
        vagas_na_mensagem = []
        lote = 1
        
        for i, vaga in enumerate(vagas):
            vaga_formatada = f"{vaga}\n\n"
            
            # Se adicionar essa vaga ultrapassar o limite, enviar mensagem atual
            if len(mensagem_atual + vaga_formatada) > LIMITE_DISCORD:
                # Enviar mensagem atual
                requests.post(DISCORD_WEBHOOK_URL, json={"content": mensagem_atual}, timeout=10)
                log_success(f"📤 Lote {lote} enviado! ({len(vagas_na_mensagem)} vagas)")
                
                # Preparar próxima mensagem
                time.sleep(2)
                lote += 1
                mensagem_atual = f"📋 **Continuação (Lote {lote}):**\n\n{vaga_formatada}"
                vagas_na_mensagem = [vaga]
            else:
                # Adicionar vaga à mensagem atual
                mensagem_atual += vaga_formatada
                vagas_na_mensagem.append(vaga)
        
        # Enviar última mensagem (se houver vagas restantes)
        if vagas_na_mensagem:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": mensagem_atual}, timeout=10)
            log_success(f"📤 Lote {lote} enviado! ({len(vagas_na_mensagem)} vagas)")
            
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




