-- Dragon Boat Analyzer - SQL DDL (SQLite)
-- Generado desde spec/dragonboat.dbml

-- Configuracion de la app (key-value)
CREATE TABLE app_settings (
    key VARCHAR(64) PRIMARY KEY,
    value VARCHAR(255) NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Catalogo de distancias
CREATE TABLE distancias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metros INTEGER UNIQUE NOT NULL,
    descripcion VARCHAR(50) NOT NULL,
    orden INTEGER NOT NULL
);

-- Sesiones diarias (un dia = un entreno)
CREATE TABLE sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE,
    categoria VARCHAR(50),
    tipo VARCHAR(20),
    distancia_total_nominal INTEGER DEFAULT 0 NOT NULL,
    distancia_total_real REAL DEFAULT 0.0 NOT NULL,
    num_pruebas INTEGER DEFAULT 0 NOT NULL,
    num_archivos INTEGER DEFAULT 0 NOT NULL,
    tiempo_total_entreno REAL,
    tiempo_parado REAL,
    tiempo_movimiento REAL,
    vel_media_movimiento REAL,
    vel_max_dia REAL,
    ritmo_medio REAL
);

-- Procedencia de CSVs subidos
CREATE TABLE csv_uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename VARCHAR(255) UNIQUE NOT NULL,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    file_path VARCHAR(255),
    kept BOOLEAN DEFAULT TRUE NOT NULL,
    metadata_date DATETIME,
    sesion_id INTEGER NOT NULL,
    FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
);

-- Datos GPS crudos (25Hz) por CSV
CREATE TABLE gps_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    csv_upload_id INTEGER UNIQUE NOT NULL,
    sesion_id INTEGER NOT NULL,
    data_json TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (csv_upload_id) REFERENCES csv_uploads(id) ON DELETE CASCADE,
    FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
);

-- Barcos
CREATE TABLE boats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(10) UNIQUE NOT NULL,
    display_name VARCHAR(50) NOT NULL,
    num_rows INTEGER NOT NULL,
    total_persons INTEGER NOT NULL
);

-- Tipos de prueba
CREATE TABLE test_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(20) UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Categorias
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Pruebas (un tramo = un test de velocidad)
CREATE TABLE test_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id INTEGER NOT NULL,
    csv_upload_id INTEGER,
    gps_data_id INTEGER,
    fecha_hora DATETIME NOT NULL,
    test_number INTEGER,
    custom_name VARCHAR(100),
    distancia_id INTEGER NOT NULL,
    boat_id INTEGER,
    tipo_id INTEGER,
    categoria_id INTEGER,
    chart_filename VARCHAR(255),
    gps_inicio TEXT,
    gps_fin TEXT,
    tiempos_por_distancia TEXT,
    tiempo_total REAL NOT NULL,
    velocidad_media REAL NOT NULL,
    velocidad_maxima REAL NOT NULL,
    velocidad_min_post10 REAL,
    aceleracion_max REAL NOT NULL,
    tiempo_12kmh REAL,
    num_paladas INTEGER NOT NULL,
    dist_media_palada REAL NOT NULL,
    dist_std_palada REAL NOT NULL,
    dist_max_palada REAL,
    dist_min_palada REAL,
    FOREIGN KEY (sesion_id) REFERENCES sesiones(id),
    FOREIGN KEY (csv_upload_id) REFERENCES csv_uploads(id),
    FOREIGN KEY (gps_data_id) REFERENCES gps_data(id) ON DELETE SET NULL,
    FOREIGN KEY (distancia_id) REFERENCES distancias(id),
    FOREIGN KEY (boat_id) REFERENCES boats(id),
    FOREIGN KEY (tipo_id) REFERENCES test_types(id),
    FOREIGN KEY (categoria_id) REFERENCES categories(id)
);

-- Tripulantes
CREATE TABLE crew_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    categoria VARCHAR(50),
    photo_path VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Asignacion de tripulacion por prueba
CREATE TABLE crew_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_metric_id INTEGER NOT NULL,
    crew_member_id INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,
    side VARCHAR(10),
    row_number INTEGER,
    FOREIGN KEY (test_metric_id) REFERENCES test_metrics(id) ON DELETE CASCADE,
    FOREIGN KEY (crew_member_id) REFERENCES crew_members(id),
    UNIQUE(test_metric_id, role, side, row_number)
);

-- Indices
CREATE INDEX idx_sesiones_fecha ON sesiones(fecha);
CREATE INDEX idx_csv_uploads_sesion ON csv_uploads(sesion_id);
CREATE INDEX idx_gps_data_sesion ON gps_data(sesion_id);
CREATE INDEX idx_test_metrics_sesion ON test_metrics(sesion_id);
CREATE INDEX idx_test_metrics_csv ON test_metrics(csv_upload_id);
CREATE INDEX idx_test_metrics_gps ON test_metrics(gps_data_id);
CREATE INDEX idx_test_metrics_fecha ON test_metrics(fecha_hora);
CREATE INDEX idx_crew_assignments_test ON crew_assignments(test_metric_id);
