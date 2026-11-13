-- ============================================================================
-- SIMTELE-RISK: Esquema Relacional de Base de Datos (PostgreSQL)
-- Descripción: Persistencia completa de casos de estudio, escenarios (3x4),
--              simulaciones, ejecuciones por método, iteraciones y análisis.
-- ============================================================================

-- Limpieza previa para reinicialización limpia
DROP TABLE IF EXISTS resultado_resumen CASCADE;
DROP TABLE IF EXISTS iteracion_resultado CASCADE;
DROP TABLE IF EXISTS ejecucion_metodo CASCADE;
DROP TABLE IF EXISTS simulacion CASCADE;
DROP TABLE IF EXISTS escenario CASCADE;
DROP TABLE IF EXISTS caso_estudio CASCADE;

-- ----------------------------------------------------------------------------
-- 1. ENTIDAD: caso_estudio
-- Almacena los 4 módulos obligatorios del sistema
-- ----------------------------------------------------------------------------
CREATE TABLE caso_estudio (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(30) UNIQUE NOT NULL,
    nombre VARCHAR(120) NOT NULL,
    descripcion TEXT NOT NULL,
    modelo_version VARCHAR(20) NOT NULL DEFAULT 'v1.0'
);

-- ----------------------------------------------------------------------------
-- 2. ENTIDAD: escenario
-- Configuraciones reproducibles NORMAL, ESTRES y MAL_CONDICIONADO por módulo
-- ----------------------------------------------------------------------------
CREATE TABLE escenario (
    id SERIAL PRIMARY KEY,
    caso_id INT NOT NULL REFERENCES caso_estudio(id) ON DELETE CASCADE,
    tipo VARCHAR(25) NOT NULL CHECK (tipo IN ('NORMAL', 'ESTRES', 'MAL_CONDICIONADO')),
    nombre_descriptivo VARCHAR(150) NOT NULL,
    parametros_json JSONB NOT NULL,
    fuente_datos VARCHAR(200) NOT NULL,
    es_predefinido BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_escenario_caso_tipo ON escenario(caso_id, tipo);

-- ----------------------------------------------------------------------------
-- 3. ENTIDAD: simulacion
-- Registra cada corrida lanzada por un usuario o equipo sobre un escenario
-- ----------------------------------------------------------------------------
CREATE TABLE simulacion (
    id SERIAL PRIMARY KEY,
    escenario_id INT NOT NULL REFERENCES escenario(id) ON DELETE CASCADE,
    fecha TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    usuario_equipo VARCHAR(100) NOT NULL DEFAULT 'Equipo_SIMTELE',
    estado VARCHAR(25) NOT NULL CHECK (estado IN ('EN_PROCESO', 'COMPLETADO', 'CON_ADVERTENCIAS', 'ERROR')),
    parametros_override_json JSONB, -- Guarda parámetros modificados manualmente en defensa
    notas_usuario TEXT
);

CREATE INDEX idx_simulacion_fecha ON simulacion(fecha DESC);
CREATE INDEX idx_simulacion_escenario ON simulacion(escenario_id);

-- ----------------------------------------------------------------------------
-- 4. ENTIDAD: ejecucion_metodo
-- Detalla cada algoritmo numérico ejecutado dentro de una simulación
-- ----------------------------------------------------------------------------
CREATE TABLE ejecucion_metodo (
    id SERIAL PRIMARY KEY,
    simulacion_id INT NOT NULL REFERENCES simulacion(id) ON DELETE CASCADE,
    familia_metodo VARCHAR(30) NOT NULL CHECK (
        familia_metodo IN ('SISTEMAS_LINEALES', 'INTERPOLACION', 'RAICES', 'INTEGRACION', 'EDO')
    ),
    metodo VARCHAR(60) NOT NULL,
    tolerancia DOUBLE PRECISION,
    paso DOUBLE PRECISION,
    max_iter INT,
    iteraciones_realizadas INT NOT NULL DEFAULT 0,
    convergio BOOLEAN NOT NULL,
    motivo_parada VARCHAR(150),
    tiempo_ms DOUBLE PRECISION NOT NULL CHECK (tiempo_ms >= 0)
);

CREATE INDEX idx_ejecucion_simulacion ON ejecucion_metodo(simulacion_id);

-- ----------------------------------------------------------------------------
-- 5. ENTIDAD: iteracion_resultado
-- Traza paso a paso (iteración, refinamiento o paso temporal) de cada ejecución
-- ----------------------------------------------------------------------------
CREATE TABLE iteracion_resultado (
    id BIGSERIAL PRIMARY KEY,
    ejecucion_id INT NOT NULL REFERENCES ejecucion_metodo(id) ON DELETE CASCADE,
    numero INT NOT NULL,
    aproximacion_json JSONB NOT NULL, -- Escalares, vectores [x1, x2...] o puntos (t, x, v)
    residual DOUBLE PRECISION,
    error_abs DOUBLE PRECISION,
    error_rel DOUBLE PRECISION,
    error_porcentual DOUBLE PRECISION
);

CREATE INDEX idx_iteracion_ejecucion_num ON iteracion_resultado(ejecucion_id, numero);

-- ----------------------------------------------------------------------------
-- 6. ENTIDAD: resultado_resumen
-- Consolidado final, referencia analítica, errores globales y dobles conclusiones
-- ----------------------------------------------------------------------------
CREATE TABLE resultado_resumen (
    id SERIAL PRIMARY KEY,
    ejecucion_id INT UNIQUE NOT NULL REFERENCES ejecucion_metodo(id) ON DELETE CASCADE,
    referencia DOUBLE PRECISION,
    tipo_referencia VARCHAR(40) NOT NULL CHECK (tipo_referencia IN ('ANALITICA', 'NUMERICA_ALTA_PRECISION')),
    valor_json JSONB NOT NULL,
    metrica_error_json JSONB NOT NULL, -- Contiene E_abs, E_rel, E_pct, residual, kappa_A, sensibilidad
    interpretacion_numerica TEXT NOT NULL,
    interpretacion_problema TEXT NOT NULL
);

-- ============================================================================
-- DATOS SEMILLA: 4 Módulos Obligatorios y 12 Escenarios Base (3 x 4)
-- ============================================================================

INSERT INTO caso_estudio (id, codigo, nombre, descripcion, modelo_version) VALUES
(1, 'MOD1_DETENCION', 'Detención de Emergencia de Cabinas', 'Modelado cinemático y dinámico de frenado de emergencia mediante EDO, integración de velocidad y búsqueda de instante de detención.', 'v1.0'),
(2, 'MOD2_DETERIORO', 'Deterioro Mecánico y Mantenimiento', 'Calibración de modelo polinómico de desgaste mediante sistemas lineales SPD y predicción de tiempo a umbral crítico.', 'v1.0'),
(3, 'MOD3_OSCILACIONES', 'Oscilaciones por Viento', 'Simulación de respuesta dinámica amortiguada ante ráfagas de viento e integración de energía acumulada.', 'v1.0'),
(4, 'MOD4_SENSORES', 'Reconstrucción de Señales de Sensores', 'Interpolación de telemetría con datos ocultados, evaluación de ruido y detección de cruce de umbrales.', 'v1.0');

SELECT setval('caso_estudio_id_seq', 4);

-- Escenarios Módulo 1: Detención de Emergencia
INSERT INTO escenario (caso_id, tipo, nombre_descriptivo, parametros_json, fuente_datos) VALUES
(1, 'NORMAL', 'Frenado nominal en tramo recto', '{"v0": 6.0, "x0": 0.0, "a0": 1.2, "kd": 0.0, "h": 0.05, "t_max": 10.0, "tol": 1e-8}', 'Parámetros sintéticos nominales de cabina urbana'),
(1, 'ESTRES', 'Carga máxima, pendiente descendente y paso grueso', '{"v0": 8.5, "x0": 0.0, "a0": 0.75, "kd": 0.02, "h": 0.4, "t_max": 15.0, "tol": 1e-8}', 'Simulación sintética de demanda pico con paso de integración exigente'),
(1, 'MAL_CONDICIONADO', 'Frenado asintótico con raíz múltiple (derivada nula)', '{"v0": 6.0, "x0": 0.0, "modelo": "asintotico_tangencial", "t_det_objetivo": 5.0, "h": 0.05, "tol": 1e-10}', 'Subexperimento numérico con v(t_det)=0 y dv/dt(t_det)=0');

-- Escenarios Módulo 2: Deterioro Mecánico
INSERT INTO escenario (caso_id, tipo, nombre_descriptivo, parametros_json, fuente_datos) VALUES
(2, 'NORMAL', 'Calibración SPD bien condicionada y desgaste estándar', '{"dimension_n": 4, "condicion_objetivo": "baja", "D0": 0.12, "alpha": 0.015, "beta": 0.0008, "D_umbral": 0.80, "tol": 1e-8, "max_iter": 500}', 'Serie sintética de inspección preventiva trimestral'),
(2, 'ESTRES', 'Sistema ampliado (n=10) y mantenimiento retrasado', '{"dimension_n": 10, "condicion_objetivo": "moderada", "D0": 0.25, "alpha": 0.028, "beta": 0.0019, "D_umbral": 0.85, "tol": 1e-11, "max_iter": 2000}', 'Escenario sintético de operación continua sin ventana de mantenimiento'),
(2, 'MAL_CONDICIONADO', 'Matriz SPD casi singular (tipo Hilbert perturbada)', '{"dimension_n": 6, "condicion_objetivo": "alta_hilbert", "perturbacion_b": 1e-4, "D0": 0.12, "alpha": 0.015, "beta": 0.0008, "D_umbral": 0.80, "tol": 1e-8, "max_iter": 5000}', 'Subexperimento numérico con número de condición kappa(A) > 10^6');

-- Escenarios Módulo 3: Oscilaciones por Viento
INSERT INTO escenario (caso_id, tipo, nombre_descriptivo, parametros_json, fuente_datos) VALUES
(3, 'NORMAL', 'Vibración subamortiguada con brisa moderada', '{"m": 1200.0, "c": 480.0, "k": 3000.0, "F0": 150.0, "omega": 0.8, "x0": 0.05, "v0": 0.0, "h": 0.02, "T": 20.0}', 'Modelo masa-resorte-amortiguador sintético equivalente'),
(3, 'ESTRES', 'Ráfagas cercanas a resonancia en ventana prolongada', '{"m": 1200.0, "c": 180.0, "k": 3000.0, "F0": 850.0, "omega": 1.55, "x0": 0.10, "v0": 0.0, "h": 0.05, "T": 120.0}', 'Forzamiento armónico sintético cerca de frecuencia natural'),
(3, 'MAL_CONDICIONADO', 'Sistema rígido (stiff) con alta rigidez y paso crítico', '{"m": 1200.0, "c": 2400.0, "k": 450000.0, "F0": 200.0, "omega": 2.0, "x0": 0.05, "v0": 0.0, "h": 0.12, "T": 10.0}', 'Subexperimento numérico para demostrar límite de estabilidad explícita RK2/RK4');

-- Escenarios Módulo 4: Reconstrucción de Sensores
INSERT INTO escenario (caso_id, tipo, nombre_descriptivo, parametros_json, fuente_datos) VALUES
(4, 'NORMAL', 'Telemetría limpia con 8 nodos equiespaciados', '{"funcion": "sin_t", "a": 0.0, "b": 6.283185307179586, "n_nodos": 8, "indices_ocultos": [2, 5], "ruido_sigma": 0.0, "umbral_alerta": 0.75}', 'Señal sintética analítica y(t) = sin(t)'),
(4, 'ESTRES', 'Señal amortiguada con ruido gaussiano y pérdida de paquetes', '{"funcion": "exp_cos", "a": 0.0, "b": 5.0, "n_nodos": 12, "indices_ocultos": [3, 4, 7, 8], "ruido_sigma": 0.04, "umbral_alerta": 0.50}', 'Señal sintética y(t) = exp(-t)*cos(2t) contaminada con ruido normal'),
(4, 'MAL_CONDICIONADO', 'Fenómeno de Runge con nodos equiespaciados de alto grado', '{"funcion": "runge", "a": -5.0, "b": 5.0, "n_nodos": 15, "indices_ocultos": [1, 13], "ruido_sigma": 0.0, "umbral_alerta": 0.50}', 'Subexperimento numérico con f(t) = 1 / (1 + 25*t^2) en [-5, 5]');