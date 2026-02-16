const { Pool } = require('pg');

const pool = new Pool({
  user: process.env.POSTGRES_USER || 'weatherapp',
  password: process.env.POSTGRES_PASSWORD || 'your_postgres_password_here',
  host: process.env.POSTGRES_HOST || 'ter_postgres',
  port: process.env.POSTGRES_PORT || 5432,
  database: process.env.POSTGRES_DB || 'weatherdb',
});

pool.on('error', (err) => {
  console.error('Erreur connexion PostgreSQL:', err);
});

module.exports = pool;
