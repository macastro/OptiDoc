# Plan de Investigación: Métrica de Compatibilidad y Optimización de Edición de Documentos Ofimáticos

## 1. Contexto y Motivación

En entornos institucionales (universidades, entidades gubernamentales, empresas), los documentos ofimáticos se intercambian constantemente entre usuarios que emplean distintas herramientas de software (Microsoft Word, LibreOffice Writer, Google Docs, entre otras). Este intercambio genera problemas de compatibilidad de formato: tablas que se descuadran, estilos que se pierden, fuentes que se sustituyen y numeraciones que se corrompen.

Estos problemas tienen consecuencias concretas:

- **Tiempo perdido** en edición y corrección manual, cuyo costo varía significativamente según el perfil del usuario (personal administrativo vs. docente/investigador).
- **Costos de licenciamiento** elevados, pues muchas instituciones mantienen licencias de software propietario en parte para evitar estos problemas.
- **Fricción en flujos de trabajo** administrativos y académicos, especialmente en procesos de transformación digital.

La relevancia del problema se observa en las grandes migraciones del sector público hacia software libre por motivos de soberanía digital y reducción de costos (ver Sección 2). En ESPOL, donde conviven herramientas propietarias, software libre y servicios en la nube, el costo de la fricción de formato sigue siendo, en gran medida, invisible y no cuantificado.

A pesar de lo extendido del problema, no existe una métrica estandarizada que permita cuantificar la compatibilidad de un documento, ni evidencia sistemática sobre qué elementos de formato son los principales responsables de la pérdida de fidelidad.

## 2. Antecedentes y trabajos relacionados

La migración entre suites ofimáticas se ha estudiado principalmente desde la perspectiva del costo total de propiedad (TCO) y de casos de migración en el sector público, más que desde la productividad o la fidelidad de formato medida de forma objetiva.

***Investigación académica.*** El trabajo de Rossi, Scotto, Sillitti y Succi (2006) es uno de los estudios empíricos más citados sobre la migración a OpenOffice.org en una administración pública: compara su uso frente a Microsoft Office y analiza el impacto en la productividad de los empleados. Estudios complementarios sobre administraciones europeas documentan tanto razones de adopción como de no adopción (Ven, Van Nuffel y Verelst, 2006; Huysmans, Ven y Verelst, 2008) y señalan de forma recurrente el intercambio de archivos con terceros como un punto crítico.

***Casos de migración a gran escala.*** El proyecto LibreDifesa del Ministerio de Defensa de Italia proyectó ahorros de entre 26 y 29 millones de euros migrando más de 100 000 equipos a LibreOffice, y reportó ausencia de problemas graves tras las primeras estaciones migradas. Más recientemente, el estado alemán de Schleswig-Holstein migra alrededor de 30 000 equipos desde Windows y Microsoft Office hacia Linux y LibreOffice, adoptando el Formato de Documento Abierto (ODF) como estándar oficial, con la soberanía digital como principal motivación.

***La brecha en la literatura.*** Lo que estos trabajos miden y lo que omiten revela una oportunidad clara:

| Lo que se estudia | Lo que falta |
| --- | --- |
| Costo total de propiedad y licencias | Experimentos controlados de productividad |
| Encuestas de satisfacción de usuarios | Medición objetiva de la pérdida de fidelidad |
| Reportes de casos de migración | Impacto de la fidelidad de formato en el flujo de trabajo |
| Listas de características (feature checklists) | Una métrica estandarizada de compatibilidad |

En particular, la fidelidad de formato —el esfuerzo de reformateo al cambiar de herramienta— suele tratarse como un "problema de compatibilidad" cualitativo y no como un costo cuantificable. Esa ausencia es, precisamente, el aporte que este proyecto busca atender.

## 3. Objetivo General

Desarrollar y validar una métrica de compatibilidad de formato (escala 0–100) que diagnostique de forma objetiva y reproducible la pérdida de fidelidad de un documento ofimático al abrirse o editarse en una plataforma distinta a la original, complementada con una estimación de la fricción y del tiempo de edición asociados, con el fin de identificar los elementos de formato más problemáticos y proponer prácticas o una capa de software que minimicen dichos costos.

## 4. Objetivos Específicos

1. Construir un corpus representativo de documentos institucionales reales, clasificados por tipo y complejidad (de texto simple a formularios con celdas y campos).
2. Implementar un pipeline semiautomático que, mediante conversión entre formatos y comparación origen–destino, mida la pérdida de fidelidad de cada documento sin requerir intervención humana intensiva.
3. Construir un índice compuesto de compatibilidad (0–100) que pondere los elementos de formato según su impacto medido.
4. Calibrar y validar la métrica contra una medición del tiempo de edición realizada por un grupo reducido de usuarios de distintos perfiles.
5. Identificar los elementos de formato que causan mayor incompatibilidad ("la piedra en el zapato") y el conjunto mínimo de elementos a evitar para garantizar compatibilidad.
6. Proponer formatos o prácticas alternativas y evaluar la viabilidad de una capa intermedia de software que asigne el puntaje y sugiera correcciones.
7. Evaluar si los resultados justifican un caso de negocio o emprendimiento viable.

## 5. Enfoque metodológico

La principal observación del tutor —evitar depender de una colaboración humana extensa para medir— guía el diseño. El núcleo del proyecto es un pipeline computacional, reproducible y ejecutable por una sola persona, que mide la fidelidad de formato a escala. La participación humana se reduce a un rol de calibración y validación, con un número pequeño de participantes y tareas acotadas. Este enfoque disminuye el riesgo de cronograma, simplifica la gestión ética y hace el proyecto viable dentro de un semestre.

El pipeline combina dos momentos:

***(a) Predicción previa (antes de convertir).*** Inventario automático de las características del documento de origen (tablas, estilos, fuentes, encabezados/pies, campos de formulario, objetos incrustados, control de cambios, etc.) mediante librerías como python-docx o Apache POI, contrastado con una matriz de compatibilidad de LibreOffice respecto a OOXML. El resultado es un puntaje de esfuerzo previsto.

***(b) Fidelidad posterior (después de convertir).*** Conversión automatizada en lote con LibreOffice en modo headless (`soffice --headless --convert-to`), registrando las advertencias de conversión, seguida de la comparación origen–destino en varias dimensiones medibles:

| Dimensión | Cómo se mide |
| --- | --- |
| Divergencia visual de maquetación | Rasterizar ambas versiones a imagen por página y calcular el índice de similitud estructural (SSIM); emplea técnicas de visión por computador. |
| Reflujo de texto | Contar líneas/párrafos cuyos saltos de línea cambian de posición. |
| Sustitución de fuentes | Comparar las tablas de fuentes y contar las no coincidentes; permite definir un conjunto de fuentes "seguras" o comunes. |
| Integridad de objetos | Porcentaje de objetos incrustados (imágenes, tablas, formas) preservados. |
| Pérdida de mapeo de estilos | Comparar los estilos con nombre presentes en origen vs. destino. |
| Diferencia de paginación | Diferencia en el número de páginas (señal rápida y burda). |

Estas dimensiones se combinan en un índice ponderado de 0 a 100; los pesos se calibran con los datos de tiempo de edición de la validación humana, de modo que la severidad de cada elemento refleje su impacto real (la sustitución de una fuente es menor; una celda de tabla perdida es grave). El tiempo de edición se trata como métrica complementaria que ancla y valida la métrica automática, no como el eje central de la medición.

Herramientas candidatas, todas de código abierto o con API disponible: python-docx y Apache POI (inventario de características), LibreOffice headless (conversión), pandoc o pandiff (diferencias estructurales) y scikit-image/OpenCV o ImageMagick (`compare -metric SSIM`) para la comparación de imágenes.

## 6. Fases del Proyecto

### Fase 1 — Corpus y construcción del pipeline (~Mes 1)

**Objetivo:** reunir los insumos y dejar operativo el pipeline de medición.

**Actividades:**

- **Definición de la muestra documental:** Armar una red de contactos institucionales para obtener una muestra representativa de los tipos de documentos utilizados (memorandos, informes, formularios con tablas/celdas, oficios, actas, etc.). Clasificar por tipo y nivel de complejidad (texto simple → formularios complejos con "cajoncitos"). Cuando no sea posible obtener documentos reales, complementar con documentos sintéticos que reproduzcan las características críticas.
- **Análisis de herramientas actuales:** Mapear qué software utilizan actualmente los usuarios y en qué casos de uso (creación, edición, revisión, distribución).
- **Implementación del pipeline:** inventario de características, conversión en lote con LibreOffice headless y cálculo de las dimensiones de fidelidad descritas en la Sección 5.
- **Matriz de compatibilidad:** construir la matriz OOXML–ODF a partir de la documentación de soporte de LibreOffice y de pruebas propias.
- **Gestión ética:** como la intervención humana se limita a una validación pequeña, tramitar la aprobación y los acuerdos de confidencialidad solo para esa parte.

**Entregables:** corpus clasificado; pipeline funcional sobre un documento de prueba; matriz de compatibilidad preliminar.

### Fase 2 — Ejecución automática y validación humana (~Mes 2)

**Objetivo:** generar los datos de fidelidad a escala y los datos de calibración.

**Actividades:**

- **Ejecución en lote:** correr el pipeline sobre todo el corpus en ambos sentidos (p. ej., Word→LibreOffice y viceversa), obteniendo el puntaje de fidelidad y el registro de incompatibilidades por documento y por elemento.
- **Validación humana:** con un grupo reducido (p. ej., 4–6 personas) que incluya personal administrativo y perfiles académicos, medir el tiempo de edición sobre un subconjunto de documentos, distinguiendo tiempo productivo de tiempo de corrección de formato. Aplicar una encuesta de percepción breve.
- **Registro cruzado:** asociar cada resultado al tipo de documento y, en la validación, también al perfil de usuario.

**Entregables:** base de datos de incompatibilidades y puntajes de fidelidad por documento; tiempos de edición de la validación; encuestas breves.

### Fase 3 — Calibración, análisis y propuesta (~Mes 3)

**Objetivo:** convertir los datos en la métrica calibrada, el diagnóstico y la propuesta de solución.

**Actividades:**

- **Calibración de la métrica:** ajustar los pesos del índice contrastándolos con el tiempo de edición observado y validar la correlación entre el puntaje automático y el esfuerzo humano.
- **Análisis cuantitativo:** ranking de los elementos de formato más problemáticos; comparación entre plataformas y, donde aplique, entre perfiles; estimación del costo económico de la fricción (horas × costo/hora por perfil).
- **Propuesta de solución:** conjunto mínimo de elementos a evitar; formatos y prácticas recomendadas (incluida la posible adopción de ODF y de un conjunto de fuentes seguras); mitigaciones de bajo costo para la transición, como el uso de la interfaz de pestañas (Notebookbar) de LibreOffice para acercar la experiencia a la de Microsoft Office; y diseño conceptual de una capa intermedia de software que analice documentos, asigne el puntaje y sugiera correcciones.
- **Evaluación de mercado preliminar:** determinar si el costo del problema justifica que una institución pague por una solución.

**Entregables:** informe de resultados con diagnóstico del problema; métrica de compatibilidad documentada, calibrada y validada.

## 7. Cronograma (Fase 1–3: ~3 meses)

| Semana | Actividad principal                                                                             |
|---|-------------------------------------------------------------------------------------------------|
| 1–2 | Diseño del protocolo experimental. Gestión ética.                                               |
| 3–4 | Recolección y clasificación de muestra documental. Construcción de la matriz de compatibilidad. |
| 5–6 | Ejecución automática en lote sobre la muestra documental.                                                         |
| 7–8 | Validación humana (personal administrativo y académicos). Registro de tiempos.                  |
| 9–10 | Calibración de la métrica y análisis cuantitativo.                                              |
| 11–12 | Propuesta técnica e informe final.                                                              |

## 8. Alcance, supuestos y riesgos

***Alcance.*** El proyecto se centra en la fidelidad de formato en el intercambio de documentos entre suites de escritorio. La dimensión de colaboración (nube vs. local) y herramientas como Google Workspace o soluciones autoalojadas tipo NextCloud/Collabora —relevantes para la estrategia de soberanía digital de ESPOL— se reconocen como contexto relacionado y posible extensión, pero quedan fuera del núcleo medible para mantener la viabilidad en el semestre.

***Supuestos.*** Se asume la disponibilidad de una muestra mínima de documentos institucionales (complementable con documentos sintéticos) y el acceso a las herramientas de código abierto necesarias.

***Riesgos y mitigaciones.*** El principal riesgo —la dependencia de coordinación humana— se mitiga al hacer del pipeline automático el núcleo del trabajo.

## 9. Referencias

Huysmans, P., Ven, K., & Verelst, J. (2008). Reasons for the Non-adoption of OpenOffice.org in a Data-intensive Public Administration. *First Monday, 13*(10).

Rossi, B., Scotto, M., Sillitti, A., & Succi, G. (2006). An Empirical Study on the Migration to OpenOffice.org in a Public Administration. *International Journal of Information Technology and Web Engineering, 1*(3), 64–80. https://doi.org/10.4018/jitwe.2006070105

The Document Foundation. (2024). *German state moving 30,000 PCs to LibreOffice (Schleswig-Holstein)* [entrada de blog].

Ven, K., Van Nuffel, D., & Verelst, J. (2006). The Introduction of OpenOffice.org in the Brussels Public Administration. En *Open Source Systems*, IFIP, vol. 203, pp. 123–134.

Observatorio Europeo de Código Abierto / Joinup. (2016). *Italian military to save 26–29 million Euro by migrating to LibreOffice* (proyecto LibreDifesa).

*Nota: estas referencias fueron verificadas contra fuentes primarias o de alta credibilidad. Se recomienda revisar los textos completos antes de la redacción final del informe.*
