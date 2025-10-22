# Optimizador de Modelos Epidemiológicos (ACOR-SEIR)

Aplicación de escritorio en Python (PyQt5) para la calibración de parámetros de modelos epidemiológicos complejos (SEIR) utilizando un optimizador metaheurístico avanzado (Ant Colony Optimization for Continuous Domains - ACOR).

Este proyecto fue desarrollado como una herramienta de investigación para encontrar los 22 parámetros de un modelo SEIR armónico (dependiente del tiempo), ajustándolo a datos de casos observados (ej. curvas epidémicas de COVID-19).

## Características Principales

* **Interfaz Gráfica (GUI):** Construida con PyQt5, permite cargar datos (`.xlsx`, `.json`), configurar parámetros y visualizar resultados en tiempo real.
* **Optimizador ACOR Avanzado:** Implementación de un optimizador ACOR multi-colonia (modelo de islas) para evitar óptimos locales.
* **Alto Rendimiento:** Utiliza `multiprocessing.Pool` para paralelizar la evaluación de la función de costo (la parte más pesada del cálculo), aprovechando todos los núcleos del CPU.
* **Modelo Epidemiológico Complejo:** Implementa un modelo SEIR donde las tasas de transmisión ($\beta$), recuperación ($\gamma$) y latencia ($\sigma$) son funciones armónicas, permitiendo capturar la estacionalidad y las olas de la epidemia.
* **Análisis y Visualización:** Incluye un dashboard con gráficas (usando `pyqtgraph`) para analizar la convergencia del costo, la evolución de los parámetros y la distribución de las soluciones en las colonias.
* **Reportes en PDF:** Genera un reporte final en PDF con los resultados de la optimización, incluyendo gráficas y los parámetros finales.


## Tecnologías Utilizadas

* **Lenguaje:** Python 3
* **GUI:** PyQt5
* **Cómputo Científico:** NumPy, SciPy (para `odeint`, la resolución de EDOs)
* **Paralelización:** `multiprocessing`
* **Visualización:** `pyqtgraph`
* **Manejo de Datos:** Pandas (para importar `.xlsx`)

## Estructura del Proyecto

El código está modularizado para una clara separación de responsabilidades:

* `main.py`: Contiene la lógica de la ventana principal (GUI), la gestión de hilos (`QThread`) y la orquestación de la aplicación.
* `clases/seir_model.py`: Define el modelo matemático SEIR, el sistema de Ecuaciones Diferenciales Ordinarias (EDOs) y la función de costo (fitness).
* `clases/acor_optimizer.py`: Contiene la implementación completa del algoritmo de optimización ACOR, incluyendo el modelo de islas (migración) y las búsquedas locales.
* `clases/dialogs.py`: Define todas las ventanas de diálogo secundarias para el análisis de resultados (convergencia, residuos, Rt, etc.).
* `clases/report_generator.py`: Lógica para crear el reporte en PDF de los resultados finales.

## Cómo Usar

1.  Clonar el repositorio:
    ```bash
    git clone [https://github.com/Josch01/optimizador-seir-acor.git](https://github.com/Josch01/optimizador-seir-acor.git)
    ```
2.  (Recomendado) Crear un entorno virtual e instalar dependencias:
    ```bash
    pip install numpy pandas scipy pyqt5 pyqtgraph qdarktheme
    ```
3.  Ejecutar la aplicación:
    ```bash
    python main.py
    ```
4.  Importar un archivo de datos (`.xlsx` o `.json`) con dos columnas: (tiempo, infectados).
5.  Ajustar los parámetros de optimización en la pestaña "Configuración".
6.  Presionar "Correr".
