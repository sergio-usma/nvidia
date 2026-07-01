# Node.js Database Integration

This guide covers database integration for Node.js applications on Jetson AGX Orin.

## SQLite3

Install:

```bash
npm install sqlite3
```

Usage:

```javascript
const sqlite3 = require('sqlite3').verbose();

const db = new sqlite3.Database('./mydb.sqlite');

// Create table
db.run(`CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT,
  email TEXT
)`);

// Insert
db.run(`INSERT INTO users (name, email) VALUES (?, ?)`, 
  ['John', 'john@example.com'],
  function(err) {
    if (err) console.error(err);
    console.log(`Inserted ID: ${this.lastID}`);
  }
);

// Select
db.all(`SELECT * FROM users`, [], (err, rows) => {
  if (err) console.error(err);
  console.log(rows);
});

// Select one
db.get(`SELECT * FROM users WHERE id = ?`, [1], (err, row) => {
  console.log(row);
});

// Update
db.run(`UPDATE users SET name = ? WHERE id = ?`, ['Jane', 1]);

// Delete
db.run(`DELETE FROM users WHERE id = ?`, [1]);

// Close
db.close();
```

## Better-SQLite3 (Synchronous)

Install:

```bash
npm install better-sqlite3
```

Usage:

```javascript
const Database = require('better-sqlite3');
const db = new Database('mydb.sqlite');

const stmt = db.prepare('INSERT INTO users (name, email) VALUES (?, ?)');
const info = stmt.run('John', 'john@example.com');

const rows = db.prepare('SELECT * FROM users').all();
const row = db.prepare('SELECT * FROM users WHERE id = ?').get(1);

db.close();
```

## PostgreSQL with node-postgres

Install:

```bash
npm install pg
```

Usage:

```javascript
const { Pool } = require('pg');

const pool = new Pool({
  user: 'postgres',
  host: 'localhost',
  database: 'mydb',
  password: 'password',
  port: 5432
});

// Query
const result = await pool.query('SELECT * FROM users');
console.log(result.rows);

// Parameterized query
const values = ['John', 'john@example.com'];
await pool.query('INSERT INTO users (name, email) VALUES ($1, $2)', values);

// Pool end
await pool.end();
```

## MongoDB with Mongoose

Install:

```bash
npm install mongoose
```

Usage:

```javascript
const mongoose = require('mongoose');

mongoose.connect('mongodb://localhost:27017/mydb');

const userSchema = new mongoose.Schema({
  name: String,
  email: { type: String, unique: true },
  createdAt: { type: Date, default: Date.now }
});

const User = mongoose.model('User', userSchema);

// Create
const user = await User.create({ name: 'John', email: 'john@example.com' });

// Read
const users = await User.find();
const user = await User.findOne({ email: 'john@example.com' });

// Update
await User.updateOne({ _id: user._id }, { name: 'Jane' });

// Delete
await User.deleteOne({ _id: user._id });
```

## Redis with ioredis

Install:

```bash
npm install ioredis
```

Usage:

```javascript
const Redis = require('ioredis');

const redis = new Redis();

// String
await redis.set('key', 'value');
const value = await redis.get('key');

// Hash
await redis.hset('user:1', 'name', 'John');
await redis.hset('user:1', 'email', 'john@example.com');
const user = await redis.hgetall('user:1');

// List
await redis.lpush('queue', 'task1');
const task = await redis.rpop('queue');

// Cache example
async function getCachedData(key) {
  const cached = await redis.get(key);
  if (cached) return JSON.parse(cached);
  
  const data = await fetchData();
  await redis.setex(key, 3600, JSON.stringify(data));
  return data;
}

redis.disconnect();
```

## MySQL

Install:

```bash
npm install mysql2
```

Usage:

```javascript
const mysql = require('mysql2/promise');

const connection = await mysql.createConnection({
  host: 'localhost',
  user: 'root',
  password: 'password',
  database: 'mydb'
});

const [rows] = await connection.execute('SELECT * FROM users');
await connection.execute(
  'INSERT INTO users (name, email) VALUES (?, ?)',
  ['John', 'john@example.com']
);

await connection.end();
```

## Prisma ORM

Install:

```bash
npm install prisma --save-dev
npm install @prisma/client
npx prisma init
```

Schema (prisma/schema.prisma):

```prisma
datasource db {
  provider = "sqlite"
  url      = "file:./dev.db"
}

model User {
  id    Int     @id @default(autoincrement())
  name  String
  email String  @unique
}
```

Usage:

```javascript
const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

const users = await prisma.user.findMany();
const user = await prisma.user.create({
  data: { name: 'John', email: 'john@example.com' }
});

await prisma.$disconnect();
```

## Database Connection Pooling

```javascript
// SQLite
const db = new sqlite3.Database('./mydb.sqlite');

// PostgreSQL
const pool = new Pool({
  max: 20,
  idleTimeoutMillis: 30000
});

// Reuse connections efficiently
```

## Environment Config

```javascript
require('dotenv').config();

const dbConfig = {
  host: process.env.DB_HOST || 'localhost',
  port: process.env.DB_PORT || 5432,
  database: process.env.DB_NAME || 'mydb',
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD
};
```

## Transactions

```javascript
// PostgreSQL
await pool.query('BEGIN');
try {
  await pool.query('INSERT INTO accounts (id, balance) VALUES (1, 100)');
  await pool.query('INSERT INTO accounts (id, balance) VALUES (2, 0)');
  await pool.query('COMMIT');
} catch (e) {
  await pool.query('ROLLBACK');
  throw e;
}
```
