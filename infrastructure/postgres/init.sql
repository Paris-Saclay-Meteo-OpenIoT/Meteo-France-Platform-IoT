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

-- Table des stations (Infos qui ne changent pas souvent)
CREATE TABLE IF NOT EXISTS stations (
    station_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100),
    type VARCHAR(50),
    geo_id_insee VARCHAR(50),
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    start_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des mesures météo (Données temporelles)
CREATE TABLE IF NOT EXISTS weather_measurements (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(50) NOT NULL,
    reference_time TIMESTAMP,
    insert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validity_time TIMESTAMP,
    t DOUBLE PRECISION,
    td DOUBLE PRECISION,
    u DOUBLE PRECISION,
    dd DOUBLE PRECISION,
    ff DOUBLE PRECISION,
    dxi10 DOUBLE PRECISION,
    fxi10 DOUBLE PRECISION,
    rr_per DOUBLE PRECISION,
    CONSTRAINT fk_station
      FOREIGN KEY(station_id) 
      REFERENCES stations(station_id)
      ON DELETE CASCADE
);

-- Index pour accélérer les recherches (Indispensable pour les courbes Grafana)
CREATE INDEX idx_weather_station_time ON weather_measurements (station_id, reference_time DESC);