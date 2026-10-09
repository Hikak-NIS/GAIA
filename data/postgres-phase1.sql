BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 38f52bd3d794

CREATE TABLE login_attempts (
    key VARCHAR(64) NOT NULL, 
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_login_attempts_key ON login_attempts (key);

CREATE INDEX ix_login_attempts_timestamp ON login_attempts (timestamp);

CREATE TABLE users (
    name VARCHAR(100) NOT NULL, 
    email VARCHAR(254) NOT NULL, 
    password_hash VARCHAR(255) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE auth_sessions (
    user_id VARCHAR(36) NOT NULL, 
    token_hash VARCHAR(64) NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    UNIQUE (token_hash)
);

CREATE INDEX ix_auth_sessions_user_id ON auth_sessions (user_id);

CREATE TABLE territories (
    owner_id VARCHAR(36) NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    description TEXT NOT NULL, 
    latitude FLOAT NOT NULL, 
    longitude FLOAT NOT NULL, 
    polygon JSON, 
    area FLOAT NOT NULL, 
    timezone VARCHAR(64) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_territories_owner_id ON territories (owner_id);

CREATE TABLE alerts (
    code VARCHAR(40) NOT NULL, 
    severity VARCHAR(20) NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    title VARCHAR(200) NOT NULL, 
    explanation TEXT NOT NULL, 
    recommendation TEXT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    resolved_at TIMESTAMP WITH TIME ZONE, 
    territory_id VARCHAR(36) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(territory_id) REFERENCES territories (id) ON DELETE CASCADE
);

CREATE INDEX ix_alerts_code ON alerts (code);

CREATE INDEX ix_alerts_territory_id ON alerts (territory_id);

CREATE TABLE daily_reports (
    period_start TIMESTAMP WITH TIME ZONE NOT NULL, 
    period_end TIMESTAMP WITH TIME ZONE NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    data JSON NOT NULL, 
    territory_id VARCHAR(36) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(territory_id) REFERENCES territories (id) ON DELETE CASCADE
);

CREATE INDEX ix_daily_reports_territory_id ON daily_reports (territory_id);

CREATE TABLE irrigation_events (
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL, 
    mode VARCHAR(20) NOT NULL, 
    action VARCHAR(30) NOT NULL, 
    reason TEXT NOT NULL, 
    trigger_value FLOAT, 
    target_value FLOAT NOT NULL, 
    duration_s FLOAT NOT NULL, 
    estimated_water_l FLOAT NOT NULL, 
    actor VARCHAR(20) NOT NULL, 
    territory_id VARCHAR(36) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(territory_id) REFERENCES territories (id) ON DELETE CASCADE
);

CREATE INDEX ix_irrigation_events_territory_id ON irrigation_events (territory_id);

CREATE INDEX ix_irrigation_events_timestamp ON irrigation_events (timestamp);

CREATE TABLE irrigation_rules (
    mode VARCHAR(20) NOT NULL, 
    trigger_pct FLOAT NOT NULL, 
    target_pct FLOAT NOT NULL, 
    max_duration_s INTEGER NOT NULL, 
    cooldown_s INTEGER NOT NULL, 
    daily_limit_l FLOAT NOT NULL, 
    min_reservoir_l FLOAT NOT NULL, 
    block_rain BOOLEAN NOT NULL, 
    rain_threshold_pct FLOAT NOT NULL, 
    territory_id VARCHAR(36) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(territory_id) REFERENCES territories (id) ON DELETE CASCADE, 
    UNIQUE (territory_id)
);

CREATE INDEX ix_irrigation_rules_territory_id ON irrigation_rules (territory_id);

CREATE TABLE irrigation_zones (
    name VARCHAR(100) NOT NULL, 
    pump_on BOOLEAN NOT NULL, 
    emergency BOOLEAN NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE, 
    stopped_at TIMESTAMP WITH TIME ZONE, 
    deadline TIMESTAMP WITH TIME ZONE, 
    run_water_l FLOAT NOT NULL, 
    daily_water_l FLOAT NOT NULL, 
    water_day VARCHAR(10) NOT NULL, 
    territory_id VARCHAR(36) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(territory_id) REFERENCES territories (id) ON DELETE CASCADE, 
    UNIQUE (territory_id)
);

CREATE INDEX ix_irrigation_zones_territory_id ON irrigation_zones (territory_id);

CREATE TABLE observations (
    source VARCHAR(20) NOT NULL, 
    category VARCHAR(20) NOT NULL, 
    severity VARCHAR(20) NOT NULL, 
    text TEXT NOT NULL, 
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL, 
    latitude FLOAT NOT NULL, 
    longitude FLOAT NOT NULL, 
    photo_path VARCHAR(100), 
    territory_id VARCHAR(36) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(territory_id) REFERENCES territories (id) ON DELETE CASCADE
);

CREATE INDEX ix_observations_territory_id ON observations (territory_id);

CREATE TABLE satellite_layers (
    source VARCHAR(20) NOT NULL, 
    provider VARCHAR(50) NOT NULL, 
    layer VARCHAR(100) NOT NULL, 
    resolution_m INTEGER NOT NULL, 
    territory_id VARCHAR(36) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(territory_id) REFERENCES territories (id) ON DELETE CASCADE
);

CREATE INDEX ix_satellite_layers_territory_id ON satellite_layers (territory_id);

CREATE TABLE sensors (
    name VARCHAR(100) NOT NULL, 
    source VARCHAR(20) NOT NULL, 
    credential_hash VARCHAR(64), 
    territory_id VARCHAR(36) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(territory_id) REFERENCES territories (id) ON DELETE CASCADE, 
    UNIQUE (credential_hash)
);

CREATE INDEX ix_sensors_territory_id ON sensors (territory_id);

CREATE TABLE simulation_sessions (
    status VARCHAR(20) NOT NULL, 
    scenario VARCHAR(30) NOT NULL, 
    seed INTEGER NOT NULL, 
    speed INTEGER NOT NULL, 
    tick_index INTEGER NOT NULL, 
    clock TIMESTAMP WITH TIME ZONE NOT NULL, 
    soil FLOAT NOT NULL, 
    reservoir_l FLOAT NOT NULL, 
    total_water_l FLOAT NOT NULL, 
    territory_id VARCHAR(36) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(territory_id) REFERENCES territories (id) ON DELETE CASCADE, 
    UNIQUE (territory_id)
);

CREATE INDEX ix_simulation_sessions_territory_id ON simulation_sessions (territory_id);

CREATE TABLE weather_snapshots (
    source VARCHAR(20) NOT NULL, 
    fetched_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    data JSON NOT NULL, 
    territory_id VARCHAR(36) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(territory_id) REFERENCES territories (id) ON DELETE CASCADE
);

CREATE INDEX ix_weather_snapshots_territory_id ON weather_snapshots (territory_id);

CREATE TABLE sensor_readings (
    sensor_id VARCHAR(36) NOT NULL, 
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL, 
    received_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    source VARCHAR(20) NOT NULL, 
    air_temperature_c FLOAT, 
    air_humidity_pct FLOAT, 
    soil_moisture_pct FLOAT, 
    light_lux FLOAT, 
    pressure_hpa FLOAT, 
    battery_pct FLOAT, 
    quality VARCHAR(20) NOT NULL, 
    raw_metadata JSON NOT NULL, 
    territory_id VARCHAR(36) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(sensor_id) REFERENCES sensors (id) ON DELETE CASCADE, 
    FOREIGN KEY(territory_id) REFERENCES territories (id) ON DELETE CASCADE
);

CREATE INDEX ix_sensor_readings_sensor_id ON sensor_readings (sensor_id);

CREATE INDEX ix_sensor_readings_territory_id ON sensor_readings (territory_id);

CREATE INDEX ix_sensor_readings_timestamp ON sensor_readings (timestamp);

INSERT INTO alembic_version (version_num) VALUES ('38f52bd3d794') RETURNING alembic_version.version_num;

-- Running upgrade 38f52bd3d794 -> fac35c316e52

UPDATE alembic_version SET version_num='fac35c316e52' WHERE alembic_version.version_num = '38f52bd3d794';

-- Running upgrade fac35c316e52 -> 10f579997c3a

CREATE UNIQUE INDEX IF NOT EXISTS uq_alerts_active_code ON alerts (territory_id, code) WHERE status = 'active';

ALTER TABLE sensor_readings ADD CONSTRAINT uq_sensor_readings_sensor_timestamp UNIQUE (sensor_id, timestamp);

ALTER TABLE sensors ADD CONSTRAINT uq_sensors_territory_source UNIQUE (territory_id, source);

UPDATE alembic_version SET version_num='10f579997c3a' WHERE alembic_version.version_num = 'fac35c316e52';

-- Running upgrade 10f579997c3a -> 7b94d6120344

CREATE TABLE plant_profiles (
    owner_id VARCHAR(36) NOT NULL, 
    common_name VARCHAR(100) NOT NULL, 
    scientific_name VARCHAR(200) NOT NULL, 
    description TEXT NOT NULL, 
    soil_moisture_min FLOAT, 
    soil_moisture_max FLOAT, 
    temperature_min FLOAT, 
    temperature_max FLOAT, 
    humidity_min FLOAT, 
    humidity_max FLOAT, 
    ph_min FLOAT, 
    ph_max FLOAT, 
    light_requirements TEXT NOT NULL, 
    irrigation_requirements TEXT NOT NULL, 
    nutrient_requirements TEXT NOT NULL, 
    common_diseases JSON NOT NULL, 
    stage_requirements JSON NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_plant_profiles_owner_id ON plant_profiles (owner_id);

CREATE TABLE zones (
    name VARCHAR(100) NOT NULL, 
    description TEXT NOT NULL, 
    is_default BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    territory_id VARCHAR(36) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(territory_id) REFERENCES territories (id) ON DELETE CASCADE
);

CREATE INDEX ix_zones_territory_id ON zones (territory_id);

CREATE UNIQUE INDEX uq_zones_default ON zones (territory_id) WHERE is_default = true;

CREATE TABLE devices (
    zone_id VARCHAR(36) NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    device_type VARCHAR(20) NOT NULL, 
    source VARCHAR(20) NOT NULL, 
    active BOOLEAN NOT NULL, 
    legacy_sensor_id VARCHAR(36), 
    legacy_irrigation_id VARCHAR(36), 
    actuator_type VARCHAR(30), 
    last_seen TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    territory_id VARCHAR(36) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(legacy_irrigation_id) REFERENCES irrigation_zones (id), 
    FOREIGN KEY(legacy_sensor_id) REFERENCES sensors (id), 
    FOREIGN KEY(territory_id) REFERENCES territories (id) ON DELETE CASCADE, 
    FOREIGN KEY(zone_id) REFERENCES zones (id), 
    UNIQUE (legacy_irrigation_id), 
    UNIQUE (legacy_sensor_id)
);

CREATE INDEX ix_devices_territory_id ON devices (territory_id);

CREATE INDEX ix_devices_zone_id ON devices (zone_id);

CREATE TABLE plant_instances (
    profile_id VARCHAR(36) NOT NULL, 
    zone_id VARCHAR(36) NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    planted_on DATE, 
    growth_stage VARCHAR(20) NOT NULL, 
    health_status VARCHAR(20) NOT NULL, 
    camera_device_id VARCHAR(36), 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    territory_id VARCHAR(36) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(camera_device_id) REFERENCES devices (id), 
    FOREIGN KEY(profile_id) REFERENCES plant_profiles (id), 
    FOREIGN KEY(territory_id) REFERENCES territories (id) ON DELETE CASCADE, 
    FOREIGN KEY(zone_id) REFERENCES zones (id)
);

CREATE INDEX ix_plant_instances_profile_id ON plant_instances (profile_id);

CREATE INDEX ix_plant_instances_territory_id ON plant_instances (territory_id);

CREATE INDEX ix_plant_instances_zone_id ON plant_instances (zone_id);

CREATE TABLE sensor_channels (
    device_id VARCHAR(36) NOT NULL, 
    sensor_type VARCHAR(40) NOT NULL, 
    unit VARCHAR(20) NOT NULL, 
    calibration JSON NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(device_id) REFERENCES devices (id) ON DELETE CASCADE, 
    CONSTRAINT uq_device_channel UNIQUE (device_id, sensor_type)
);

CREATE INDEX ix_sensor_channels_device_id ON sensor_channels (device_id);

CREATE TABLE plant_sensor_links (
    plant_id VARCHAR(36) NOT NULL, 
    channel_id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (plant_id, channel_id), 
    FOREIGN KEY(channel_id) REFERENCES sensor_channels (id), 
    FOREIGN KEY(plant_id) REFERENCES plant_instances (id) ON DELETE CASCADE
);

ALTER TABLE sensors DROP CONSTRAINT uq_sensors_territory_source;

INSERT INTO zones (id, territory_id, name, description, is_default, created_at, updated_at)
        SELECT id, id, 'Основная зона', '', true, created_at, updated_at FROM territories;

INSERT INTO devices
        (id, territory_id, zone_id, name, device_type, source, active, legacy_sensor_id,
         legacy_irrigation_id, actuator_type, last_seen, created_at, updated_at)
        SELECT s.id, s.territory_id, s.territory_id, s.name, 'SENSOR',
               CASE WHEN s.source = 'simulated' THEN 'SIMULATED' ELSE 'REAL' END, true, s.id,
               NULL, NULL, (SELECT MAX(r.received_at) FROM sensor_readings r WHERE r.sensor_id = s.id),
               t.created_at, t.updated_at FROM sensors s JOIN territories t ON t.id = s.territory_id;

INSERT INTO devices
        (id, territory_id, zone_id, name, device_type, source, active, legacy_sensor_id,
         legacy_irrigation_id, actuator_type, last_seen, created_at, updated_at)
        SELECT i.id, i.territory_id, i.territory_id, 'Виртуальный насос', 'ACTUATOR', 'SIMULATED',
               true, NULL, i.id, 'PUMP', NULL, t.created_at, t.updated_at
        FROM irrigation_zones i JOIN territories t ON t.id = i.territory_id;

INSERT INTO sensor_channels (id, device_id, sensor_type, unit, calibration)
            SELECT CAST(gen_random_uuid() AS varchar(36)), id, 'air_temperature_c', '°C', '{}' FROM devices WHERE device_type = 'SENSOR';

INSERT INTO sensor_channels (id, device_id, sensor_type, unit, calibration)
            SELECT CAST(gen_random_uuid() AS varchar(36)), id, 'air_humidity_pct', '%', '{}' FROM devices WHERE device_type = 'SENSOR';

INSERT INTO sensor_channels (id, device_id, sensor_type, unit, calibration)
            SELECT CAST(gen_random_uuid() AS varchar(36)), id, 'soil_moisture_pct', '%', '{}' FROM devices WHERE device_type = 'SENSOR';

INSERT INTO sensor_channels (id, device_id, sensor_type, unit, calibration)
            SELECT CAST(gen_random_uuid() AS varchar(36)), id, 'light_lux', 'lx', '{}' FROM devices WHERE device_type = 'SENSOR';

INSERT INTO sensor_channels (id, device_id, sensor_type, unit, calibration)
            SELECT CAST(gen_random_uuid() AS varchar(36)), id, 'pressure_hpa', 'hPa', '{}' FROM devices WHERE device_type = 'SENSOR';

INSERT INTO sensor_channels (id, device_id, sensor_type, unit, calibration)
            SELECT CAST(gen_random_uuid() AS varchar(36)), id, 'battery_pct', '%', '{}' FROM devices WHERE device_type = 'SENSOR';

UPDATE alembic_version SET version_num='7b94d6120344' WHERE alembic_version.version_num = '10f579997c3a';

COMMIT;

