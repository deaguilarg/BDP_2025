# 🌐 Guía de Deployment Público - Asistente de Seguros Allianz

## 🚀 Streamlit Community Cloud (RECOMENDADO)

### **Preparación (5 minutos)**

1. **Asegurar el repositorio:**
   - ✅ Confirma que no hay API keys hardcodeadas
   - ✅ Push todos los cambios a GitHub
   - ✅ Repositorio debe ser público o tienes Streamlit Pro

2. **Datos necesarios:**
   - URL del repositorio: `https://github.com/deaguilarg/BDP_2025`
   - Archivo principal: `app/streamlit_app.py`
   - Rama: `master`

### **Configuración en Streamlit Cloud**

1. **Crear cuenta:**
   - Ve a: https://share.streamlit.io/
   - Conecta con tu cuenta de GitHub

2. **Deploy aplicación:**
   - Clic en "New app"
   - Repository: `deaguilarg/BDP_2025`
   - Branch: `master`
   - Main file path: `app/streamlit_app.py`

3. **Configurar variables de entorno:**
   ```
   OPENAI_API_KEY = tu-api-key-aqui
   ```

4. **Deploy:** Clic en "Deploy!"

### **URL Resultante:**
Tu aplicación estará en: `https://bdp-2025-asistente-seguros.streamlit.app/`

---

## ⚡ Alternativas Rápidas

### **Option A: Railway**
```bash
# 1. Instalar Railway CLI
npm install -g @railway/cli

# 2. Login y deploy
railway login
railway init
railway up
```

### **Option B: Render**
1. Conecta tu repositorio en: https://render.com/
2. Configura como "Web Service"
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `streamlit run app/streamlit_app.py --server.port $PORT`

---

## 🔐 Configuración de Seguridad (IMPORTANTE)

### **Para Uso Interno (Empresa):**
```python
# En streamlit_app.py - agregar autenticación simple
import streamlit_authenticator as stauth

# Configurar usuarios autorizados
names = ['Juan Pérez', 'María García']
usernames = ['jperez', 'mgarcia']
passwords = ['password1', 'password2']  # Usar hashing en producción

authenticator = stauth.Authenticate(names, usernames, passwords, 'some_cookie_name', 'some_signature_key')
name, authentication_status, username = authenticator.login('Login', 'main')

if authentication_status == False:
    st.error('Username/password is incorrect')
    st.stop()
elif authentication_status == None:
    st.warning('Please enter your username and password')
    st.stop()
```

### **Para Uso Público:**
- Implementar sistema donde cada usuario ingresa su propia API key
- Considerar un backend proxy que maneje las API keys
- Implementar rate limiting

---

## 📊 Monitoreo y Métricas

### **Streamlit Cloud:**
- Analytics básicos incluidos
- Logs limitados en plan gratuito

### **Métricas a Monitorear:**
- Número de consultas diarias
- Costo de API de OpenAI
- Usuarios activos
- Errores de aplicación

---

## 💰 Costos Estimados

### **Streamlit Community Cloud:**
- **Gratis** hasta 3 apps
- Limitaciones: 1GB RAM, suspensión tras inactividad

### **OpenAI API:**
- **GPT-3.5-turbo**: ~$0.002 por 1K tokens
- **Estimación**: $5-20/mes para uso moderado empresarial
- **⚠️ RIESGO**: Uso público sin límites puede generar costos altos

### **Planes Pagos:**
- **Streamlit Pro**: $20/mes - Sin límites, más recursos
- **Heroku**: $7-25/mes según recursos
- **Railway**: $5-20/mes según uso

---

## 🚨 Checklist Pre-Deployment

### **Seguridad:**
- [ ] No hay API keys hardcodeadas
- [ ] Variables de entorno configuradas
- [ ] .gitignore actualizado
- [ ] Autenticación implementada (si es necesario)

### **Funcionalidad:**
- [ ] Aplicación funciona localmente
- [ ] Todos los requirements están en requirements.txt
- [ ] Manejo de errores implementado
- [ ] Datos de prueba disponibles

### **Performance:**
- [ ] Índices FAISS generados
- [ ] Archivos grandes en .gitignore
- [ ] Caching implementado (@st.cache_data)

---

## 🔧 Solución de Problemas de Deployment

### **Error: "Module not found"**
- Verifica requirements.txt
- Algunas librerías requieren versiones específicas en la nube

### **Error: "Memory limit exceeded"**
- Reduce el tamaño del índice FAISS
- Usa @st.cache_data para componentes pesados
- Considera un plan pagado

### **Error: "API key not found"**
- Verifica configuración de variables de entorno
- Revisa que la variable se llame exactamente "OPENAI_API_KEY"

### **Aplicación muy lenta:**
- Implementa caching agresivo
- Reduce el número de documentos indexados
- Optimiza queries de embedding

---

## 🎯 Recomendaciones Finales

### **Para Demo/Presentación:**
- Usar Streamlit Community Cloud
- Configurar autenticación simple
- Preparar datos de ejemplo

### **Para Producción Empresarial:**
- Considerar Heroku/Railway/Azure
- Implementar autenticación robusta
- Configurar monitoreo de costos
- Backup de datos y configuraciones

### **Para Uso Público Masivo:**
- Backend separado con API keys
- Rate limiting por usuario
- Sistema de facturación si es necesario
- Infraestructura escalable (AWS/GCP/Azure)

---

**¿Listo para hacer el deployment? Sigue estos pasos y tu aplicación estará online en minutos! 🚀** 