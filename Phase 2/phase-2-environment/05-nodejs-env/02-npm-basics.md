# NPM and Package Management

This guide covers npm (Node Package Manager) for Jetson AGX Orin.

## Check npm Version

```bash
npm --version
node --version
```

## Initialize Project

```bash
npm init
npm init -y  # quick init with defaults
```

## Install Packages

```bash
npm install package_name
npm install package_name@version
npm install package_name --save
npm install package_name --save-dev
npm install package_name -g  # global
```

## Install from package.json

```bash
npm install
```

## Update Packages

```bash
npm update
npm update package_name
```

## List Packages

```bash
npm list
npm list --depth=0
npm list -g --depth=0
```

## Remove Packages

```bash
npm uninstall package_name
npm uninstall package_name --save
```

## Package.json Scripts

```json
{
  "scripts": {
    "start": "node app.js",
    "dev": "nodemon app.js",
    "test": "jest",
    "build": "webpack --mode production",
    "lint": "eslint ."
  }
}
```

Run scripts:

```bash
npm run dev
npm start
```

## npx - Run Packages

```bash
npx create-react-app my-app
npx typescript --init
```

## Global Packages

List global packages:

```bash
npm list -g --depth=0
```

Update global packages:

```bash
npm update -g
```

## npm Config

Set registry:

```bash
npm config set registry https://registry.npmjs.org/
```

Use yarn:

```bash
npm install -g yarn
```

## pnpm Alternative

Install:

```bash
npm install -g pnpm
```

Usage:

```bash
pnpm install
pnpm add package
pnpm remove package
```

## yarn Alternative

Install:

```bash
npm install -g yarn
```

Usage:

```bash
yarn install
yarn add package
yarn remove package
```

## Common Global Tools

```bash
npm install -g nodemon
npm install -g pm2
npm install -g typescript
npm install -g ts-node
npm install -g eslint
npm install -g webpack
npm install -g create-react-app
```

## npm Cache

Clean cache:

```bash
npm cache clean --force
```

Verify:

```bash
npm cache verify
```

## Package.json Fields

```json
{
  "name": "my-project",
  "version": "1.0.0",
  "description": "My project",
  "main": "index.js",
  "scripts": {},
  "dependencies": {},
  "devDependencies": {},
  "keywords": [],
  "author": "",
  "license": "MIT"
}
```

## npm Audit

Check for vulnerabilities:

```bash
npm audit
npm audit fix
```

## Semantic Versioning

- `^1.2.3` = >=1.2.3 <2.0.0
- `~1.2.3` = >=1.2.3 <1.3.0
- `1.2.3` = exactly 1.2.3
- `*` = latest

## npm Workspaces

```json
{
  "workspaces": [
    "packages/*"
  ]
}
```

## Publish Package

```bash
npm login
npm publish
```

## Private Packages

```json
{
  "private": true
}
```
