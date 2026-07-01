# Node.js Testing

This guide covers testing frameworks for Node.js applications on Jetson AGX Orin.

## Jest

Install:

```bash
npm install --save-dev jest
```

Configure in package.json:

```json
{
  "scripts": {
    "test": "jest"
  },
  "jest": {
    "testEnvironment": "node",
    "coverageDirectory": "coverage"
  }
}
```

## Basic Tests

```javascript
// math.js
function add(a, b) {
  return a + b;
}

function subtract(a, b) {
  return a - b;
}

module.exports = { add, subtract };
```

```javascript
// math.test.js
const { add, subtract } = require('./math');

describe('Math functions', () => {
  test('add adds two numbers', () => {
    expect(add(2, 3)).toBe(5);
  });
  
  test('subtract subtracts numbers', () => {
    expect(subtract(5, 3)).toBe(2);
  });
  
  test('add handles negative numbers', () => {
    expect(add(-2, -3)).toBe(-5);
  });
});
```

## Assertions

```javascript
// Equality
expect(value).toBe(5);
expect(value).toEqual({ name: 'John' });

// Truthiness
expect(value).toBeTruthy();
expect(value).toBeFalsy();
expect(value).toBeNull();
expect(value).toBeUndefined();

// Numbers
expect(value).toBeGreaterThan(5);
expect(value).toBeLessThan(10);
expect(value).toBeCloseTo(3.14, 2);

// Strings
expect(value).toMatch(/pattern/);
expect(value).toContain('substring');

// Arrays
expect(array).toContain(value);
expect(array).toHaveLength(3);

// Objects
expect(obj).toHaveProperty('name');
expect(obj).toMatchObject({ name: 'John' });

// Errors
expect(() => fail()).toThrow();
```

## Async Testing

```javascript
test('async data', async () => {
  const data = await fetchData();
  expect(data).toBeDefined();
});

test('promise resolves', () => {
  return expect(Promise.resolve('value')).resolves.toBe('value');
});

test('promise rejects', () => {
  return expect(Promise.reject('error')).rejects.toBe('error');
});
```

## Mocking

```javascript
// Mock module
jest.mock('./api');
const api = require('./api');
api.fetchData.mockResolvedValue({ name: 'John' });

// Mock function
const mockFn = jest.fn();
mockFn.mockReturnValue(5);
mockFn.mockResolvedValue('value');

// Spy
const obj = { method: jest.fn() };
obj.method.mockReturnValue(42);
```

## Supertest for API Testing

Install:

```bash
npm install --save-dev supertest
```

```javascript
const request = require('supertest');
const app = require('./app');

describe('API Tests', () => {
  test('GET /api/users', async () => {
    const response = await request(app)
      .get('/api/users')
      .expect(200);
    
    expect(Array.isArray(response.body)).toBe(true);
  });
  
  test('POST /api/users', async () => {
    const response = await request(app)
      .post('/api/users')
      .send({ name: 'John', email: 'john@example.com' })
      .expect(201);
    
    expect(response.body).toHaveProperty('id');
  });
  
  test('GET /api/users/:id not found', async () => {
    await request(app)
      .get('/api/users/999')
      .expect(404);
  });
});
```

## Mocha

Install:

```bash
npm install --save-dev mocha chai
```

```javascript
const { expect } = require('chai');
const { add, subtract } = require('./math');

describe('Math', () => {
  it('should add two numbers', () => {
    expect(add(2, 3)).to.equal(5);
  });
  
  it('should subtract numbers', () => {
    expect(subtract(5, 3)).to.equal(2);
  });
});
```

Run: `npx mocha`

## Running Tests

```bash
# Run tests
npm test

# Watch mode
npm test -- --watch

# Coverage
npm test -- --coverage

# Specific file
npm test -- math.test.js

# Specific test
npm test -- -t "add"
```

## CI Integration

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      - run: npm ci
      - run: npm test
      - run: npm run coverage
```

## Test Coverage

```json
{
  "jest": {
    "coverageThreshold": {
      "global": {
        "branches": 80,
        "functions": 80,
        "lines": 80,
        "statements": 80
      }
    }
  }
}
```

## Integration Tests

```javascript
const { spawn } = require('child_process');

describe('Integration Tests', () => {
  let server;
  
  beforeAll(async () => {
    server = spawn('node', ['server.js'], { cwd: __dirname });
    await new Promise(resolve => server.stdout.on('data', resolve));
  });
  
  afterAll(() => {
    server.kill();
  });
  
  test('server responds', async () => {
    const response = await fetch('http://localhost:3000');
    expect(response.ok).toBe(true);
  });
});
```

## Test Organization

```
tests/
├── unit/
│   ├── math.test.js
│   └── api.test.js
├── integration/
│   ├── auth.test.js
│   └── users.test.js
├── fixtures/
│   └── users.json
└── setup.js
```
