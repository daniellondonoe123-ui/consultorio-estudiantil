import os
import streamlit as st
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
    st.error("Falta configurar la clave GEMINI_API_KEY en el sistema.")
    st.stop()

client = genai.Client(api_key=api_key)

# 3. Carga única del Manual de Convivencia en caché (Modo NotebookLM)
@st.cache_resource
def cargar_manual():
    ruta_pdf = "manual_convivencia.pdf"
    if not os.path.exists(ruta_pdf):
        return None
    return client.files.upload(file=ruta_pdf)

manual_pdf = cargar_manual()

if manual_pdf is None:
    st.warning("⚠️ Aún no se ha encontrado el archivo 'manual_convivencia.pdf' en la carpeta del proyecto.")
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

# 5. Procesamiento y protocolo de respuesta
if boton_consultar:
    if not nombre.strip() or not documento.strip() or not grado.strip() or not caso.strip():
        st.warning("⚠️ Por favor completa tu nombre, documento, grado/grupo y la descripción del caso.")
    elif not confirmacion:
        st.warning("⚠️ Marca la casilla de confirmación para generar la consulta.")
    else:
        with st.spinner("Consultando el Manual de Convivencia de la IE Ana Gómez de Sierra y la Ley 1620..."):
            instrucciones_sistema = """
            Eres el Asesor Jurídico y de Convivencia Escolar de la Institución Educativa Ana Gómez de Sierra.
            Tu objetivo es orientar a los estudiantes con un lenguaje claro, empático, sencillo y pedagógico.

            REGLA ESTRICTA DE FUENTES (MODO NOTEBOOKLM):
            - Para normas internas del colegio, usa ÚNICAMENTE el archivo PDF adjunto (Manual de Convivencia de la IE Ana Gómez de Sierra). Prohibido inventar artículos o sanciones que no estén en el PDF.
            - Prioriza en primer lugar el Manual de Convivencia adjunto y compleméntalo únicamente con la Constitución Política de Colombia vigente y la Ley 1620 de 2013 (y su Decreto Reglamentario 1965 de 2013).

            PROTOCOLO DE RESPUESTA OBLIGATORIO:
            Dirígete al estudiante por su nombre y responde usando exactamente estos 5 apartados:
            
            1. **Tipo de caso:** Explica de forma clara qué situación se presenta (conflicto interpersonal, agresión verbal/física/relacional, ciberacoso, reclamo académico, debido proceso, etc.).
            2. **Tipo de falta o situación:** Clasifícala según el Manual de Convivencia del colegio y la Ley 1620 (Situación Tipo I, Situación Tipo II, Situación Tipo III, o falta/situación académica). Explica por qué encaja en esa categoría.
            3. **Ley y normas que te respaldan:** Cita los artículos o capítulos específicos del Manual de Convivencia adjunto, junto con los artículos de la Ley 1620 de 2013 y de la Constitución Política de Colombia que amparan al estudiante.
            4. **¿Con quién debes acudir para escalar el caso?:** Indica claramente a qué figura escolar debe acudir (representante de grupo, personero estudiantil, docente de área, director de grupo, psicoorientación, coordinación, comité escolar de convivencia o rectoría).
            5. **Conducto regular paso a paso:**
               - **Qué debes hacer tú como estudiante:** Pasos concretos en orden cronológico.
               - **Qué debe hacer la institución:** Pasos y garantías del debido proceso que el colegio debe cumplir.
            """

            consulta_usuario = f"""
            Estudiante: {nombre}
            Documento: {documento}
            Grado/Grupo: {grado}
            Caso reportado: {caso}
            """

            respuesta = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[manual_pdf, consulta_usuario],
                config=types.GenerateContentConfig(
                    system_instruction=instrucciones_sistema,
                    temperature=0.0 # Cero creatividad para evitar que invente normas fuera de los documentos
                )
            )

            st.markdown("---")
            st.markdown(f"### 📄 Concepto de Orientación para {nombre} ({grado})")
            st.markdown(respuesta.text)