from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict
import asyncio
import json
from fastapi.middleware.cors import CORSMiddleware
from db_config import users_list, create_tables  # Importa correctamente estas funciones
import logging
import aiohttp  # Agregamos esta importación
import os  # Agregamos esta importación

# Configurar el logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Diccionario para almacenar los clientes WebSocket conectados
connected_users: Dict[str, WebSocket] = {}

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chat-web-407k.onrender.com"],  # En producción, deberías especificar los dominios exactos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Nueva ruta para el ping
@app.get("/ping")
async def ping():
    return {"status": "alive"}

# Nueva función para mantener viva la aplicación
async def keep_alive():
    """Hace ping al servidor cada 5 minutos para mantenerlo activo"""
    app_url ='https://chat-api-flyo.onrender.com'
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{app_url}/ping") as response:
                    logger.info(f"Ping status: {response.status}")
            await asyncio.sleep(300)  # 5 minutos
        except Exception as e:
            logger.error(f"Error en keep_alive: {e}")
            await asyncio.sleep(60)  # Si hay error, espera 1 minuto antes de reintentar

# Modificar la función de inicio
@app.on_event("startup")
async def startup_event():
    """Inicia el proceso de keep-alive cuando arranca la aplicación"""
    asyncio.create_task(keep_alive())

async def broadcast_user_count():
    """Envía el número de usuarios conectados a todos los clientes."""
    count_message = json.dumps({
        "type": "user_count",
        "count": len(connected_users)
    })
    logger.info(f"Enviando conteo de usuarios conectados: {count_message}")
    disconnected_users = []

    for user_id, user_ws in connected_users.items():
        try:
            await user_ws.send_text(count_message)
        except WebSocketDisconnect:
            logger.warning(f"Usuario {user_id} desconectado durante el broadcast.")
            disconnected_users.append(user_id)
        except Exception as e:
            logger.error(f"Error al enviar mensaje al usuario {user_id}: {e}")

    # Remover usuarios desconectados
    for user_id in disconnected_users:
        connected_users.pop(user_id, None)

async def broadcast_message(message: dict):
    """Envía un mensaje a todos los clientes conectados."""
    logger.info(f"Transmitiendo mensaje: {message}")
    disconnected_users = []

    for user_id, user_ws in connected_users.items():
        try:
            await user_ws.send_text(json.dumps(message))
        except WebSocketDisconnect:
            logger.warning(f"Usuario {user_id} desconectado durante el broadcast.")
            disconnected_users.append(user_id)
        except Exception as e:
            logger.error(f"Error al enviar mensaje al usuario {user_id}: {e}")

    # Remover usuarios desconectados
    for user_id in disconnected_users:
        connected_users.pop(user_id, None)

async def heartbeat(websocket: WebSocket):
    """Mantiene la conexión activa enviando pings periódicos."""
    try:
        while True:
            await websocket.send_text(json.dumps({"type": "ping"}))
            await asyncio.sleep(30)  # Envía un ping cada 30 segundos
    except WebSocketDisconnect:
        logger.warning("WebSocket desconectado durante el heartbeat.")
    except Exception as e:
        logger.error(f"Error en el heartbeat: {e}")

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(user_id: str, websocket: WebSocket):
    logger.info(f"Intento de conexión WebSocket para el usuario: {user_id}")

    # Verificar si el usuario ya está conectado
    if user_id in connected_users:
        logger.warning(f"Usuario {user_id} ya está conectado. Cerrando conexión.")
        await websocket.close(code=1008)
        return

    # Aceptar la conexión y agregar al usuario
    await websocket.accept()
    connected_users[user_id] = websocket
    logger.info(f"Usuario {user_id} conectado exitosamente.")
    await broadcast_user_count()  # Actualizar el conteo de usuarios conectados

    # Iniciar el heartbeat
    asyncio.create_task(heartbeat(websocket))

    try:
        # Esperar mensajes del cliente
        while True:
            data = await websocket.receive_text()
            logger.info(f"Mensaje recibido del usuario {user_id}: {data}")
            
            # Procesar el mensaje recibido
            try:
                message_data = json.loads(data)
                # Agregar el tipo de mensaje para el cliente
                message_data["type"] = "message"
                await broadcast_message(message_data)
            except json.JSONDecodeError:
                logger.error(f"Error al decodificar el mensaje: {data}")
            except Exception as e:
                logger.error(f"Error al procesar el mensaje: {e}")

    except WebSocketDisconnect:
        logger.info(f"Usuario {user_id} se desconectó.")
    except Exception as e:
        logger.error(f"Error en WebSocket con el usuario {user_id}: {e}")
    finally:
        # Eliminar usuario de la lista y actualizar el conteo
        connected_users.pop(user_id, None)
        await broadcast_user_count()

@app.get("/users")
async def get_users():
    """Obtiene la lista de usuarios desde la base de datos."""
    try:
        logger.info("Obteniendo lista de usuarios...")
        return {"users": users_list()}
    except Exception as e:
        logger.error(f"Error al obtener la lista de usuarios: {e}")
        return {"error": "No se pudo obtener la lista de usuarios"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Creando tablas si no existen...")
    create_tables()
    logger.info("Iniciando servidor...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
