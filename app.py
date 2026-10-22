import os
from pathlib import Path
import streamlit as st
from pypdf import PdfReader
from google import genai
from google.genai import types

# 1. Configuración visual de la página
st.set_page_config(
    page_title="Asesor Escolar - IE Ana Gómez de Sierra",
    page_icon="⚖️",
    layout="centered"
)

st.title("⚖️ Consultor de Convivencia Escolar")
st.subheader("Institución Educativa Ana Gómez de Sierra")
st.markdown(
    "Esta herramienta te explica tus derechos, deberes y el paso a paso que debes seguir "
    "ante cualquier situación escolar, basándose **únicamente** en el Manual de Convivencia "
    "del colegio, la Ley 1620 de 2013 y la Constitución Política de Colombia."
)

# 2. Conexión con Gemini API
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("Falta configurar la clave GEMINI_API_KEY en Settings -> Secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

# 3. Extracción de texto del Manual de Convivencia (rápido, sin expiración y ahorra tokens)
ruta_pdf = Path(__file__).parent / "manual_convivencia.pdf"

if not ruta_pdf.exists():
    st.warning("⚠️ Aún no se ha encontrado el archivo 'manual_convivencia.pdf' en la carpeta del proyecto.")
    st.stop()

@st.cache_resource
def extraer_texto_manual(ruta):
    lector = PdfReader(str(ruta))
    texto_completo = []
    for num_pagina, pagina in enumerate(lector.pages, start=1):
        texto_pagina = pagina.extract_text()
        if texto_pagina:
            texto_completo.append(f"--- PÁGINA {num_pagina} ---\n{texto_pagina}")
    return "\n".join(texto_completo)

texto_manual = extraer_texto_manual(ruta_pdf)

if not texto_manual.strip():
    st.error("⚠️ El PDF parece estar escaneado como imagen sin texto seleccionable. Usa un PDF con texto reconocible.")
    st.stop()

# 4. Formulario de operación para el estudiante
with st.form("consulta_estudiante"):
    st.markdown("### 1. Identificación del estudiante")
    col1, col2 = st.columns(2)
    with col1:
        nombre = st.text_input("Nombre completo *")
        documento = st.text_input("Número de documento (T.I. / C.C.) *")
    with col2:
        grado = st.text_input("Grado y grupo (Ej: 6°A, 9°B, 11°A) *")
        confirmacion = st.checkbox("Comprendo que esta consulta es una orientación pedagógica.")

    st.markdown("### 2. Describe tu caso")
    caso = st.text_area(
        "Explica con tus palabras qué pasó, quiénes estuvieron involucrados y qué necesitas saber: *",
        height=160,
        placeholder="Escribe aquí los detalles de la situación..."
    )

    boton_consultar = st.form_submit_button("Consultar orientación jurídica ⚖️")

# 5. Procesamiento y protocolo de respuesta con autodetección de modelos
if boton_consultar:
    if not nombre.strip() or not documento.strip() or not grado.strip() or not caso.strip():
        st.warning("⚠️ Por favor completa tu nombre, documento, grado/grupo y la descripción del caso.")
    elif not confirmacion:
        st.warning("⚠️ Marca la casilla de confirmación para generar la consulta.")
    else:
        instrucciones_sistema = """
        Eres el Asesor Jurídico y de Convivencia Escolar de la Institución Educativa Ana Gómez de Sierra.
        Tu objetivo es orientar a los estudiantes con un lenguaje claro, empático, sencillo y pedagógico.

        REGLA ESTRICTA DE FUENTES (MODO NOTEBOOKLM):
        - Para normas internas del colegio, usa ÚNICAMENTE el texto del Manual de Convivencia de la IE Ana Gómez de Sierra suministrado. Prohibido inventar artículos, numerales o sanciones que no aparezcan allí.
        - Prioriza el Manual de Convivencia y compleméntalo únicamente con la Constitución Política de Colombia vigente y la Ley 1620 de 2013 (y su Decreto Reglamentario 1965 de 2013).

        PROTOCOLO DE RESPUESTA OBLIGATORIO:
        Dirígete al estudiante por su nombre y responde usando exactamente estos 5 apartados:
        
        1. **Tipo de caso:** Explica de forma clara qué situación se presenta.
        2. **Tipo de falta o situación:** Clasifícala según el Manual de Convivencia del colegio y la Ley 1620 (Tipo I, II, III o académica).
        3. **Ley y normas que te respaldan:** Cita los artículos específicos del Manual de Convivencia, Ley 1620 y Constitución Política.
        4. **¿Con quién debes acudir para escalar el caso?:** Indica claramente a qué figura escolar debe acudir.
        5. **Conducto regular paso a paso:**
           - **Qué debes hacer tú como estudiante:** Pasos en orden cronológico.
           - **Qué debe hacer la institución:** Pasos y garantías del debido proceso.
        """

        prompt_completo = f"""
        === MANUAL DE CONVIVENCIA IE ANA GÓMEZ DE SIERRA ===
        {texto_manual}
        ====================================================

        DATOS DE LA CONSULTA DEL ESTUDIANTE:
        - Estudiante: {nombre}
        - Documento: {documento}
        - Grado/Grupo: {grado}
        - Caso reportado: {caso}
        """

        st.markdown("---")
        st.markdown(f"### 📄 Concepto de Orientación para {nombre} ({grado})")

        def flujo_respuesta():
            import time
            
            # 1. Consultar automáticamente a Google qué modelos existen en tu cuenta
            try:
                todos = [
                    m.name.replace("models/", "")
                    for m in client.models.list()
                    if "gemini" in m.name.lower()
                    and not any(x in m.name.lower() for x in ["embedding", "imagen", "veo", "aqa", "tts", "audio", "vision", "1.5", "2.5"])
                ]
                # Priorizar modelos flash y flash-lite (más rápidos y con cupo separado)
                modelos_flash = [m for m in todos if "flash" in m]
                 otros_modelos = [m for m in todos if "flash" not in m]
                modelos = modelos_flash + otros_modelos
            except Exception:
                modelos = ["gemini-3.8-flash-lite", "gemini-3.8-flash", "gemini-3.8-pro"]

            ultimo_error = ""
            
            # 2. Probar cada modelo disponible hasta que uno responda con cupo libre
            for modelo_actual in modelos:
                try:
                    stream = client.models.generate_content_stream(
                        model=modelo_actual,
                        contents=prompt_completo,
                        config=types.GenerateContentConfig(
                            system_instruction=instrucciones_sistema,
                            temperature=0.0
                        )
                    )
                    for pedazo in stream:
                        if pedazo.text:
                            yield pedazo.text
                    return  # Terminó con éxito
                except Exception as e:
                    ultimo_error = f"[{modelo_actual}] {e}"
                    time.sleep(1)
                    continue
            
            yield f"⚠️ No fue posible conectar tras probar los modelos disponibles ({', '.join(modelos)}). Último error: {ultimo_error}"

        with st.spinner("Analizando tu caso con el Manual de Convivencia..."):
            st.write_stream(flujo_respuesta)
