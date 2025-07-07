# 🏢 Configuración del Logo de Allianz

## 📋 Instrucciones para agregar el logo

### 1. **Ubicación del Logo**
Coloca tu archivo de logo de Allianz en una de estas ubicaciones:

```
BDP_2025/
├── allianz-logo.png          ← OPCIÓN 1 (Recomendado)
├── assets/
│   ├── allianz-logo.png      ← OPCIÓN 2
│   └── allianz_logo.png      ← OPCIÓN 3
```

### 2. **Formatos Soportados**
- ✅ **PNG** (Recomendado para transparencia)
- ✅ **JPG/JPEG** (Para archivos más pequeños)
- ✅ **SVG** (Para calidad vectorial)

### 3. **Especificaciones del Logo**
- **Tamaño recomendado:** 200x80 píxeles
- **Resolución:** 300 DPI (para calidad alta)
- **Fondo:** Transparente (PNG) o blanco
- **Formato:** Horizontal preferible

### 4. **Nombres de Archivo Aceptados**
La aplicación buscará automáticamente estos nombres:
- `allianz-logo.png`
- `assets/allianz-logo.png`
- `assets/allianz_logo.png`

### 5. **Verificación**
Una vez colocado el logo, la aplicación:
- ✅ Detectará automáticamente el archivo
- ✅ Lo mostrará en el header corporativo
- ✅ Aplicará el estilo corporativo de Allianz

### 6. **Fallback**
Si no encuentra el logo:
- 🔄 Mostrará el texto "Allianz" estilizado
- 🔄 Mantendrá el branding corporativo
- 🔄 Funcionará completamente sin problemas

## 🎨 Branding Aplicado

### **Colores Corporativos:**
- **Azul Principal:** #0066cc
- **Azul Oscuro:** #003366
- **Azul Claro:** #e8f4ff
- **Gris:** #f8f9fa
- **Blanco:** #ffffff

### **Elementos de Branding:**
- ✅ Header corporativo con gradiente
- ✅ Botones con colores Allianz
- ✅ Tarjetas de resultados estilizadas
- ✅ Sidebar con tema corporativo
- ✅ Métricas con estilo profesional

## 📝 Ejemplo de Uso

```bash
# Copiar logo a la raíz del proyecto
cp mi-logo-allianz.png BDP_2025/allianz-logo.png

# O copiar a la carpeta assets
cp mi-logo-allianz.png BDP_2025/assets/allianz-logo.png

# Ejecutar la aplicación
streamlit run streamlit_app.py
```

## 🔧 Personalización Adicional

Si necesitas personalizar más elementos:

1. **Colores:** Modifica las variables CSS en `app/streamlit_app.py`
2. **Tema:** Edita `.streamlit/config.toml`
3. **Estilos:** Ajusta las clases CSS en el archivo principal

---

**✅ ¡Listo! Tu aplicación tendrá el branding corporativo de Allianz** 