# Métrica de Compatibilidad de Documentos Ofimáticos — Pipeline  

## Descripción

Este proyecto busca construir una métrica objetiva para estimar cuánto se altera el formato de un documento ofimático cuando un archivo creado en formato OOXML (`.docx`) se convierte o edita mediante otra plataforma, inicialmente LibreOffice y el formato ODF (`.odt`).

La propuesta consiste en automatizar la conversión, el renderizado y la comparación de los documentos para producir un puntaje de compatibilidad en una escala de **0 a 100**, donde:

- **100** representa una conservación visual muy alta.
- **0** representa una pérdida severa de fidelidad.

En esta primera versión se prioriza comprobar la viabilidad técnica del flujo completo con al menos un documento de prueba. La definición final de las métricas, sus pesos y el protocolo experimental todavía se encuentra en revisión.

---

## Objetivo

Implementar una prueba de concepto reproducible que permita:

1. Recibir un documento `.docx`.
2. Convertirlo a `.odt` utilizando LibreOffice en modo *headless*.
3. Generar una representación PDF del documento original y del documento convertido.
4. Rasterizar las páginas de ambos PDF.
5. Comparar visualmente las páginas mediante SSIM.
6. Calcular un puntaje de compatibilidad.
7. Generar archivos de salida que permitan revisar manualmente las diferencias.

De manera complementaria, se plantea crear un inventario básico de las características del documento para identificar elementos que podrían generar problemas durante la conversión.

---

## Estado actual del prototipo

La versión contempla las siguientes funciones:

- Conversión automática de `.docx` a `.odt`.
- Exportación del documento original y convertido a PDF.
- Rasterización de las páginas a imágenes PNG.
- Comparación visual página por página utilizando SSIM.
- Registro del número de páginas del documento original y convertido.
- Generación de un puntaje inicial de compatibilidad.
- Producción de un reporte básico en formato JSON.

Las siguientes funciones todavía están incompletas o sujetas a cambios:

- Inventario exhaustivo de características OOXML.
- Detección y comparación confiable de fuentes.
- Tratamiento de documentos con diferente número de páginas.
- Definición de sustituciones tipográficas aceptables.
- Calibración de los pesos del índice.
- Validación con documentos reales y usuarios.
- Medición del tiempo requerido para corregir manualmente un documento.

---

## Flujo

El pipeline propuesto sigue este proceso:

```text
Documento DOCX
      |
      v
Inventario básico del documento
      |
      v
Conversión DOCX -> ODT
      |
      +-------------------+
      |                   |
      v                   v
PDF del origen       PDF del destino
      |                   |
      v                   v
Imágenes PNG         Imágenes PNG
      |                   |
      +---------+---------+
                |
                v
     Comparación visual SSIM
                |
                v
      Puntaje 0–100
                |
                v
          Reporte JSON
```

---

## Métricas consideradas

### 1. Similitud visual mediante SSIM

La métrica principal del prototipo es el **Índice de Similitud Estructural**, o SSIM.

Para cada par de páginas se calcula un valor entre `0` y `1`:

- Un valor cercano a `1` indica que ambas páginas son visualmente similares.
- Un valor cercano a `0` indica diferencias importantes.

El resultado del documento se obtiene mediante el promedio de las páginas comparables.

```text
SSIM_documento = promedio(SSIM_página_1, ..., SSIM_página_n)
```

En esta etapa todavía se debe definir cómo penalizar de forma adecuada:

- páginas agregadas;
- páginas eliminadas;
- cambios de resolución;
- desplazamientos mínimos;
- diferencias producidas por el propio motor de renderizado.

### 2. Conservación de paginación

Se registra la cantidad de páginas del documento original y del documento convertido.

Una primera aproximación sería:

```text
paginacion = min(paginas_origen, paginas_destino)
             / max(paginas_origen, paginas_destino)
```

Esta fórmula todavía debe validarse, ya que dos documentos pueden tener el mismo número de páginas y presentar diferencias importantes de maquetación.

### 3. Conservación de fuentes

Se plantea comparar las fuentes declaradas dentro del archivo `.docx` con las encontradas en el archivo `.odt`.

Esta dimensión se encuentra en fase experimental porque:

- una misma fuente puede aparecer con nombres diferentes;
- LibreOffice puede aplicar sustituciones durante el renderizado;
- algunas fuentes se definen en estilos y no directamente en el contenido;
- una sustitución tipográfica no siempre produce una degradación visible.

Por el momento, esta métrica podrá omitirse o utilizarse únicamente como dato informativo.

---

## Puntaje

El puntaje inicial se calculará principalmente a partir de la similitud visual y la paginación.

Una primera fórmula propuesta es:

```text
puntaje = 100 * (
    0.80 * similitud_visual +
    0.20 * conservacion_paginacion
)
```

Los pesos son provisionales y no representan todavía una validación experimental.

En versiones posteriores se espera incorporar:

```text
puntaje = 100 * (
    w1 * similitud_visual +
    w2 * conservacion_paginacion +
    w3 * conservacion_fuentes +
    w4 * otras_metricas
)
```

Donde los pesos `w1`, `w2`, `w3` y `w4` deberán determinarse con datos observados.

---

## Inventario del documento

Antes de la conversión se propone registrar algunas características del `.docx` que podrían influir en el resultado:

- número de páginas estimado;
- tablas;
- imágenes;
- encabezados y pies de página;
- estilos utilizados;
- fuentes declaradas;
- listas numeradas o con viñetas;
- saltos de página;
- secciones;
- columnas;
- notas al pie;
- hipervínculos.

El inventario inicial no pretende evaluar todavía la calidad de la conversión. Su objetivo es describir la complejidad del documento y facilitar el análisis posterior de los errores.

La detección de control de cambios, objetos incrustados, ecuaciones, formas y elementos avanzados se deja como trabajo pendiente.

---

## Requisitos

- Python 3.12.
- LibreOffice con el ejecutable `soffice` disponible en el `PATH`.
- Poppler, específicamente el comando `pdftoppm`.
- Dependencias de Python definidas en `requirements.txt`.


---

## Uso provisional

Ejecutar el pipeline sobre un documento:

```bash
python -m src.pipeline \
    --doc corpus/documento_prueba.docx \
    --salida salidas
```

El nombre y los parámetros de la interfaz de línea de comandos podrían cambiar durante el desarrollo.

También se prevé permitir la ejecución sobre una carpeta completa:

```bash
python -m src.pipeline \
    --corpus corpus/documentos \
    --salida salidas
```

Esta opción todavía puede no estar implementada en la primera revisión del prototipo.

---

## Salidas esperadas

Para cada documento se espera generar una estructura similar a la siguiente:

```text
salidas/
└── documento_prueba/
    ├── reporte.json
    ├── origen.pdf
    ├── destino.pdf
    ├── img_origen/
    │   ├── pag-1.png
    │   └── pag-2.png
    ├── img_destino/
    │   ├── pag-1.png
    │   └── pag-2.png
    └── diferencias/
        ├── pag-1.png
        └── pag-2.png
```

El archivo `reporte.json` podría contener inicialmente:

```json
{
  "documento": "documento_prueba.docx",
  "paginas_origen": 2,
  "paginas_destino": 2,
  "ssim_promedio": 0.91,
  "conservacion_paginacion": 1.0,
  "puntaje": 92.8,
  "estado": "prototipo"
}
```

Los nombres de campos y la estructura definitiva del reporte están sujetos a cambios.

---
