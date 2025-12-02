"""
Simulador de fallas aleatorias en estaciones de producción.
Genera un CSV con fechas de falla y reparación para cada estación.
Versión simplificada sin impresiones extensas.
"""

import csv
import random
from datetime import datetime, timedelta
import uuid
import locale

# Configurar locale para formato de números con comas decimales
locale.setlocale(locale.LC_NUMERIC, 'es_ES.UTF-8')

# ---------------------------
# CONFIGURACIÓN PRINCIPAL
# ---------------------------
# Fecha de inicio y fin de la simulación de fallas
FECHA_INICIO = datetime(2025, 1, 2, 8, 0, 0)
FECHA_FIN = datetime(2025, 12, 31, 17, 0, 0)

# ---------------------------
# CONFIGURACIÓN POR ESTACIÓN (AJUSTA AQUÍ)
# ---------------------------
# PROBABILIDAD DE FALLA POR ESTACIÓN (por día de operación)
PROBABILIDAD_FALLA_POR_ESTACION = {
    "Corte Material": 0.001,         
    "Mecanizado Rueda": 0.023,        
    "Mecanizado Piñón": 0.025,        
    "Cilindrado Material": 0.018,     
    "CNC Dientes Rueda": 0.024,        
    "Tallado Piñón": 0.013,           
    "Torneado Tornillo Sinfín": 0.013, 
    "Fresado Cuñero": 0.017,           
    "Tratamiento Térmico": 0.001,      
    "Rectificado Dientes": 0.015,   
    "Inspección Software": 0.001,                       
}

# TIEMPO PROMEDIO DE REPARACIÓN POR ESTACIÓN (en horas)
TIEMPO_REPARACION_POR_ESTACION = {
    "Corte Material": 16.5,
    "Mecanizado Rueda": 14.0,
    "Mecanizado Piñón": 15.5,
    "Cilindrado Material": 14.0,
    "CNC Dientes Rueda": 15.0,
    "Tallado Piñón": 8.5,
    "Torneado Tornillo Sinfín": 14.0,
    "Fresado Cuñero": 13.0,
    "Tratamiento Térmico": 8.0,
    "Rectificado Dientes": 15.5,
    "Inspección Software": 14.0,
}

# DESVIACIÓN ESTÁNDAR DE REPARACIÓN
DESVIACION_REPARACION = 0.3

# PROBABILIDAD DE FALLA GRAVE POR ESTACIÓN
PROBABILIDAD_FALLA_GRAVE_POR_ESTACION = {
    "Corte Material": 0.2,
    "Mecanizado Rueda": 0.25,
    "Mecanizado Piñón": 0.22,
    "Cilindrado Material": 0.15,
    "CNC Dientes Rueda": 0.35,
    "Tallado Piñón": 0.3,
    "Torneado Tornillo Sinfín": 0.25,
    "Fresado Cuñero": 0.18,
    "Tratamiento Térmico": 0.4,
    "Rectificado Dientes": 0.35,
    "Inspección Software": 0.1,
}

# FACTOR DE TIEMPO PARA FALLAS GRAVES
FACTOR_FALLA_GRAVE = 2.5

# ---------------------------
# CONFIGURACIÓN GENERAL
# ---------------------------
HORA_INICIO_JORNADA = 8
HORA_FIN_JORNADA = 17
DIAS_NO_HABILES = [5, 6]  # Sábado, Domingo

DIAS_FERIADOS = [
    "2025-01-01", "2025-01-06", "2025-03-24", "2025-03-28",
    "2025-05-01", "2025-05-25", "2025-06-20", "2025-07-09",
    "2025-08-17", "2025-10-12", "2025-11-20", "2025-12-08",
    "2025-12-25"
]

# ---------------------------
# FUNCIONES AUXILIARES
# ---------------------------
def es_dia_habil(fecha):
    """Devuelve True si la fecha es día hábil."""
    if fecha.weekday() in DIAS_NO_HABILES:
        return False
    fecha_str = fecha.strftime("%Y-%m-%d")
    if fecha_str in DIAS_FERIADOS:
        return False
    return True

def siguiente_dia_habil(fecha):
    """Devuelve la siguiente fecha hábil."""
    fecha_temp = fecha
    while True:
        fecha_temp += timedelta(days=1)
        if es_dia_habil(fecha_temp):
            return fecha_temp

def ajustar_a_horario_laboral(fecha):
    """Ajusta una fecha al horario laboral más cercano."""
    while not es_dia_habil(fecha):
        fecha = siguiente_dia_habil(fecha)
        fecha = fecha.replace(hour=HORA_INICIO_JORNADA, minute=0, second=0)
    
    if fecha.hour < HORA_INICIO_JORNADA:
        fecha = fecha.replace(hour=HORA_INICIO_JORNADA, minute=0, second=0)
    elif fecha.hour >= HORA_FIN_JORNADA:
        fecha = siguiente_dia_habil(fecha)
        fecha = fecha.replace(hour=HORA_INICIO_JORNADA, minute=0, second=0)
    
    return fecha

def generar_dias_hasta_falla(probabilidad_diaria):
    """Genera días hasta la próxima falla basado en probabilidad diaria."""
    dias_sin_falla = 0
    
    while True:
        if random.random() < probabilidad_diaria:
            return dias_sin_falla + 1
        dias_sin_falla += 1
        
        if dias_sin_falla > 365:
            return 365

def generar_tiempo_reparacion(estacion, es_grave):
    """Genera tiempo de reparación para una estación específica."""
    tiempo_base = TIEMPO_REPARACION_POR_ESTACION.get(estacion, 2.0)
    
    if es_grave:
        tiempo_base *= FACTOR_FALLA_GRAVE
    
    tiempo = random.gauss(tiempo_base, tiempo_base * DESVIACION_REPARACION)
    return max(0.25, tiempo)

def formato_decimal(numero):
    """Formatea un número decimal con coma como separador decimal."""
    # Usar locale para formato correcto
    try:
        return locale.format_string("%.2f", numero, grouping=False)
    except:
        # Fallback si locale no funciona
        return f"{numero:.2f}".replace('.', ',')

def simular_fallas_estacion(estacion, fecha_inicio, fecha_fin):
    """Simula fallas para una estación específica."""
    fallas = []
    fecha_actual = fecha_inicio
    
    probabilidad_diaria = PROBABILIDAD_FALLA_POR_ESTACION.get(estacion, 0.02)
    prob_falla_grave = PROBABILIDAD_FALLA_GRAVE_POR_ESTACION.get(estacion, 0.3)
    
    while fecha_actual < fecha_fin:
        dias_hasta_falla = generar_dias_hasta_falla(probabilidad_diaria)
        fecha_falla = fecha_actual + timedelta(days=dias_hasta_falla)
        
        if fecha_falla >= fecha_fin:
            break
        
        fecha_falla = ajustar_a_horario_laboral(fecha_falla)
        es_grave = random.random() < prob_falla_grave
        horas_reparacion = generar_tiempo_reparacion(estacion, es_grave)
        fecha_reparacion = fecha_falla + timedelta(hours=horas_reparacion)
        
        # Ajustar fecha de reparación
        while True:
            while not es_dia_habil(fecha_reparacion):
                fecha_reparacion = siguiente_dia_habil(fecha_reparacion)
                fecha_reparacion = fecha_reparacion.replace(hour=HORA_INICIO_JORNADA, minute=0, second=0)
            
            if HORA_INICIO_JORNADA <= fecha_reparacion.hour < HORA_FIN_JORNADA:
                break
            else:
                if fecha_reparacion.hour < HORA_INICIO_JORNADA:
                    fecha_reparacion = fecha_reparacion.replace(hour=HORA_INICIO_JORNADA, minute=0, second=0)
                else:
                    horas_extras = (fecha_reparacion.hour - HORA_FIN_JORNADA) + (fecha_reparacion.minute / 60)
                    fecha_reparacion = siguiente_dia_habil(fecha_reparacion)
                    horas_enteras = int(horas_extras)
                    minutos_enteros = int((horas_extras - horas_enteras) * 60)
                    hora_final = HORA_INICIO_JORNADA + horas_enteras
                    if hora_final >= HORA_FIN_JORNADA:
                        fecha_reparacion = siguiente_dia_habil(fecha_reparacion)
                        hora_final = HORA_INICIO_JORNADA + (hora_final - HORA_FIN_JORNADA)
                    fecha_reparacion = fecha_reparacion.replace(hour=hora_final, minute=minutos_enteros, second=0)
        
        if fecha_reparacion > fecha_fin:
            fecha_reparacion = fecha_fin
        
        falla_id = f"{estacion[:3].upper()}-{str(uuid.uuid4())[:6].upper()}"
        tipo_falla = "GRAVE" if es_grave else "LEVE"
        
        # Usar formato_decimal para números con comas
        duracion_formateada = formato_decimal(horas_reparacion)
        
        fallas.append({
            "falla_id": falla_id,
            "estacion": estacion,
            "fecha_falla": fecha_falla,
            "fecha_reparacion": fecha_reparacion,
            "duracion_horas": duracion_formateada,
            "tipo_falla": tipo_falla,
            "dias_desde_ultima_falla": formato_decimal(dias_hasta_falla)
        })
        
        fecha_actual = fecha_reparacion
    
    return fallas

def simular_todas_fallas():
    """Simula fallas para todas las estaciones."""
    todas_fallas = []
    
    for estacion in PROBABILIDAD_FALLA_POR_ESTACION:
        fallas_estacion = simular_fallas_estacion(estacion, FECHA_INICIO, FECHA_FIN)
        todas_fallas.extend(fallas_estacion)
    
    return todas_fallas

def exportar_csv(fallas, archivo="fallas_estaciones.csv"):
    """Exporta las fallas a un archivo CSV con punto y coma como separador."""
    if not fallas:
        print("No se generaron fallas para exportar.")
        return
    
    with open(archivo, "w", newline="", encoding="utf-8") as f:
        # Usar punto y coma como delimitador y comas como separador decimal
        writer = csv.writer(f, delimiter=';')
        
        # Encabezados simplificados
        writer.writerow([
            "falla_id",
            "estacion",
            "fecha_falla",
            "hora_falla",
            "fecha_reparacion",
            "hora_reparacion",
            "duracion_horas",
            "tipo_falla"
        ])
        
        # Datos - ya están formateados con comas decimales
        for falla in fallas:
            writer.writerow([
                falla["falla_id"],
                falla["estacion"],
                falla["fecha_falla"].strftime("%Y-%m-%d"),
                falla["fecha_falla"].strftime("%H:%M"),
                falla["fecha_reparacion"].strftime("%Y-%m-%d"),
                falla["fecha_reparacion"].strftime("%H:%M"),
                falla["duracion_horas"],  # Ya formateado con coma
                falla["tipo_falla"]
            ])
    
    print(f"CSV generado: {archivo}")
    print(f"Total de fallas registradas: {len(fallas)}")

# ---------------------------
# EJECUCIÓN PRINCIPAL
# ---------------------------
if __name__ == "__main__":
    print("Generando simulación de fallas...")
    fallas = simular_todas_fallas()
    
    if fallas:
        exportar_csv(fallas)
        print("Simulación completada exitosamente.")
    else:
        print("No se generaron fallas en la simulación.")