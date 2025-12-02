"""
Simulación con SimPy — soporte de días no hábiles configurables.
Modificado para incluir verificación de calidad EN CADA ESTACIÓN con posibilidad de reproceso inmediato.
Cuando una estación de inspección rechaza, se regresa a estaciones anteriores.
"""

import simpy
import csv
import uuid
import random
from datetime import datetime, timedelta, date

# ---------------------------
# CONFIGURACIÓN (ajusta aquí)
# ---------------------------
ORDENES = {
    "Cónico": 100,  
    "Helicoidal": 200,
    "Sinfín-Corona": 200
}

# PROCESOS ahora incluye probabilidad de rechazo como cuarto elemento
PROCESOS = {
    "Cónico": [
        ("Corte Material", 2, 1, 0.001),      # 0.1% probabilidad de rechazo
        ("Mecanizado Rueda", 15, 3, 0.03),   # 3% probabilidad de rechazo
        ("CNC Dientes Rueda", 30, 1, 0.05),  # 5% probabilidad de rechazo
        ("Tratamiento Térmico", 600, 30, 0.04),  # 4% probabilidad de rechazo
        ("Rectificado Dientes", 5, 1, 0.03), # 3% probabilidad de rechazo
        ("Inspección Software", 10, 1, 0.02),# 2% probabilidad de rechazo
        ("Ensamblaje", 30, 3, 0.03),         # 3% probabilidad de rechazo
        ("Inspección Final", 5, 1, 0.05)     # 5% probabilidad de rechazo
    ],

    "Helicoidal": [
        ("Corte Material", 2, 1, 0.001),
        ("Mecanizado Piñón", 10, 3, 0.03),
        ("Tallado Piñón", 15, 1, 0.04),
        ("Tratamiento Térmico", 600, 30, 0.04),
        ("Rectificado Dientes", 5, 1, 0.03),
        ("Inspección Software", 10, 1, 0.02),
        ("Ensamblaje", 30, 3, 0.03),
        ("Inspección Final", 5, 1, 0.05)
    ],

    "Sinfín-Corona": [
        ("Corte Material", 2, 1, 0.001),
        ("Cilindrado Material", 6, 3, 0.03),
        ("Torneado Tornillo Sinfín", 10, 1, 0.04),
        ("Fresado Cuñero", 5, 2, 0.03),
        ("Tratamiento Térmico", 600, 30, 0.04),
        ("Rectificado Dientes", 5, 1, 0.03),
        ("Inspección Software", 10, 1, 0.02),
        ("Ensamblaje", 30, 3, 0.03),
        ("Inspección Final", 5, 1, 0.05)
    ]
}

# Configuración de qué estaciones anteriores deben reprocesarse cuando una inspección falla
# Mapeo: estación_inspección -> [estaciones_anteriores_para_reproceso]
REPROCESO_POR_INSPECCION = {
    "Inspección Software": ["Rectificado Dientes", "Tratamiento Térmico"],
    "Inspección Final": ["Ensamblaje", "Rectificado Dientes"]
}

# Estaciones que requieren reproceso completo desde ellas mismas
ESTACIONES_REPROCESO_COMPLETO = {
    "Cónico": ["Tratamiento Térmico", "Rectificado Dientes"],
    "Helicoidal": ["Tratamiento Térmico", "Rectificado Dientes"],
    "Sinfín-Corona": ["Tratamiento Térmico", "Rectificado Dientes"]
}

# Horario laboral
HORA_INICIO = 8
HORA_FIN = 17

# Fecha base (inicio de simulación)
FECHA_INICIAL = datetime(2025, 1, 2, HORA_INICIO, 0, 0)

# Lista de días no hábiles (format "YYYY-MM-DD")
NON_WORKING_DAYS = [
    "2025-01-04",
    "2025-01-05",
    "2025-01-06",
    "2025-01-11",  
    "2025-01-12",
    "2025-01-18",
    "2025-01-19",
    "2025-01-25",
    "2025-01-26",
]

# ---------------------------
# PARÁMETROS ALEATORIEDAD
# ---------------------------
VAR_SIGMA_PORC = 0.20  # desviación como fracción (20%)
SEED = None            # semilla opcional

# ---------------------------
# UTILITARIOS: parsear feriados
# ---------------------------
def parse_non_working(dates_list):
    s = set()
    for ds in dates_list:
        try:
            dt = datetime.strptime(ds, "%Y-%m-%d").date()
            s.add(dt)
        except Exception:
            raise ValueError(f"Formato inválido en NON_WORKING_DAYS: {ds} (use YYYY-MM-DD)")
    return s

NON_WORKING_SET = parse_non_working(NON_WORKING_DAYS)

# ---------------------------
# FUNCIONES DE TIEMPO
# ---------------------------
def es_dia_habil(dt_date):
    """Devuelve True si la fecha (obj date) es día hábil (no está en NON_WORKING_SET)."""
    return dt_date not in NON_WORKING_SET

def siguiente_dia_habil(dt):
    """Devuelve datetime del siguiente día hábil con hora = HORA_INICIO."""
    d = dt.date()
    # avanza día a día hasta encontrar uno habil
    while True:
        d = d + timedelta(days=1)
        if es_dia_habil(d):
            return datetime(d.year, d.month, d.day, HORA_INICIO, 0, 0)

def a_fecha_laboral(env_minutes):
    """
    Convierte tiempo simulado (minutos desde FECHA_INICIAL) a datetime "real"
    respetando:
      - horario laboral HORA_INICIO..HORA_FIN (minutos por día = (HORA_FIN-HORA_INICIO)*60)
      - saltar fechas en NON_WORKING_SET (no hábiles)
    """
    minutos_por_dia = (HORA_FIN - HORA_INICIO) * 60
    cursor = FECHA_INICIAL
    remaining = int(env_minutes)

    if remaining == 0:
        return cursor

    while True:
        if not es_dia_habil(cursor.date()):
            cursor = siguiente_dia_habil(cursor)
            continue
            
        start_of_day = cursor.replace(hour=HORA_INICIO, minute=0, second=0)
        end_of_day = cursor.replace(hour=HORA_FIN, minute=0, second=0)

        if cursor < start_of_day:
            cursor = start_of_day

        if cursor >= end_of_day:
            cursor = siguiente_dia_habil(cursor)
            continue

        minutos_disponibles = int((end_of_day - cursor).total_seconds() / 60)

        if remaining <= minutos_disponibles:
            result = cursor + timedelta(minutes=remaining)
            if not es_dia_habil(result.date()):
                cursor = siguiente_dia_habil(cursor)
                continue
            return result
        else:
            remaining -= minutos_disponibles
            cursor = siguiente_dia_habil(cursor)

def normal_time(mu):
    """Variación normal: μ=base, σ=mu*VAR_SIGMA_PORC, devuelve minutos enteros >=1."""
    sigma = mu * VAR_SIGMA_PORC
    t = random.gauss(mu, sigma)
    return max(1, int(round(t)))

def verificar_calidad_estacion(estacion, prob_rechazo_base):
    """Simula la verificación de calidad para una estación específica."""
    return random.random() > prob_rechazo_base

def obtener_estaciones_para_reproceso(producto, estacion_actual, procesos_lista):
    """Determina qué estaciones deben reprocesarse basado en la estación actual."""
    # Si es una estación de inspección, regresar a las estaciones anteriores definidas
    if estacion_actual in REPROCESO_POR_INSPECCION:
        return REPROCESO_POR_INSPECCION[estacion_actual]
    
    # Si es una estación de reproceso completo, regresar a ella misma
    if estacion_actual in ESTACIONES_REPROCESO_COMPLETO.get(producto, []):
        return [estacion_actual]
    
    # Para otras estaciones, regresar solo a esa estación
    return [estacion_actual]

def obtener_procesos_desde_estaciones(procesos_lista, estaciones_reproceso):
    """Obtiene la lista de procesos a partir de las estaciones especificadas para reproceso."""
    # Encontrar la primera estación que necesita reproceso
    primera_estacion = None
    for est, _, _, _ in procesos_lista:
        if est in estaciones_reproceso:
            primera_estacion = est
            break
    
    if not primera_estacion:
        return procesos_lista  # Por defecto, reprocesar todo
    
    # Encontrar desde qué índice empezar
    procesos_reproceso = []
    empezar = False
    for proceso in procesos_lista:
        estacion = proceso[0]
        if estacion == primera_estacion:
            empezar = True
        if empezar:
            procesos_reproceso.append(proceso)
    
    return procesos_reproceso

# ---------------------------
# SIMULACIÓN SIMPY
# ---------------------------
def procesar_estacion_con_calidad(env, producto, pid, estacion, base_t, prob_rechazo, 
                                 estaciones, log, intento_numero):
    """Procesa una estación con verificación de calidad incorporada."""
    recurso = estaciones[estacion]
    intento_local = 1
    max_intentos_local = 3
    
    while intento_local <= max_intentos_local:
        # Procesar la estación
        dur = normal_time(base_t)
        
        with recurso.request() as req:
            t_antes = env.now
            yield req
            espera = env.now - t_antes

            start = env.now
            fecha_real = a_fecha_laboral(start)
            
            # Procesamos directamente
            yield env.timeout(dur)
        
        # Verificación de calidad (excepto para estaciones de inspección)
        es_inspeccion = "Inspección" in estacion
        
        if not es_inspeccion:
            # Para estaciones normales, hacer inspección de calidad
            yield env.timeout(2)  # Tiempo para inspección
            
            if verificar_calidad_estacion(estacion, prob_rechazo):
                # Aprobado - registrar resultado
                log.append([
                    fecha_real.strftime("%Y-%m-%d %H:%M:%S"),
                    producto,
                    pid,
                    estacion,
                    dur + 2,  # Tiempo total (proceso + inspección)
                    round(espera, 2),
                    intento_numero,
                    "APROBADO"
                ])
                return True, None  # Aprobado, continuar a siguiente estación
            else:
                # Rechazado - registrar resultado
                log.append([
                    fecha_real.strftime("%Y-%m-%d %H:%M:%S"),
                    producto,
                    pid,
                    estacion,
                    dur + 2,  # Tiempo total (proceso + inspección)
                    round(espera, 2),
                    intento_numero,
                    "RECHAZADO"
                ])
                intento_local += 1
                # Si superó el máximo de intentos locales, salir
                if intento_local > max_intentos_local:
                    return False, estacion
                # Continuar intentando en la misma estación
                continue
        else:
            # Para estaciones de inspección, el resultado ya está incluido en el proceso
            if verificar_calidad_estacion(estacion, prob_rechazo):
                # Aprobado - registrar resultado
                log.append([
                    fecha_real.strftime("%Y-%m-%d %H:%M:%S"),
                    producto,
                    pid,
                    estacion,
                    dur,  # Solo tiempo de inspección
                    round(espera, 2),
                    intento_numero,
                    "APROBADO"
                ])
                return True, None
            else:
                # Rechazado - registrar resultado
                log.append([
                    fecha_real.strftime("%Y-%m-%d %H:%M:%S"),
                    producto,
                    pid,
                    estacion,
                    dur,  # Solo tiempo de inspección
                    round(espera, 2),
                    intento_numero,
                    "RECHAZADO"
                ])
                intento_local += 1
                # Si superó el máximo de intentos locales, salir
                if intento_local > max_intentos_local:
                    return False, estacion
                # Volver a procesar la inspección (nueva medición/verificación)
                continue
    
    # Si llegamos aquí, se agotaron los intentos locales
    return False, estacion

def proceso_producto(env, producto, pid, procesos_lista, estaciones, log, 
                    intento_numero=1, max_reprocesos=3):
    """Simula el flujo completo de UN producto con verificación en cada estación."""
    start_global = env.now
    
    for i, (estacion, base_t, cap, prob_rechazo) in enumerate(procesos_lista):
        # Procesar estación con verificación de calidad incorporada
        aprobado, estacion_rechazada = yield from procesar_estacion_con_calidad(
            env, producto, pid, estacion, base_t, prob_rechazo,
            estaciones, log, intento_numero
        )
        
        if not aprobado:
            # Producto rechazado en esta estación (agotó intentos locales)
            if intento_numero < max_reprocesos:
                # Determinar qué estaciones necesitan reproceso
                estaciones_reproceso = obtener_estaciones_para_reproceso(
                    producto, estacion_rechazada, procesos_lista
                )
                
                # Obtener procesos desde las estaciones que necesitan reproceso
                procesos_reproceso = obtener_procesos_desde_estaciones(
                    procesos_lista, estaciones_reproceso
                )
                
                # Reprocesar desde las estaciones necesarias
                env.process(
                    proceso_producto(
                        env, producto, pid, procesos_reproceso, estaciones, log,
                        intento_numero + 1, max_reprocesos
                    )
                )
                return  # Terminar este proceso, el reproceso se hará en otro
            else:
                # Máximo de reprocesos alcanzado
                log.append([
                    a_fecha_laboral(env.now).strftime("%Y-%m-%d %H:%M:%S"),
                    producto,
                    pid,
                    "DESCARTE DEFINITIVO",
                    0,
                    0,
                    intento_numero,
                    "DESCARTADO"
                ])
                return
    
    # Si llegamos aquí, todas las estaciones fueron aprobadas
    total = env.now - start_global
    log.append([
        a_fecha_laboral(env.now).strftime("%Y-%m-%d %H:%M:%S"),
        producto,
        pid,
        "PROCESO COMPLETADO",
        0,
        0,
        intento_numero,
        "COMPLETADO"
    ])
    return total

def run_simulacion():
    if SEED is not None:
        random.seed(SEED)

    env = simpy.Environment()

    # Crear recursos (máquinas) por nombre (compartidos si el nombre coincide)
    estaciones = {}
    for plist in PROCESOS.values():
        for est, t, cap, prob in plist:  # Ahora esperamos 4 valores
            if est not in estaciones:
                estaciones[est] = simpy.Resource(env, capacity=cap)

    log = []

    # Crear órdenes: todos los procesos arrancan en t=0 (simulación paralela)
    for producto, cantidad in ORDENES.items():
        for _ in range(cantidad):
            pid = str(uuid.uuid4())
            # Usar los procesos directamente (ya incluyen probabilidad)
            procesos_lista = PROCESOS[producto]
            
            env.process(
                proceso_producto(env, producto, pid, procesos_lista, estaciones, log)
            )

    env.run()

    return log

# ---------------------------
# EXPORT CSV
# ---------------------------
def exportar_csv(log, archivo="timeline_produccion.csv"):
    with open(archivo, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", 
            "producto", 
            "product_id", 
            "estacion", 
            "duracion_min", 
            "espera_min",
            "intento_numero",
            "estado_calidad"
        ])
        for fila in log:
            writer.writerow(fila)
    print(f"CSV generado: {archivo}")

# ---------------------------
# ESTADÍSTICAS DETALLADAS
# ---------------------------
def generar_estadisticas_detalladas(log):
    """Genera estadísticas detalladas sobre calidad y reprocesos."""
    estadisticas = {
        "por_producto": {},
        "por_estacion": {},
        "reprocesos_totales": 0,
        "descartes_totales": 0,
        "productos_completados": 0,
        "inspecciones": {
            "aprobadas": 0,
            "rechazadas": 0,
            "total": 0
        },
        "estaciones_proceso": {
            "aprobadas": 0,
            "rechazadas": 0,
            "total": 0
        }
    }
    
    # Identificar productos únicos
    productos_unicos = set()
    for fila in log:
        pid = fila[2]
        productos_unicos.add(pid)
    
    # Inicializar seguimiento por producto
    for pid in productos_unicos:
        estadisticas["por_producto"][pid] = {
            "estado_final": "PENDIENTE",
            "reprocesos": 0,
            "estaciones_rechazadas": [],
            "estaciones_aprobadas": []
        }
    
    # Procesar log para actualizar estados
    for fila in log:
        timestamp, producto, pid, estacion, duracion, espera, intento_numero, estado = fila
        
        if pid not in estadisticas["por_producto"]:
            continue
        
        # Actualizar estado final
        if estado == "COMPLETADO":
            estadisticas["por_producto"][pid]["estado_final"] = "COMPLETADO"
            estadisticas["productos_completados"] += 1
        elif estado == "DESCARTADO":
            estadisticas["por_producto"][pid]["estado_final"] = "DESCARTADO"
            estadisticas["descartes_totales"] += 1
        
        # Contar aprobaciones/rechazos por tipo de estación
        if estado == "APROBADO":
            estadisticas["por_producto"][pid]["estaciones_aprobadas"].append(estacion)
            if "Inspección" in estacion:
                estadisticas["inspecciones"]["aprobadas"] += 1
                estadisticas["inspecciones"]["total"] += 1
            else:
                estadisticas["estaciones_proceso"]["aprobadas"] += 1
                estadisticas["estaciones_proceso"]["total"] += 1
        
        elif estado == "RECHAZADO":
            estadisticas["por_producto"][pid]["estaciones_rechazadas"].append(estacion)
            if "Inspección" in estacion:
                estadisticas["inspecciones"]["rechazadas"] += 1
                estadisticas["inspecciones"]["total"] += 1
            else:
                estadisticas["estaciones_proceso"]["rechazadas"] += 1
                estadisticas["estaciones_proceso"]["total"] += 1
        
        # Contar reprocesos
        if estado == "DESCARTADO":
            # Contar intentos como reprocesos
            estadisticas["reprocesos_totales"] += intento_numero - 1
    
    # Imprimir reporte
    print("\n" + "="*60)
    print("REPORTE DETALLADO DE CALIDAD")
    print("="*60)
    
    print(f"\nProductos únicos simulados: {len(productos_unicos)}")
    print(f"Productos completados: {estadisticas['productos_completados']}")
    print(f"Productos descartados: {estadisticas['descartes_totales']}")
    print(f"Reprocesos totales: {estadisticas['reprocesos_totales']}")
    
    if len(productos_unicos) > 0:
        tasa_exito = estadisticas['productos_completados']/len(productos_unicos)*100
        print(f"\nTasa de éxito: {tasa_exito:.1f}%")
    
    # Estadísticas de estaciones de proceso
    if estadisticas["estaciones_proceso"]["total"] > 0:
        tasa_rechazo_proceso = estadisticas["estaciones_proceso"]["rechazadas"] / estadisticas["estaciones_proceso"]["total"] * 100
        print(f"\nEstaciones de proceso:")
        print(f"  Total verificaciones: {estadisticas['estaciones_proceso']['total']}")
        print(f"  Aprobadas: {estadisticas['estaciones_proceso']['aprobadas']}")
        print(f"  Rechazadas: {estadisticas['estaciones_proceso']['rechazadas']}")
        print(f"  Tasa de rechazo: {tasa_rechazo_proceso:.1f}%")
    
    # Estadísticas de inspecciones
    if estadisticas["inspecciones"]["total"] > 0:
        tasa_rechazo_inspecciones = estadisticas["inspecciones"]["rechazadas"] / estadisticas["inspecciones"]["total"] * 100
        print(f"\nEstaciones de inspección:")
        print(f"  Total inspecciones: {estadisticas['inspecciones']['total']}")
        print(f"  Aprobadas: {estadisticas['inspecciones']['aprobadas']}")
        print(f"  Rechazadas: {estadisticas['inspecciones']['rechazadas']}")
        print(f"  Tasa de rechazo: {tasa_rechazo_inspecciones:.1f}%")
    
    # Estadísticas adicionales por tipo de producto
    print("\n" + "-"*60)
    print("ESTADÍSTICAS POR TIPO DE PRODUCTO:")
    print("-"*60)
    
    productos_por_tipo = {}
    for fila in log:
        producto = fila[1]
        pid = fila[2]
        
        if producto not in productos_por_tipo:
            productos_por_tipo[producto] = set()
        productos_por_tipo[producto].add(pid)
    
    for producto, pids in productos_por_tipo.items():
        completados = 0
        descartados = 0
        
        for pid in pids:
            if pid in estadisticas["por_producto"]:
                if estadisticas["por_producto"][pid]["estado_final"] == "COMPLETADO":
                    completados += 1
                elif estadisticas["por_producto"][pid]["estado_final"] == "DESCARTADO":
                    descartados += 1
        
        print(f"\n{producto}:")
        print(f"  Total productos: {len(pids)}")
        print(f"  Completados: {completados}")
        print(f"  Descartados: {descartados}")
        if len(pids) > 0:
            tasa = completados/len(pids)*100
            print(f"  Tasa de éxito: {tasa:.1f}%")
    
    print("\n" + "="*60)

# ---------------------------
# EJECUCIÓN
# ---------------------------
if __name__ == "__main__":
    print("Iniciando simulación final...")
    print("NOTA: Solo estados APROBADO o RECHAZADO.")
    print("NOTA: Solo columna intento_numero (sin etapa_numero).")
    print("NOTA: Cada estación se procesa hasta que sale APROBADO (máx 3 intentos por estación).")
    print("NOTA: Cuando una inspección rechaza, se regresa a estaciones anteriores.")
    log = run_simulacion()
    exportar_csv(log)
    generar_estadisticas_detalladas(log)