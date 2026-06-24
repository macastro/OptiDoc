# Protocolo Experimental — Métrica de Compatibilidad de Documentos Ofimáticos

## Fase 1 del proyecto  

---

## 1. Planteamiento del problema

Los documentos ofimáticos pueden experimentar alteraciones de formato cuando se abren, convierten o editan en una plataforma distinta a aquella en la que fueron creados. Estas alteraciones pueden incluir cambios en:

- distribución del contenido;
- saltos de página;
- tablas;
- imágenes;
- encabezados y pies de página;
- listas;
- columnas;
- estilos;
- fuentes tipográficas;
- objetos incrustados.

Actualmente, la valoración de estas pérdidas suele realizarse mediante inspección manual. Este procedimiento depende del criterio del evaluador, requiere tiempo y dificulta la comparación reproducible entre documentos y plataformas.

El proyecto propone explorar una métrica computacional que permita diagnosticar de forma objetiva la pérdida de fidelidad de formato y expresarla mediante un índice de compatibilidad entre **0 y 100**.

En esta fase inicial se estudiará principalmente el flujo:

```text
OOXML (.docx) -> LibreOffice -> ODF (.odt)
```

La comparación con Microsoft Word u otros motores de renderizado se considera una posible extensión posterior.

---

## 2. Objetivo

Diseñar e implementar un procedimiento experimental reproducible que permita:

1. analizar las características de un documento `.docx` antes de convertirlo;
2. convertir el documento a formato `.odt`;
3. renderizar el documento original y el documento convertido;
4. comparar ambas representaciones;
5. calcular un puntaje de compatibilidad;
6. conservar evidencias que permitan revisar manualmente el diagnóstico;
7. explorar la relación entre la complejidad del documento y el esfuerzo necesario para corregirlo.

El índice obtenido durante el Hito 1 tendrá carácter exploratorio. No se considerará una métrica validada hasta contrastarlo con documentos reales y con observaciones de usuarios.

---

## 3. Preguntas iniciales de investigación

Se proponen las siguientes preguntas:

### PI1

¿Es posible detectar automáticamente diferencias de formato entre un documento OOXML y su versión convertida a ODF?

### PI2

¿Qué dimensiones resultan útiles para representar la compatibilidad de un documento?

Inicialmente se considerarán:

- similitud visual;
- conservación de la paginación;
- conservación de las fuentes;
- conservación de algunos elementos estructurales.

### PI3

¿Puede estimarse, antes de realizar la conversión, qué documentos presentan mayor riesgo de pérdida de fidelidad?

### PI4

¿Existe relación entre el puntaje calculado automáticamente y el tiempo que una persona necesita para corregir el documento convertido?

La PI4 no se responderá completamente durante el Hito 1, pero se dejará planteado el procedimiento para una fase de calibración posterior.

---

## 4. Hipótesis de trabajo

Se plantean provisionalmente las siguientes hipótesis:

- **H1:** una comparación visual entre páginas rasterizadas puede detectar cambios relevantes de maquetación;
- **H2:** una diferencia en el número de páginas constituye una señal de pérdida de fidelidad;
- **H3:** la pérdida o sustitución de fuentes puede afectar la apariencia del documento;
- **H4:** los documentos con mayor cantidad de tablas, imágenes, columnas, listas, fuentes y objetos especiales presentan mayor riesgo de requerir reformateo;
- **H5:** un índice compuesto puede aproximar mejor la compatibilidad que una única métrica aislada.

Estas hipótesis deberán revisarse después de las primeras ejecuciones del pipeline.

---

## 5. Diseño general del experimento

El protocolo propone separar el análisis en dos momentos.

### 5.1 Momento A: análisis previo

Antes de convertir el documento se realizará un inventario de sus características.

La finalidad será estimar su complejidad y generar una predicción del riesgo de incompatibilidad.

```text
Documento original
        |
        v
Inventario de características
        |
        v
Estimación de riesgo
```

### 5.2 Momento B: análisis posterior

Después de la conversión se comparará el documento original con el convertido.

```text
Documento original -----> representación de origen
        |
        v
Conversión a ODF
        |
        v
Documento convertido ---> representación de destino
        |
        v
Comparación y puntaje
```

Es importante no confundir ambos resultados:

- el **riesgo previsto** intenta anticipar problemas;
- el **índice de compatibilidad** intenta medir la degradación observada.

---

## 6. Inventario del documento

Se propone desarrollar un módulo que extraiga automáticamente información del archivo `.docx`.

Las características iniciales serán:

- número de párrafos;
- número de tablas;
- cantidad de estilos utilizados;
- fuentes declaradas;
- imágenes;
- listas;
- hipervínculos;
- encabezados;
- pies de página;
- secciones;
- columnas;
- saltos de página.

También se explorará la detección de:

- objetos OLE;
- ecuaciones;
- formas;
- campos;
- notas al pie;
- control de cambios;
- contenido incrustado.

La extracción se realizaría mediante `python-docx` y, cuando sea necesario, mediante lectura directa de los archivos XML contenidos en el paquete OOXML.

### 6.1 Estimación de esfuerzo

Se propone construir una puntuación heurística de riesgo basada en la presencia de elementos que suelen provocar problemas de interoperabilidad.

Una primera formulación podría ser:

```text
riesgo =
    w1 * tablas +
    w2 * imágenes +
    w3 * listas +
    w4 * columnas +
    w5 * fuentes_no_comunes +
    w6 * objetos_especiales +
    w7 * control_de_cambios
```

El resultado se normalizaría a una escala de `0–100` y se clasificaría como:

- bajo;
- medio;
- alto.

Los pesos todavía no están definidos. Durante el Hito 1 podrán asignarse por juicio experto y documentarse como provisionales.

Esta estimación no formará parte necesariamente del índice final de fidelidad.

---

## 7. Conversión de documentos

La conversión se realizará inicialmente con LibreOffice en modo *headless*.

Comando de referencia:

```bash
soffice --headless \
        --convert-to odt \
        --outdir <directorio_salida> \
        <documento.docx>
```

También será necesario generar archivos PDF para obtener representaciones comparables.

Se prevén dos alternativas:

### Alternativa A: un solo motor de renderizado

LibreOffice renderizará:

- el archivo `.docx` original;
- el archivo `.odt` convertido.

Ventajas:

- automatización sencilla;
- ejecución multiplataforma;
- menor dependencia de software propietario;
- mayor reproducibilidad.

Limitación:

- podría no capturar las diferencias entre Microsoft Word y LibreOffice, porque ambos lados serían interpretados por el mismo motor.

### Alternativa B: motores diferentes

Microsoft Word generaría el PDF de referencia y LibreOffice generaría el PDF convertido.

Ventaja:

- representaría mejor el comportamiento observado por un usuario que cambia de plataforma.

Limitaciones:

- requiere Microsoft Word;
- dificulta la ejecución automatizada;
- reduce la reproducibilidad en Linux o en integración continua.

Para el Hito 1 se propone iniciar con la **Alternativa A** y documentar claramente qué tipo de pérdida permite medir.

---

## 8. Rasterización

Los archivos PDF se convertirán a imágenes PNG para realizar la comparación visual.

Herramienta prevista:

```bash
pdftoppm -png documento.pdf pagina
```

Parámetros por definir:

- resolución de rasterización;
- formato de color;
- tratamiento de transparencia;
- compresión;
- normalización del tamaño de página.

Se propone utilizar inicialmente una resolución fija entre **150 y 200 DPI**. La resolución definitiva deberá seleccionarse después de evaluar el costo computacional y la sensibilidad de la métrica.

---

## 9. Métricas

### 9.1 Similitud visual

La métrica principal propuesta es el **Índice de Similitud Estructural (SSIM)**.

Para cada par de páginas:

```text
SSIM(página_origen, página_destino) -> [0, 1]
```

Interpretación inicial:

- `1.0`: imágenes idénticas;
- valor cercano a `1.0`: alta similitud;
- valor menor: presencia de diferencias.

El puntaje visual se expresaría como:

```text
fidelidad_visual = promedio(SSIM_paginas) * 100
```

Aspectos pendientes:

- definir si se compararán todas las páginas;
- definir cómo seleccionar páginas representativas en documentos extensos;
- definir cómo tratar páginas faltantes;
- definir cómo normalizar imágenes de distinto tamaño;
- definir un umbral para clasificar una página como compatible;
- evaluar la sensibilidad ante pequeños desplazamientos o diferencias de antialiasing.

Como valor inicial podría explorarse un umbral de compatibilidad entre `0.98` y `0.99`, sin considerarlo definitivo.

### 9.2 Conservación de paginación

Se comparará el número de páginas del documento original y del documento convertido.

Una fórmula inicial sería:

```text
paginacion =
    min(paginas_origen, paginas_destino)
    / max(paginas_origen, paginas_destino)
```

El resultado se multiplicaría por `100`.

Esta métrica es sencilla, pero no identifica cambios internos cuando el número total de páginas se conserva.

### 9.3 Conservación de fuentes

Se explorará la comparación entre las fuentes utilizadas en el documento original y las fuentes declaradas en el documento convertido.

Posibles casos:

- fuente conservada exactamente;
- fuente reemplazada por una alternativa considerada compatible;
- fuente ausente;
- fuente declarada, pero no disponible en el sistema.

Una puntuación tentativa podría asignar:

```text
fuente exacta              = 1.0
sustitución aceptable      = 0.5 a 0.8
fuente ausente             = 0.0
```

Esta dimensión se considera experimental porque el nombre declarado dentro del archivo no garantiza que la fuente haya sido realmente utilizada durante el renderizado.

### 9.4 Conservación estructural

Como posible extensión se analizará la conservación de:

- tablas;
- imágenes;
- listas;
- encabezados;
- pies de página;
- secciones;
- columnas.

Durante el Hito 1 esta dimensión podrá limitarse al inventario y no incluirse todavía en el puntaje.

---

## 10. Índice de compatibilidad

El índice se calculará como una combinación ponderada de las métricas disponibles.

Una primera alternativa simplificada sería:

```text
indice = 0.80 * fidelidad_visual
       + 0.20 * conservacion_paginacion
```

Una segunda alternativa sería incorporar fuentes:

```text
indice = w1 * fidelidad_visual
       + w2 * conservacion_paginacion
       + w3 * conservacion_fuentes
```

Con:

```text
w1 + w2 + w3 = 1
```

Los pesos iniciales podrán ser uniformes o definidos por criterio experto. La decisión deberá registrarse como provisional.

En una fase posterior, los pesos se calibrarán utilizando:

- evaluación humana;
- tiempo de reformateo;
- número de operaciones de corrección;
- modelos de regresión;
- técnicas de decisión multicriterio.

---

## 11. Corpus experimental

### 11.1 Corpus sintético inicial

Para validar técnicamente el pipeline se propone crear entre uno y tres documentos sintéticos.

Los documentos deberían cubrir al menos:

#### Documento simple

- texto;
- títulos;
- estilos básicos;
- una página;
- fuentes comunes.

#### Documento intermedio

- varias páginas;
- tablas;
- imágenes;
- encabezados;
- pies de página;
- listas.

#### Documento complejo

- varias secciones;
- columnas;
- tablas con combinaciones;
- múltiples fuentes;
- objetos o campos;
- control de cambios, si es posible.

El corpus sintético permitirá introducir características de forma controlada y repetir el experimento.

### 11.2 Corpus real

En una fase posterior se incorporarán documentos reales, preferiblemente institucionales.

Será necesario:

- anonimizar datos personales;
- obtener autorización de uso;
- clasificar los documentos por complejidad;
- evitar documentos protegidos;
- documentar las características relevantes.

### 11.3 Posibles criterios de exclusión

Se propone excluir inicialmente:

- documentos protegidos por contraseña;
- documentos corruptos;
- archivos con macros;
- documentos con contenido no redistribuible;
- documentos que requieran complementos propietarios;
- documentos con fuentes embebidas cuya licencia impida su uso.

---

## 12. Procedimiento experimental

Para cada documento se realizará el siguiente procedimiento:

1. registrar el nombre y las características generales del archivo;
2. ejecutar el inventario automático;
3. guardar la estimación de riesgo;
4. convertir el `.docx` a `.odt`;
5. generar el PDF del documento de origen;
6. generar el PDF del documento convertido;
7. rasterizar ambos PDF;
8. emparejar las páginas por posición;
9. calcular SSIM;
10. comparar el número de páginas;
11. explorar la conservación de fuentes;
12. calcular el índice;
13. generar mapas o imágenes de diferencias;
14. producir un reporte estructurado;
15. revisar manualmente los resultados.

---

## 13. Referencias

- Wang, Z., Bovik, A. C., Sheikh, H. R., & Simoncelli, E. P. (2004). *Image quality assessment: From error visibility to structural similarity*. IEEE Transactions on Image Processing, 13(4), 600–612.
- ISO/IEC 26300. *OpenDocument Format for Office Applications*.
- ISO/IEC 29500. *Office Open XML File Formats*.
- The Document Foundation. Documentación de LibreOffice para conversión mediante línea de comandos.

---

## Nota final

Este protocolo corresponde a una versión temprana de la propuesta experimental. Su finalidad es orientar la implementación del primer prototipo y hacer explícitas las decisiones que todavía deben validarse.

Las fórmulas, pesos, umbrales, herramientas y criterios podrán modificarse a partir de los resultados del piloto.
