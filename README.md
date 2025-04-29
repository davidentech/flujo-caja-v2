# 💰 Control de Flujo de Caja

Dashboard financiero interactivo desarrollado en Streamlit para visualizar, analizar y simular el flujo de caja de una empresa o persona. Permite cargar extractos bancarios en PDF, analizar datos históricos, simular escenarios y trabajar con datos de prueba.

## Características principales
- Visualización de ingresos, egresos, flujo neto y saldo acumulado.
- Filtros por mes, trimestre, semestre o año completo.
- Carga de extractos bancarios en PDF (soporte para tablas tipo "lattice").
- Opción de datos históricos, simulados y datos de prueba 2024.
- Gráficos interactivos y KPIs modernos.
- Interfaz personalizable y responsiva.

## Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/davidentech/flujo-caja-v2.git
   cd flujo-caja-v2
   ```
2. Crea y activa un entorno virtual (opcional pero recomendado):
   ```bash
   python -m venv env
   # En Windows:
   .\env\Scripts\activate
   # En Mac/Linux:
   source env/bin/activate
   ```
3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

## Uso

1. Ejecuta la aplicación:
   ```bash
   streamlit run app.py
   ```
2. Abre tu navegador en [http://localhost:8501](http://localhost:8501)
3. Usa el sidebar para cargar datos, seleccionar periodos y analizar el flujo de caja.

## Dependencias principales
- streamlit
- pandas
- numpy
- plotly
- camelot-py
- pdfplumber
- python-dateutil

## Estructura del proyecto

```
flujo-caja-v2/
├── app.py              # Código principal de la app Streamlit
├── requirements.txt    # Dependencias del proyecto
├── README.md           # Este archivo
└── datos_bancarios/    # (opcional) CSVs históricos
```

## Para desarrolladores

- El código está documentado y modularizado para facilitar la extensión.
- Puedes agregar nuevas fuentes de datos, tipos de análisis o personalizar la UI fácilmente.
- Para desarrollo colaborativo, usa ramas feature/ y pull requests.
- Si agregas nuevas dependencias, actualiza `requirements.txt`.

### Scripts útiles
- Formateo de código: `black app.py`
- Revisión de dependencias: `pip freeze > requirements.txt`

## Licencia
MIT

---

Desarrollado por [@davidentech](https://github.com/davidentech) 🚀