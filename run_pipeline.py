import logging  # Para registrar mensajes de información, advertencias y errores en la consola
import time     # Para medir el rendimiento y tiempo total de ejecución del pipeline

from src import extract, load, transform  # Importa los tres módulos principales de tu ETL

# Configuración básica del sistema de logs con formato de marca temporal, nivel y mensaje
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("pipeline")  # Crea un registrador específico con el nombre "pipeline"


def main() -> None:
    """Función principal que orquesta la ejecución secuencial de todo el ETL."""
    inicio = time.perf_counter()  # Inicia el cronómetro de alta precisión para medir el tiempo total
    
    # Define la lista de pasos que componen el ETL vinculando su nombre con su respectiva función run()
    pasos = [("extract", extract.run), ("transform", transform.run), ("load", load.run)]
    
    # Itera de manera secuencial a través de cada paso del pipeline
    for nombre, paso in pasos:
        log.info("Paso: %s", nombre)  # Registra el inicio de la ejecución del paso actual
        try:
            paso()  # Ejecuta la función del paso (extract, transform o load)
        except Exception:
            # Si ocurre cualquier excepción imprevista durante el paso, registra el error completo con su traza (stack trace)
            log.exception("Falló el paso %s", nombre)
            raise SystemExit(1)  # Detiene la ejecución de todo el programa inmediatamente devolviendo código de error (1)
            
    # Al finalizar con éxito todos los pasos, calcula el tiempo transcurrido y lo registra en consola con un decimal
    log.info("Pipeline completo en %.1f s", time.perf_counter() - inicio)


if __name__ == "__main__":
    main()  # Ejecuta la función principal si el script se llama directamente desde la terminal