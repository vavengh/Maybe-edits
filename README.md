# Crypto Portfolio API – Buda.com

REST API desarrollada en **Python + FastAPI** que permite valorizar un portafolio de criptomonedas usando precios en tiempo real obtenidos desde la API pública de **Buda.com**.

> Este repositorio se está construyendo de manera incremental, priorizando buenas prácticas, código limpio y tests automatizados.

---

## Requisitos del sistema

Antes de comenzar, asegúrate de tener instalado:

- **Python 3.10 o superior**
- **pip**
- **git**

En sistemas basados en Debian/Ubuntu (incluido WSL):

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

## Instalación y ejecución local

1️⃣ Clonar el repositorio

```bash
git clone https://github.com/TU_USUARIO/Tarea-Buda-Py.git
cd Tarea-Buda-Py
```

## Crear y activar entorno virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Instalar dependencias

```bash
pip install -r requirements.txt
```

## Levantar el servidor

```bash
uvicorn app.main:app --reload
```
La API quedará disponible en:

Health check: http://127.0.0.1:8000/health

Documentación Swagger (OpenAPI): http://127.0.0.1:8000/docs

## Endpoint:

POST /portfolio/value (endpoint principal)

Calcula el valor de un portafolio de criptomonedas en una moneda fiat de referencia.

Request body ejemplo (JSON)
```bash
{
  "portfolio": {
    "BTC": 0.5,
    "ETH": 2.0
  },
  "fiat_currency": "CLP"
}
```

portfolio: mapa de símbolo de criptomoneda a cantidad (no negativa)
fiat_currency: moneda fiat de referencia (CLP, PEN o COP)

Respuesta exitosa (200)
```bash
{
  "fiat_currency": "CLP",
  "total": "45400000",
  "breakdown": {
    "BTC": "40000000",
    "ETH": "5400000"
  },
  "unpriced": []
}
```

total: valor total del portafolio en la moneda fiat
breakdown: valorización individual por cripto
unpriced: criptos que no pudieron valorizarse

## Deploy
Fue realizado con render y se encuentra en el enlace:
https://tarea-buda-py.onrender.com

## Supuestos para la valorización
🔹 Máximo de dos saltos
Si no existe un mercado directo, la API permite una conversión usando un intermediario, con un máximo de 2 saltos.

Por ejemplo:
ETH → BTC → CLP
En caso de que no sea posible ETH → CLP

Se toma en cuenta este límite de 2 saltos por varias razones:
- Mantiene la solución simple y eficiente.
- Refleja un escenario realista de valorización (la idea tampoco es alejarse de una valoracion realista por exceso de saltos).
- Evita rutas largas, ciclos y resultados poco fiables.
- Facilita testeo y mantenimiento del código.
- Es facilmente extensible en el futuro si se desea aumentar el límite.

🔹Criptomonedas no valorizables
Si una criptomoneda no puede convertirse a la moneda fiat ni directa ni indirectamente (hasta 2 saltos), entonces:
- No se incluye en el cálculo del total
- Se agrega su símbolo al arreglo unpriced

## Ejemplos de uso manual (curl)

En la consola, con el servidor corriendo, puedes probar los siguientes ejemplos:
(Si se quiere usar el servidor deployado debes reemplazar "https://tarea-buda-py.onrender.com" por http://127.0.0.1:8000)

Ejemplo válido – conversión directa:
```bash
curl -X POST "http://127.0.0.1:8000/portfolio/value" \
  -H "Content-Type: application/json" \
  -d '{
    "portfolio": {"BTC": 0.5},
    "fiat_currency": "CLP"
  }'
```

Ejemplo inválido – cantidad negativa:
```bash
curl -X POST "http://127.0.0.1:8000/portfolio/value" \
  -H "Content-Type: application/json" \
  -d '{
    "portfolio": {"BTC": -1},
    "fiat_currency": "CLP"
  }'
```
Respuesta esperada: 422 Unprocessable Entity

Ejemplo inválido – moneda fiat no permitida
```bash
curl -X POST "http://127.0.0.1:8000/portfolio/value" \
  -H "Content-Type: application/json" \
  -d '{
    "portfolio": {"BTC": 1},
    "fiat_currency": "USD"
  }'
```
Respuesta esperada: 422 Unprocessable Entity

## Tests
Para ejecutar los tests de manera manual, asegúrate de tener instalado `pytest` y luego corre:

```bash
source .venv/bin/activate
pytest -q
```

De igual forma, estos se corren automaticamente mediante GithubActions en cada push o pull request.