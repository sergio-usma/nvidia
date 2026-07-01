# API Documentation

This guide covers API documentation tools for Jetson AGX Orin projects.

## Swagger/OpenAPI

Install:

```bash
pip install flasgger
```

```python
from flasgger import Swagger
from flask import Flask, request, jsonify

app = Flask(__name__)
swagger = Swagger(app)

@app.route('/api/users', methods=['GET'])
def get_users():
    """
    Get all users
    ---
    tags:
      - Users
    responses:
      200:
        description: List of users
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              name:
                type: string
    """
    return jsonify([{'id': 1, 'name': 'John'}])

@app.route('/api/users', methods=['POST'])
def create_user():
    """
    Create a new user
    ---
    tags:
      - Users
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - name
          properties:
            name:
              type: string
            email:
              type: string
    responses:
      201:
        description: User created
    """
    return jsonify({'id': 1, 'name': request.json['name']}), 201
```

Run and access: http://jetson:5000/apidocs

## Redoc

```bash
pip install flasgger
```

```python
from flasgger import Swagger
from flask import Flask

app = Flask(__name__)
swagger = Swagger(app, template={
    "swagger": "2.0",
    "info": {
        "title": "My API",
        "version": "1.0"
    },
    "definitions": {
        "User": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"}
            }
        }
    }
})
```

## FastAPI Documentation

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="My API",
    description="API for AI services",
    version="1.0.0"
)

class User(BaseModel):
    id: int
    name: str
    email: str | None = None

users = []

@app.post("/users", response_model=User)
async def create_user(user: User):
    users.append(user)
    return user

@app.get("/users", response_model=list[User])
async def get_users():
    return users
```

Access: http://jetson:8000/docs

## API Platform

```bash
npm install -g @api-platform/api-platform-admin
```

## Postman Collections

```json
{
  "info": {
    "name": "AI API Collection",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Chat",
      "request": {
        "method": "POST",
        "url": {
          "raw": "http://jetson:11434/api/generate",
          "protocol": "http",
          "host": ["jetson"],
          "port": "11434",
          "path": ["api", "generate"]
        },
        "body": {
          "mode": "raw",
          "raw": "{\"model\": \"llama2\", \"prompt\": \"Hello\"}"
        }
      }
    }
  ]
}
```

## Slate Documentation

```markdown
# API Reference

## Chat

Generate text using LLM.

**Endpoint:** `POST /api/generate`

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| model | string | Model name |
| prompt | string | Input prompt |

**Response:**

```json
{
  "response": "Generated text"
}
```
```

## MkDocs with OpenAPI

```yaml
# mkdocs.yml
plugins:
  - openapi
```

```markdown
# API Documentation

```{openapi}
openapi: 3.0.0
info:
  title: AI API
  version: 1.0.0
paths:
  /api/generate:
    post:
      summary: Generate text
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                prompt:
                  type: string
      responses:
        '200':
          description: OK
```
```

## GraphQL Documentation

```python
import graphene

class Query(graphene.ObjectType):
    hello = graphene.String(name=graphene.String(default_value="World"))

    def resolve_hello(self, info, name):
        return f"Hello {name}"

schema = graphene.Schema(query=Query)

# Access at /graphql
```

## Auto-generated Docs

```bash
# Install pdoc
pip install pdoc

# Generate docs
pdoc --output-dir docs mymodule
```

## API Versioning

```python
from flask import Blueprint

api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')
api_v2 = Blueprint('api_v2', __name__, url_prefix='/api/v2')

@api_v1.route('/users')
def get_users_v1():
    return jsonify([{'id': 1}])

@api_v2.route('/users')
def get_users_v2():
    return jsonify([{'id': 1, 'name': 'John', 'email': 'john@example.com'}])
```
