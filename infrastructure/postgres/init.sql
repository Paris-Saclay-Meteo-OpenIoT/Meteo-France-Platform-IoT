-- Création de la table users avec la colonne role
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password TEXT NOT NULL,
    nom VARCHAR(50) NOT NULL,
    prenom VARCHAR(50) NOT NULL,
    status BOOLEAN NOT NULL DEFAULT true,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- Insertion d'un compte admin avec mot de passe haché
-- Le hash ci-dessous correspond à "motdepasseadmin" généré avec bcrypt et 10 salt rounds
INSERT INTO users (email, password, role, nom, prenom)
VALUES (
    'admin@example.com',
    '$2b$10$i3PRLsVQ7TY9J1xguNjdXutP.2Dcv2k1aK.fF5KooJKMhttk2f3CO',
    'admin',
    'Admin',
    'User'
);

-- Création de la table role_request pour gérer les demandes de changement de rôle
CREATE TABLE IF NOT EXISTS role_request (
    id SERIAL PRIMARY KEY,
    id_user INTEGER NOT NULL,
    lname VARCHAR(50) NOT NULL,
    fname VARCHAR(50) NOT NULL,
    desired_role VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user
      FOREIGN KEY (id_user)
      REFERENCES users(id)
      ON DELETE CASCADE,
    CONSTRAINT status_valid CHECK (status IN ('pending', 'accepted', 'refused'))
);

-- Création de la table weather_data pour les données historiques
CREATE TABLE IF NOT EXISTS weather_data (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(50),
    nom_usuel VARCHAR(255),
    lat FLOAT,          -- Latitude
    lon FLOAT,          -- Longitude
    date TIMESTAMP,
    t FLOAT,           -- Température
    u FLOAT,           -- Humidité
    ff FLOAT,          -- Vitesse du vent
    dd INT,            -- Direction du vent
    rr1 FLOAT,         -- Précipitations
    n FLOAT,           -- Nébulosité
    vis INT,           -- Visibilité
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(station_id, date)
);

-- Index pour les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_weather_station ON weather_data(station_id);
CREATE INDEX IF NOT EXISTS idx_weather_date ON weather_data(date);
CREATE INDEX IF NOT EXISTS idx_weather_station_date ON weather_data(station_id, date);
CREATE UNIQUE INDEX IF NOT EXISTS idx_weather_nom_station_date ON weather_data(nom_usuel, station_id, date);

-- Création de la table forecast_results pour les prédictions ML
CREATE TABLE IF NOT EXISTS forecast_results (
    id SERIAL PRIMARY KEY,
    station VARCHAR(50),
    station_id VARCHAR(50),
    lat FLOAT,          -- Latitude
    lon FLOAT,          -- Longitude
    forecast_time TIMESTAMP,
    forecast_date DATE,
    t_pred FLOAT,      -- Température prédite
    ff_pred FLOAT,     -- Vent prédit
    rr1_pred FLOAT,    -- Précipitations prédites
    u_pred FLOAT,      -- Humidité prédite
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(station_id, forecast_time)
);

-- Index pour les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_forecast_station ON forecast_results(station);
CREATE INDEX IF NOT EXISTS idx_forecast_station_id ON forecast_results(station_id);
CREATE INDEX IF NOT EXISTS idx_forecast_time ON forecast_results(forecast_time);
CREATE INDEX IF NOT EXISTS idx_forecast_date ON forecast_results(forecast_date);
CREATE UNIQUE INDEX IF NOT EXISTS idx_forecast_station_time ON forecast_results(station, forecast_time);