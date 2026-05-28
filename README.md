# Plan de Investigación: Métrica de Compatibilidad y Optimización de Edición de Documentos Ofimáticos

## 1. Contexto y Motivación

En entornos institucionales (universidades, entidades gubernamentales, empresas), los documentos ofimáticos se intercambian constantemente entre usuarios que utilizan distintas herramientas de software (Microsoft Word, LibreOffice Writer, Google Docs, etc.). Este intercambio genera **problemas de compatibilidad de formato**: tablas que se descuadran, estilos que se pierden, fuentes que cambian, numeración que se corrompe, entre otros.

Estos problemas tienen consecuencias concretas:

- **Tiempo perdido** en edición y corrección manual — tiempo cuyo costo varía significativamente según el perfil del usuario (personal administrativo vs. docente/investigador).
- **Costos de licenciamiento** elevados, ya que muchas instituciones pagan licencias de software propietario para evitar estos problemas.
- **Fricción en flujos de trabajo** administrativos y académicos, especialmente en procesos de transformación digital.

A pesar de lo extendido del problema, **no existe una métrica estandarizada** que permita cuantificar la compatibilidad de un documento ni evidencia sistemática sobre qué elementos de formato son los principales responsables.

---

## 2. Objetivo General

Evaluar la fricción y la pérdida de tiempo en la edición de documentos institucionales entre distintas plataformas, y desarrollar una **métrica de compatibilidad de formato** (escala 0–100) que permita diagnosticar los problemas actuales, proponer prácticas o formatos alternativos, y minimizar los costos asociados al uso de herramientas tradicionales.

---

## 3. Objetivos Específicos

1. Recopilar una muestra representativa de documentos institucionales reales, clasificados por tipo, complejidad y perfil de usuario.
2. Identificar los elementos de formato que causan mayor incompatibilidad entre plataformas ("la piedra en el zapato").
3. Cuantificar el tiempo y esfuerzo que distintos perfiles de usuario dedican a corregir problemas de formato, y estimar su costo económico.
4. Construir un índice numérico (0–100) que refleje el grado de compatibilidad de un documento dado al ser abierto en otra plataforma.
5. Proponer formatos o prácticas alternativas que maximicen la compatibilidad, o diseñar una capa intermedia de software que reduzca la fricción.
6. Evaluar si los resultados justifican un caso de negocio o emprendimiento viable.

---

## 4. Fases del Proyecto

### Fase 1 — Preparación y diseño del experimento (~Mes 1)

**Objetivo:** Establecer las bases metodológicas y reunir los insumos necesarios antes de ejecutar las pruebas.

**Actividades:**

- **Definición de la muestra documental:** Armar una red de contactos institucionales para obtener una muestra representativa de los tipos de documentos utilizados (memorandos, informes, formularios con tablas/celdas, oficios, actas, etc.). Clasificar por tipo y nivel de complejidad (texto simple → formularios complejos con "cajoncitos").
- **Análisis de herramientas actuales:** Mapear qué software utilizan actualmente los usuarios de la institución y en qué casos de uso (creación, edición, revisión, distribución).
- **Selección de participantes — Personal administrativo:** Reclutar secretarias y personal administrativo aprovechando los contactos existentes en el área de transformación digital. Este perfil representa al usuario frecuente con alta destreza en edición.
- **Selección de participantes — Perfiles académicos:** Incluir profesores e investigadores para contrastar la experiencia de edición y, crucialmente, **la diferencia en el costo económico del tiempo invertido** frente al personal administrativo.
- **Diseño del protocolo experimental:** Definir las tareas que realizarán los participantes, los documentos que editarán, las plataformas en las que lo harán, y los instrumentos de medición (cronómetro, grabación de pantalla, encuesta de percepción, etc.).
- **Gestión ética:** Tramitar la aprobación del comité de ética para experimentos con humanos. Preparar acuerdos de confidencialidad para los documentos institucionales.

**Entregables:**
- Muestra documental clasificada.
- Protocolo experimental aprobado.
- Lista de participantes confirmados.

---

### Fase 2 — Ejecución del experimento y recopilación de datos (~Mes 2)

**Objetivo:** Ejecutar las pruebas con usuarios reales y recopilar datos cuantitativos y cualitativos.

**Actividades:**

- **Pruebas de edición cruzada:** Entregar documentos a los participantes y pedirles que los abran y editen en una plataforma distinta a la original (ej. documento creado en Word → editado en LibreOffice, y viceversa).
- **Identificación de obstáculos:** Registrar sistemáticamente qué elementos específicos de formato se rompen o generan fricción en cada caso (tablas, estilos, numeración, imágenes, fuentes, encabezados/pies de página, campos de formulario, etc.).
- **Medición de tiempos de edición:** Cuantificar el tiempo exacto que cada usuario demora en completar las tareas de edición, distinguiendo entre tiempo productivo y tiempo dedicado a corregir problemas de formato.
- **Encuesta de percepción:** Recoger la experiencia subjetiva de los usuarios (¿qué fue lo más frustrante?, ¿qué tan difícil fue?, ¿usaría otra herramienta?).
- **Registro por perfil:** Asociar cada resultado al tipo de documento Y al perfil de usuario, para poder cruzar ambas variables en el análisis.

**Entregables:**
- Base de datos con registros de incompatibilidades por documento, plataforma y perfil de usuario.
- Tiempos de edición medidos.
- Encuestas de percepción completadas.

---

### Fase 3 — Análisis de resultados y propuesta técnica (~Mes 3)

**Objetivo:** Transformar los datos en conocimiento accionable: la métrica, el diagnóstico y la propuesta de solución.

**Actividades:**

- **Análisis cuantitativo:**
  - Ranking de los elementos de formato más problemáticos.
  - Comparación de tiempos de edición entre plataformas y entre perfiles de usuario.
  - Estimación del costo económico de la fricción (horas × costo/hora por perfil).
- **Construcción de la métrica de compatibilidad (0–100):**
  - Definir los criterios: fidelidad visual (cómo se ve) e integridad estructural (cómo se comporta el formato subyacente).
  - Ponderar los elementos según su impacto real medido en la Fase 2.
  - Validar la métrica contrastándola con la percepción de los usuarios.
- **Propuesta de solución:**
  - Identificar qué formatos o prácticas de formato minimizan los problemas detectados.
  - Evaluar la viabilidad de una capa intermedia de software que analice documentos, asigne su puntaje de compatibilidad, y sugiera correcciones.
  - Determinar el conjunto mínimo de elementos que un usuario debería evitar para garantizar compatibilidad.
- **Evaluación de mercado preliminar:** ¿Los datos muestran que el problema es lo suficientemente costoso como para que instituciones paguen por una solución?

**Entregables:**
- Informe de resultados con diagnóstico del problema.
- Métrica de compatibilidad documentada y validada.

## 5. Cronograma (Fase 1–3: ~3 meses)

| Semana | Actividad principal |
|---|---|
| 1–2 | Diseño del protocolo experimental. Gestión ética. |
| 3–4 | Recolección de muestra documental. Reclutamiento de participantes. |
| 5–6 | Ejecución de pruebas con personal administrativo. |
| 7–8 | Ejecución de pruebas con profesores. Registro de datos. |
| 9–10 | Análisis cuantitativo. Construcción de la métrica. |
| 11–12 | Propuesta técnica. Informe final. |

---
